from datetime import datetime, timedelta

from astrbot.api import logger
from astrbot.core import html_renderer
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.message.components import Image, Plain
from astrbot.core.platform.message_session import MessageSession
from astrbot.core.platform.message_type import MessageType


WORD_CARD_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .card {
      width: 100%;
      background: #fff;
      overflow: hidden;
    }
    .card-header {
      background: linear-gradient(135deg, #4f46e5, #7c3aed);
      color: #fff;
      padding: 28px 32px 20px;
      text-align: center;
    }
    .card-tag {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      border-radius: 20px;
      padding: 4px 18px;
      font-size: 14px;
      letter-spacing: 2px;
      margin-bottom: 16px;
    }
    .word {
      font-size: 52px;
      font-weight: 700;
      letter-spacing: 2px;
    }
    .phonetic {
      font-size: 20px;
      opacity: 0.8;
      margin-top: 6px;
    }
    .card-body {
      padding: 28px 32px;
      text-align: center;
    }
    .meaning {
      font-size: 26px;
      color: #1e293b;
      line-height: 1.6;
      padding: 14px 20px;
      background: #f8fafc;
      border-radius: 12px;
      border-left: 4px solid #4f46e5;
    }
    .example-box {
      margin-top: 20px;
      padding: 14px 20px;
      background: #fefce8;
      border-radius: 12px;
      border-left: 4px solid #f59e0b;
      text-align: left;
    }
    .example-label {
      font-size: 14px;
      color: #b45309;
      letter-spacing: 1px;
      margin-bottom: 4px;
    }
    .example-text {
      font-size: 20px;
      color: #713f12;
      font-style: italic;
      line-height: 1.5;
    }
    .card-footer {
      padding: 16px 32px 24px;
      display: flex;
      justify-content: space-around;
      color: #64748b;
      font-size: 18px;
    }
    .stat-item {
      text-align: center;
    }
    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #4f46e5;
    }
    .stat-label {
      font-size: 14px;
      margin-top: 2px;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="card-header">
      <div class="card-tag">{{ card_tag }}</div>
      <div class="word">{{ word.word }}</div>
      {% if word.phonetic %}
      <div class="phonetic">{{ word.phonetic }}</div>
      {% endif %}
    </div>
    <div class="card-body">
      <div class="meaning">{{ word.meaning }}</div>
      {% if word.example %}
      <div class="example-box">
        <div class="example-label">例句</div>
        <div class="example-text">"{{ word.example }}"</div>
      </div>
      {% endif %}
    </div>
    <div class="card-footer">
      <div class="stat-item">
        <div class="stat-value">{{ streak }}</div>
        <div class="stat-label">连续天数</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ total }}</div>
        <div class="stat-label">累计单词</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ today_learned }}/{{ target }}</div>
        <div class="stat-label">今日进度</div>
      </div>
    </div>
  </div>
</body>
</html>"""


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

    async def _on_push(self, target_type: str, target_id: str, include_learned: bool = False):
        logger.info(f"Daily push triggered for {target_type}:{target_id}")

        user_id = f"cron_{target_id}"
        platform = "cron"
        user = await self.db.get_user(user_id)
        today = datetime.now().strftime("%Y-%m-%d")

        if not user:
            await self.db.create_user(user_id, platform, target_id)
            user = await self.db.get_user(user_id)

        word = await self.wordbank_loader.pick_new_word(user_id, include_learned=include_learned)
        if not word:
            logger.info("No new words available for push.")
            return

        # Record learning
        await self.db.add_learning_record(user_id, word["word"], today)
        total = user.get("total_learned", 0) + 1
        streak = 1
        if user.get("last_checkin"):
            last = user["last_checkin"]
            last_dt = datetime.strptime(last, "%Y-%m-%d")
            if (datetime.now() - last_dt).days == 1:
                streak = user.get("streak_days", 0) + 1
        today_learned = await self.db.get_today_learned(user_id, today) + 1
        await self.db.update_user_checkin(user_id, today, streak, total, today_learned)

        # Refresh user data
        user = await self.db.get_user(user_id)

        mt = MessageType.FRIEND_MESSAGE if target_type == "private" else MessageType.GROUP_MESSAGE
        session = MessageSession(
            platform_name="cron",
            message_type=mt,
            session_id=target_id,
        )

        # Render HTML card to image
        streak_val = user.get("streak_days", 0)
        total_val = user.get("total_learned", 0)
        target_val = user.get("daily_target", 10)

        is_learned = word.get("is_learned", False)
        card_tag = "📖 今日单词推送 · 已学习" if is_learned else "📖 今日单词推送"

        image_url = await html_renderer.render_custom_template(
            WORD_CARD_TMPL,
            {
                "card_tag": card_tag,
                "word": {
                    "word": word.get("word", ""),
                    "phonetic": word.get("phonetic", ""),
                    "meaning": word.get("meaning", ""),
                    "example": word.get("example", ""),
                },
                "streak": streak_val,
                "total": total_val,
                "today_learned": today_learned,
                "target": target_val,
            },
            return_url=True,
        )

        stats = (
            f"🔥 连续 {streak_val} 天  |  "
            f"📚 累计 {total_val} 词  |  "
            f"🎯 今日 {today_learned}/{target_val}"
        )

        chain = MessageChain()
        chain.chain.append(Image.fromURL(image_url))
        chain.chain.append(Plain("\n" + stats))

        try:
            await self.context.send_message(session, chain)
            logger.info("Daily push sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send push message: {e}")
