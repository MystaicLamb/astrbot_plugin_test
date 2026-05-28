import os
from datetime import datetime, timedelta

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain

from .database import WordDatabase
from .wordbank import WordBankLoader
from .tasks import PushScheduler


@register("dailyword", "PluginDev", "每日单词学习插件", "2.0.0")
class DailyWordPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.plugin_dir, "data.db")
        self.db = WordDatabase(self.db_path)
        self.loader = WordBankLoader(self.db)
        self.scheduler = PushScheduler(context, self.db, self.loader)

    async def initialize(self):
        await self.db.initialize()
        await self.loader.ensure_loaded("cet4")
        await self.scheduler.schedule(self.config)
        logger.info("DailyWord plugin initialized.")

    async def terminate(self):
        await self.scheduler.cancel()
        await self.db.close()
        logger.info("DailyWord plugin terminated.")

    def _get_user_id(self, event: AstrMessageEvent) -> str:
        return event.unified_msg_origin

    def _get_group_id(self, event: AstrMessageEvent) -> str:
        return event.get_group_id() or ""

    def _get_today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _get_greeting(self) -> str:
        """Return greeting based on time of day."""
        hour = datetime.now().hour
        if 5 <= hour < 11:
            return "🌅 早安！开启今日学习之旅 ~"
        elif 11 <= hour < 14:
            return "☀️ 中午好！学个单词提神醒脑 ~"
        elif 14 <= hour < 19:
            return "🌤️ 下午好！继续积累词汇量 ~"
        else:
            return "🌙 晚上好！睡前复习效果加倍 ~"

    @staticmethod
    def _progress_bar(current: int, total: int, length: int = 10) -> str:
        """Generate emoji progress bar."""
        if total <= 0:
            return "░" * length
        filled = min(length, int(current / total * length))
        return "█" * filled + "░" * (length - filled)

    async def _ensure_user(self, event: AstrMessageEvent):
        user_id = self._get_user_id(event)
        user = await self.db.get_user(user_id)
        if not user:
            platform = event.get_platform_name()
            native_id = event.get_sender_id()
            await self.db.create_user(user_id, platform, native_id)
            user = await self.db.get_user(user_id)
        group_id = event.get_group_id()
        if group_id:
            await self.db.update_user_groups(user_id, group_id)
        return user

    @staticmethod
    def _fmt_word_card(word: dict, user: dict, today_learned: int = 0, review_count: int = 0) -> str:
        """Format a word as a plain-text card."""
        lines = []
        tag = "📖 复习单词" if review_count > 0 else ("📖 已学习" if word.get("is_learned") else "📖 每日单词")
        lines.append(f"{tag}")
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
        lines.append("")
        streak = user.get("streak_days", 0)
        total = user.get("total_learned", 0)
        target = user.get("daily_target", 10)
        lines.append(f"🔥 连续 {streak} 天  |  📚 累计 {total} 词  |  🎯 今日 {today_learned}/{target}")
        if review_count > 0:
            lines.append(f"📝 第 {review_count} 次复习")
        return "\n".join(lines)

    @staticmethod
    def _fmt_stats(user: dict, today_learned: int = 0) -> str:
        """Format statistics line as plain text."""
        streak = user.get("streak_days", 0)
        total = user.get("total_learned", 0)
        target = user.get("daily_target", 10)
        return (
            f"🔥 连续 {streak} 天  |  "
            f"📚 累计 {total} 词  |  "
            f"🎯 今日 {today_learned}/{target}"
        )

    @filter.command("今日单词")
    async def today_word(self, event: AstrMessageEvent):
        """Pick a new word to learn, check in, and send text card."""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)
        group_id = self._get_group_id(event)
        today = self._get_today()

        include_learned = self.config.get("include_learned", False)
        word = await self.loader.pick_new_word(user_id, group_id=group_id, category="cet4", include_learned=include_learned)
        if not word:
            yield event.plain_result("🎉 恭喜你！你已经学完了当前词库中的所有单词！")
            return

        await self.db.add_learning_record(user_id, group_id, word["word"], today)
        total = user.get("total_learned", 0) + 1
        streak = 1
        if user.get("last_checkin"):
            last_dt = datetime.strptime(user["last_checkin"], "%Y-%m-%d")
            if (datetime.now() - last_dt).days == 1:
                streak = user.get("streak_days", 0) + 1
        today_learned = await self.db.get_group_today_learned(user_id, group_id, today) + 1
        await self.db.update_user_checkin(user_id, today, streak, total, today_learned)
        user = await self.db.get_user(user_id)

        card_text = self._fmt_word_card(word, user, today_learned=today_learned)

        greeting = self._get_greeting()
        bar = self._progress_bar(today_learned, user.get("daily_target", 10))
        target = user.get("daily_target", 10)
        remain = max(0, target - today_learned)

        footer_lines = [
            f"━━━━━━━━━━━━━━",
            f"📊 今日进度  {bar}  {today_learned}/{target}",
            f"🔥 连续打卡 {user.get('streak_days', 0)} 天  |  📚 累计学习 {user.get('total_learned', 0)} 词",
            f"━━━━━━━━━━━━━━",
        ]
        if today_learned >= target:
            footer_lines.append("🎉 太棒了！今日目标已达成！")
        else:
            footer_lines.append(f"💪 还差 {remain} 个单词达成今日目标，加油！")
        footer_lines.append("💡 /复习单词 巩固记忆  ·  /我的进度 查看详情")

        text = greeting + "\n" + card_text + "\n" + "\n".join(footer_lines)
        yield event.plain_result(text)

    @filter.command("复习单词")
    async def review_word(self, event: AstrMessageEvent):
        """Pick a learned word to review."""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)
        group_id = self._get_group_id(event)

        learned = await self.db.get_group_learned_words(user_id, group_id)
        if not learned:
            yield event.plain_result("📭 你还没有学过单词，先发送 /今日单词 开始学习吧！")
            return

        word = await self.loader.pick_review_word(user_id, group_id=group_id)
        if not word:
            yield event.plain_result("📭 你还没有学过单词，先发送 /今日单词 开始学习吧！")
            return

        today = self._get_today()
        await self.db.update_review(user_id, group_id, word["word"], today)

        record = None
        for r in learned:
            if r["word"] == word["word"]:
                record = r
                break
        review_count = (record["review_count"] + 1) if record else 1

        card_text = self._fmt_word_card(word, user, today_learned=user.get("today_learned", 0), review_count=review_count)

        bar = self._progress_bar(user.get("today_learned", 0), user.get("daily_target", 10))

        footer_lines = [
            f"━━━━━━━━━━━━━━",
            f"📊 今日进度  {bar}  {user.get('today_learned', 0)}/{user.get('daily_target', 10)}",
            f"🔥 连续打卡 {user.get('streak_days', 0)} 天  |  📚 累计学习 {user.get('total_learned', 0)} 词",
            f"━━━━━━━━━━━━━━",
            f"📝 这是第 {review_count} 次复习这个单词",
            "💡 /今日单词 学习新词  ·  /单词本 查看已学",
        ]

        text = "🔄 来复习一下，温故知新 ~\n" + card_text + "\n" + "\n".join(footer_lines)
        yield event.plain_result(text)

    @filter.command("我的进度")
    async def my_progress(self, event: AstrMessageEvent):
        """Show personal learning progress."""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)
        group_id = self._get_group_id(event)
        today = self._get_today()

        group_learned = await self.db.get_group_learned_words(user_id, group_id)
        group_today = await self.db.get_group_today_learned(user_id, group_id, today)

        d = "━━━━━━━━━━━━━━"
        lines = ["📊 我的学习进度", d]
        lines.append(f"🔥 连续打卡: {user.get('streak_days', 0)} 天")
        lines.append(f"📚 累计学习: {user.get('total_learned', 0)} 词")
        lines.append(f"🎯 每日目标: {user.get('daily_target', 10)} 词")
        lines.append(f"📅 最后打卡: {user.get('last_checkin', '无') or '无'}")
        if group_id:
            lines.append(d)
            lines.append(f"👥 当前群组学习: {len(group_learned)} 词")
            lines.append(f"📊 本群今日已学: {group_today} 词")
        yield event.plain_result("\n".join(lines))

    @filter.command("单词本")
    async def word_book(self, event: AstrMessageEvent):
        """List recently learned words. Usage: /单词本 [数量]"""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)
        group_id = self._get_group_id(event)

        msg = event.message_str.strip()
        parts = msg.split()
        limit = 10
        if len(parts) > 1:
            try:
                limit = max(1, min(50, int(parts[1])))
            except ValueError:
                pass

        records = await self.db.get_group_recent_words(user_id, group_id, limit)
        if not records:
            yield event.plain_result("📭 你的单词本还是空的，快发送 /今日单词 开始学习吧！")
            return

        d = "━━━━━━━━━━━━━━"
        lines = [f"📒 最近学过的 {len(records)} 个单词", d]
        for i, r in enumerate(records, 1):
            word_detail = await self.db.get_word(r["word"])
            meaning = word_detail["meaning"] if word_detail else ""
            lines.append(f"{i}. {r['word']} - {meaning}")
        yield event.plain_result("\n".join(lines))

    @filter.command("排行榜")
    async def rank_board(self, event: AstrMessageEvent):
        """Generate group learning leaderboard (group chat only)."""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("🏆 排行榜仅在群聊中可用哦！")
            return

        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)

        users = await self.db.get_group_users(group_id, limit=50)
        if not users:
            yield event.plain_result("🏆 暂无人参与学习，快来成为第一个吧！")
            return

        d = "━━━━━━━━━━━━━━"
        lines = [f"🏆 群内学习排行榜", f"共 {len(users)} 人参与学习", d]
        for i, u in enumerate(users[:10], 1):
            me = " ←你" if u.get("user_id") == user_id else ""
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            native = u.get("native_id", "Unknown")[:10]
            glearned = u.get("group_learned", 0)
            gstreak = u.get("group_streak", 0)
            lines.append(
                f"{medal} #{i} {native}  "
                f"📚 {glearned}词  "
                f"🔥 {gstreak}天{me}"
            )
        yield event.plain_result("\n".join(lines))

    @filter.command("设置目标")
    async def set_target(self, event: AstrMessageEvent):
        """Set daily learning target. Usage: /设置目标 <数字>"""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)

        msg = event.message_str.strip()
        parts = msg.split()
        if len(parts) < 2:
            yield event.plain_result("🎯 用法: /设置目标 <数字>\n例如: /设置目标 15")
            return

        try:
            target = int(parts[1])
            if target < 1 or target > 1000:
                yield event.plain_result("🎯 目标数量需要在 1~1000 之间哦！")
                return
        except ValueError:
            yield event.plain_result("🎯 请输入有效的数字！")
            return

        await self.db.update_user_target(user_id, target)
        yield event.plain_result(f"🎯 每日学习目标已设置为 {target} 词！加油！")

    @filter.command("推送设置")
    async def push_settings(self, event: AstrMessageEvent):
        """Set daily auto-push. Usage: /推送设置 on/off/qq号"""
        if not event.is_private_chat() and not event.is_admin():
            yield event.plain_result("⛔ 推送设置仅限私聊或群管理员使用！")
            return

        msg = event.message_str.strip()
        parts = msg.split()
        if len(parts) < 2:
            push_cfg = self.config.get("daily_push", {})
            status = "开启" if push_cfg.get("enabled") else "关闭"
            tid = push_cfg.get("target_id", "未设置")
            ttype = push_cfg.get("target_type", "private")
            yield event.plain_result(
                f"📢 当前推送状态: {status}\n"
                f"目标类型: {ttype}\n"
                f"目标ID: {tid}\n"
                f"推送时间: {push_cfg.get('push_time', '08:00')}\n"
                f"用法: /推送设置 on | /推送设置 off | /推送设置 qq号"
            )
            return

        arg = parts[1].strip().lower()
        push_cfg = self.config.get("daily_push", {})

        if arg in ("on", "off"):
            push_cfg["enabled"] = arg == "on"
            if arg == "on":
                if not push_cfg.get("target_id"):
                    group_id = event.get_group_id()
                    if group_id:
                        push_cfg["target_type"] = "group"
                        push_cfg["target_id"] = group_id
                    else:
                        push_cfg["target_type"] = "private"
                        push_cfg["target_id"] = event.get_sender_id()
            self.config["daily_push"] = push_cfg
            if hasattr(self.config, "save_config"):
                self.config.save_config()
            await self.scheduler.schedule(self.config)
            status = "开启" if push_cfg["enabled"] else "关闭"
            target = push_cfg.get("target_id", "未设置")
            yield event.plain_result(f"📢 自动推送已{status}！目标: {push_cfg.get('target_type','private')}:{target}")
        else:
            push_cfg["enabled"] = True
            push_cfg["target_id"] = arg
            push_cfg["target_type"] = "private"
            self.config["daily_push"] = push_cfg
            if hasattr(self.config, "save_config"):
                self.config.save_config()
            await self.scheduler.schedule(self.config)
            yield event.plain_result(f"📢 已设置自动推送到 {arg}，将在每天 {push_cfg.get('push_time', '08:00')} 推送！")
