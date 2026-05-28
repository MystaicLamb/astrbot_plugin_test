from datetime import datetime

from astrbot.api import logger
from astrbot.core.platform.message_session import MessageSession
from astrbot.core.platform.message_type import MessageType


class PushScheduler:
    def __init__(self, context, db, wordbank_loader):
        self.context = context
        self.db = db
        self.wordbank_loader = wordbank_loader
        self._job_id = None

    async def schedule(self, config: dict):
        """Schedule or reschedule the daily push job."""
        push_cfg = config.get("daily_push", {})
        if not push_cfg.get("enabled", False):
            await self.cancel()
            return

        push_time = push_cfg.get("push_time", "08:00")
        target_type = push_cfg.get("target_type", "private")
        target_id = push_cfg.get("target_id", "")

        if not target_id:
            logger.warning("Push target_id is empty, skipping schedule.")
            return

        try:
            hour, minute = push_time.split(":")
            cron_expr = f"{int(minute)} {int(hour)} * * *"
        except Exception:
            logger.warning(f"Invalid push_time format: {push_time}, using 08:00")
            cron_expr = "0 8 * * *"

        await self.cancel()

        job = await self.context.cron_manager.add_basic_job(
            name="daily_word_push",
            cron_expression=cron_expr,
            handler=self._on_push,
            description="Daily word push for users",
            payload={
                "target_type": target_type,
                "target_id": target_id,
                "include_learned": config.get("include_learned", False),
            },
            enabled=True,
            persistent=False,
        )
        self._job_id = job.job_id
        logger.info(f"Scheduled daily word push at {push_time} to {target_type}:{target_id}")

    async def cancel(self):
        if self._job_id:
            try:
                await self.context.cron_manager.delete_job(self._job_id)
            except Exception as e:
                logger.warning(f"Failed to cancel push job: {e}")
            self._job_id = None

    @staticmethod
    def _fmt_word_card(word: dict) -> str:
        """Format a word as a plain-text card."""
        lines = []
        lines.append("📖 今日单词推送")
        lines.append("")
        word_line = f"🔤 {word.get('word', '')}"
        phonetic = word.get("phonetic", "")
        if phonetic:
            word_line += f"  {phonetic}"
        lines.append(word_line)
        lines.append("")
        lines.append(f"📘 释义: {word.get('meaning', '')}")
        example = word.get("example", "")
        if example:
            lines.append(f"💬 例句: \"{example}\"")
        return "\n".join(lines)

    async def _on_push(self, target_type: str, target_id: str, include_learned: bool = False):
        logger.info(f"Daily push triggered for {target_type}:{target_id}")

        today = datetime.now().strftime("%Y-%m-%d")
        group_id = target_id if target_type == "group" else ""

        # For group push, pick a word that hasn't been learned by anyone in the group today
        # Use a synthetic cron user for word selection
        user_id = f"cron_{target_id}"
        platform = "cron"
        user = await self.db.get_user(user_id)
        if not user:
            await self.db.create_user(user_id, platform, target_id)
            user = await self.db.get_user(user_id)

        word = await self.wordbank_loader.pick_new_word(user_id, group_id=group_id, include_learned=include_learned)
        if not word:
            logger.info("No new words available for push.")
            return

        # Record learning for cron user (so next push won't repeat immediately)
        await self.db.add_learning_record(user_id, group_id, word["word"], today)
        total = user.get("total_learned", 0) + 1
        streak = 1
        if user.get("last_checkin"):
            last = user["last_checkin"]
            last_dt = datetime.strptime(last, "%Y-%m-%d")
            if (datetime.now() - last_dt).days == 1:
                streak = user.get("streak_days", 0) + 1
        today_learned = await self.db.get_group_today_learned(user_id, group_id, today) + 1
        await self.db.update_user_checkin(user_id, today, streak, total, today_learned)

        card_text = self._fmt_word_card(word)

        mt = MessageType.FRIEND_MESSAGE if target_type == "private" else MessageType.GROUP_MESSAGE
        session = MessageSession(
            platform_name="cron",
            message_type=mt,
            session_id=target_id,
        )

        text = f"🌅 早安！今日单词已送达 ~\n\n{card_text}\n\n💡 发送 /今日单词 开始学习，/复习单词 巩固记忆"

        try:
            from astrbot.api.message_components import Plain
            chain = Plain(text)
            await self.context.send_message(session, chain)
            logger.info("Daily push sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send push message: {e}")
