import os
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import io

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path

from PIL import Image as PILImage, ImageDraw, ImageFont

from .database import WordDatabase
from .wordbank import WordBankLoader
from .tasks import PushScheduler


THEME_COLORS = [
    "#2F4F4F",  # 深石板灰
    "#4B0082",  # 靛蓝
    "#006400",  # 深绿
    "#8B0000",  # 深红
    "#2F2F4F",  # 深紫蓝
    "#4A4A6A",  # 灰紫
    "#1a1a2e",  # 深夜蓝
    "#16213e",  # 海军蓝
    "#0f3460",  # 深蓝
    "#533483",  # 紫罗兰
]

CDN_BACKGROUNDS = [
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/alex-he-IGsLkWL4JMM-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/andrei-r-popescu-zHyr6DRoxFo-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/angelina-kusznirewicz--lCQhQ1Ueik-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/cai-fang-B47KcMR2eNY-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/eduard-pretsi-tzxzXecKA-Q-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/eugene-golovesov-TTqfc5TWPcI-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/farnaz-kohankhaki-mAIPCIDOcjk-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/fer-troulik-9EnnPbqiJbk-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/hanvin-cheong-0zr1TG4qRos-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/jisang-jung-HB1kt6cVz2E-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/junel-mujar-Po8CZAwyy6w-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/kristaps-ungurs-aaEwFuzBrDA-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/land-o-lakes-inc-9w6Qb-dqBwE-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/land-o-lakes-inc-TQSvFz7NHuo-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/lcs-_vgt-pZYzbpu_9bk-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/lens-by-benji-_jF2nXuu9AA-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/liana-s-3bPnXCN0ZUs-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/louis-gaudiau-7Z94A-v9kvw-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/magicpattern-87PP9Zd7MNo-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/marek-piwnicki-lm_CeNw9bH4-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/nemo-jDcjw0jCfv0-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/oleksandra-nadtocha-mRcd6AWsX3I-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/pascal-debrunner-ob8DTqyLzME-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/pavel-moiseev-6OyIuRmctNY-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/robert-visual-diary-berlin-4ic17Co0d6k-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/rod-long-liGPSuWK4ek-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/rod-long-o_npS9MnX34-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/roman-0OZK7ciERRM-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/samuel-quek-EBTXvQuVX08-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/samuel-quek-zg9nNEvqytQ-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/spencer-plouzek-ZcQ0g_frEck-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/takashi-s-EG_Yvw7tzV4-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/the-walters-art-museum-gjIIkr9-8qc-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/tobias-reich-BG3PSRcTOik-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/tobias-reich-n36_NSOBLnw-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/tobias-reich-UgiiLFskUCw-unsplash.jpg",
    "https://tuchuang12.oss-cn-hangzhou.aliyuncs.com/photos/wallace-henry--r5wlBxk9NA-unsplash.jpg",
]

class DailyWordPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.plugin_dir, "data.db")
        self.bg_cache_dir = os.path.join(self.plugin_dir, "bg_cache")
        os.makedirs(self.bg_cache_dir, exist_ok=True)
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
        return f"{event.get_platform_name()}:{event.get_sender_id()}"

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

    # ---------- PIL Image Rendering ----------

    @staticmethod
    def _find_font_by_fc(lang: str = "zh"):
        """Use fc-list to discover system fonts dynamically."""
        try:
            result = subprocess.run(
                ["fc-list", f":lang={lang}", "file"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    path = line.split(":")[0].strip()
                    if path and os.path.exists(path):
                        return path
        except Exception:
            pass
        return None

    @staticmethod
    def _get_font(size: int):
        """Try to load a CJK-capable font, fallback to default."""
        # 0. Bundled font (always available)
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        bundled = os.path.join(plugin_dir, "assets", "font.ttf")
        if os.path.exists(bundled):
            try:
                return ImageFont.truetype(bundled, size)
            except Exception:
                pass

        # 1. Dynamic discovery via fontconfig (Linux)
        path = DailyWordPlugin._find_font_by_fc("zh")
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

        # 2. Static fallback paths
        candidates = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue

        # 3. Auto-download fallback
        path = DailyWordPlugin._ensure_cjk_font()
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

        logger.warning("No CJK font found, Chinese characters will render as boxes.")
        return ImageFont.load_default()

    @staticmethod
    def _ensure_cjk_font():
        """Auto-download a CJK font if none found on the system. Returns path or None."""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(plugin_dir, "bg_cache")
        font_path = os.path.join(font_dir, "NotoSansCJKsc-Regular.otf")

        if os.path.exists(font_path) and os.path.getsize(font_path) > 100000:
            return font_path

        urls = [
            "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
            "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
        ]
        for url in urls:
            try:
                logger.info(f"Downloading CJK font for Chinese rendering...")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                with open(font_path, "wb") as f:
                    f.write(data)
                logger.info(f"CJK font saved to {font_path}")
                return font_path
            except Exception as e:
                logger.warning(f"Failed to download font from {url}: {e}")
        return None

    @staticmethod
    def _get_phonetic_font(size: int):
        """Try to load a font with IPA phonetic symbol support."""
        # 1. Dynamic discovery via fontconfig (Linux)
        path = DailyWordPlugin._find_font_by_fc("en")
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

        # 2. Static fallback paths
        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue

        # 3. Fallback to bundled CJK font (usually has basic IPA)
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        bundled = os.path.join(plugin_dir, "assets", "font.ttf")
        if os.path.exists(bundled):
            try:
                return ImageFont.truetype(bundled, size)
            except Exception:
                pass

        return ImageFont.load_default()

    def _get_background(self):
        """Load background from local cache, download if missing."""
        url = random.choice(CDN_BACKGROUNDS)
        cache_name = url.split("/")[-1]
        cache_path = os.path.join(self.bg_cache_dir, cache_name)

        if os.path.exists(cache_path):
            try:
                return PILImage.open(cache_path).convert("RGB")
            except Exception:
                pass

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            with open(cache_path, "wb") as f:
                f.write(data)
            return PILImage.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            logger.warning(f"Failed to download background, using fallback: {e}")
            return None

    def _render_word_image(
        self,
        word: dict,
        user: dict,
        today_learned: int = 0,
        review_count: int = 0,
    ) -> str:
        """Render a word card using PIL with semi-transparent overlay, save to temp dir."""
        W, H = 600, 700
        theme_color = random.choice(THEME_COLORS)

        # 1. Background layer
        bg_img = self._get_background()
        if bg_img:
            bg_img = bg_img.resize((W, H), PILImage.LANCZOS)
        else:
            # Fallback gradient
            bg_img = PILImage.new("RGB", (W, H), theme_color)
            draw_bg = ImageDraw.Draw(bg_img)
            tc = tuple(int(theme_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            for y in range(H):
                factor = 1.0 - 0.3 * (y / H)
                draw_bg.line([(0, y), (W, y)], fill=(int(tc[0] * factor), int(tc[1] * factor), int(tc[2] * factor)))

        # 2. Semi-transparent overlay layer (so background is visible)
        overlay = PILImage.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_o = ImageDraw.Draw(overlay)

        # Uniform dark overlay
        draw_o.rectangle([0, 0, W, H], fill=(0, 0, 0, 140))

        # Composite
        bg_img = bg_img.convert("RGBA")
        img = PILImage.alpha_composite(bg_img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Fonts
        ft_tag = self._get_font(22)
        ft_word = self._get_font(56)
        ft_phonetic = self._get_phonetic_font(24)
        ft_meaning = self._get_font(28)
        ft_example = self._get_font(22)
        ft_stat = self._get_font(20)
        ft_small = self._get_font(18)

        # Tag (no emoji to avoid garbled text)
        tag = "复习单词" if review_count > 0 else ("已学习" if word.get("is_learned") else "每日单词")
        draw.text((W // 2, 30), tag, fill="#ffffff", font=ft_tag, anchor="mt")

        # Word
        draw.text((W // 2, 85), word.get("word", ""), fill="#ffffff", font=ft_word, anchor="mt")

        # Phonetic
        phonetic = word.get("phonetic", "")
        if phonetic:
            draw.text((W // 2, 150), phonetic, fill="#e2e8f0", font=ft_phonetic, anchor="mt")

        # Meaning
        meaning = word.get("meaning", "")
        if meaning:
            draw.text((48, 230), "释义", fill="#7c3aed", font=ft_small)
            meaning_y = 258
            max_width = W - 96
            words = meaning
            while words:
                bbox = draw.textbbox((0, 0), words, font=ft_meaning)
                if bbox[2] <= max_width:
                    draw.text((48, meaning_y), words, fill="#e2e8f0", font=ft_meaning)
                    break
                low, high = 1, len(words)
                while low < high:
                    mid = (low + high + 1) // 2
                    bbox = draw.textbbox((0, 0), words[:mid], font=ft_meaning)
                    if bbox[2] <= max_width:
                        low = mid
                    else:
                        high = mid - 1
                draw.text((48, meaning_y), words[:low], fill="#e2e8f0", font=ft_meaning)
                words = words[low:].lstrip()
                meaning_y += 38

        # Example
        example = word.get("example", "")
        if example:
            example_y = max(meaning_y + 20, 320)
            draw.text((48, example_y), "例句", fill="#f59e0b", font=ft_small)
            draw.text((48, example_y + 28), f'"{example}"', fill="#d1d5db", font=ft_example)

        # Footer stats (no emoji)
        streak = user.get("streak_days", 0)
        total = user.get("total_learned", 0)
        target = user.get("daily_target", 10)
        stat_text = f"连续 {streak} 天    累计 {total} 词    今日 {today_learned}/{target}"
        draw.text((W // 2, H - 30), stat_text, fill="#e2e8f0", font=ft_stat, anchor="mm")

        # Save to AstrBot temp dir
        temp_dir = get_astrbot_temp_path()
        os.makedirs(temp_dir, exist_ok=True)
        fname = f"word_card_{word.get('word','')}_{int(datetime.now().timestamp())}.png"
        out_path = os.path.join(temp_dir, fname)
        img.save(out_path, "PNG")
        return out_path

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
        """Pick a new word to learn, check in, and send image card."""
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

        # Global user stats (shared across all groups and private chats)
        total = await self.db.get_global_total_learned(user_id)
        today_learned = await self.db.get_user_today_learned(user_id, today)
        last_checkin = await self.db.get_user_last_checkin(user_id)

        streak = 1
        if last_checkin and last_checkin != today:
            last_dt = datetime.strptime(last_checkin, "%Y-%m-%d")
            if (datetime.now() - last_dt).days == 1:
                streak = await self.db.get_global_streak(user_id)
        if last_checkin == today:
            streak = await self.db.get_global_streak(user_id)

        await self.db.update_user_checkin(user_id, today, streak, total, today_learned)
        user = await self.db.get_user(user_id)

        logger.info(f"[today_word] user={user_id} group={group_id} "
                    f"total={total} today={today_learned} streak={streak}")

        img_path = self._render_word_image(word, user, today_learned=today_learned)

        greeting = self._get_greeting()
        bar = self._progress_bar(today_learned, user.get("daily_target", 10))
        target = user.get("daily_target", 10)
        remain = max(0, target - today_learned)

        footer_lines = [
            f"━━━━━━━━━━━━━━",
            f"📊 今日进度  {bar}  {today_learned}/{target}",
            f"🔥 连续打卡 {streak} 天  |  📚 累计学习 {total} 词",
            f"━━━━━━━━━━━━━━",
        ]
        if today_learned >= target:
            footer_lines.append("🎉 太棒了！今日目标已达成！")
        else:
            footer_lines.append(f"💪 还差 {remain} 个单词达成今日目标，加油！")
        footer_lines.append("💡 /复习单词 巩固记忆  ·  /我的进度 查看详情")

        text = greeting + "\n" + "\n".join(footer_lines)
        yield event.chain_result([
            Plain(text),
            Image.fromFileSystem(img_path),
        ])

    @filter.command("复习单词")
    async def review_word(self, event: AstrMessageEvent):
        """Pick a learned word to review."""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)
        group_id = self._get_group_id(event)

        learned = await self.db.get_user_learned_words(user_id)
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

        # Global user stats
        total = await self.db.get_global_total_learned(user_id)
        today_learned = await self.db.get_user_today_learned(user_id, today)
        streak = await self.db.get_global_streak(user_id)

        img_path = self._render_word_image(word, user, today_learned=today_learned, review_count=review_count)

        bar = self._progress_bar(today_learned, user.get("daily_target", 10))

        footer_lines = [
            f"━━━━━━━━━━━━━━",
            f"📊 今日进度  {bar}  {today_learned}/{user.get('daily_target', 10)}",
            f"🔥 连续打卡 {streak} 天  |  📚 累计学习 {total} 词",
            f"━━━━━━━━━━━━━━",
            f"📝 这是第 {review_count} 次复习这个单词",
            "💡 /今日单词 学习新词  ·  /单词本 查看已学",
        ]

        logger.info(f"[review_word] user={user_id} group={group_id} "
                    f"total={total} today={today_learned} streak={streak}")

        text = "🔄 来复习一下，温故知新 ~\n" + "\n".join(footer_lines)
        yield event.chain_result([
            Plain(text),
            Image.fromFileSystem(img_path),
        ])

    @filter.command("我的进度")
    async def my_progress(self, event: AstrMessageEvent):
        """Show personal learning progress."""
        user = await self._ensure_user(event)
        user_id = self._get_user_id(event)
        group_id = self._get_group_id(event)
        today = self._get_today()

        total = await self.db.get_global_total_learned(user_id)
        today_learned = await self.db.get_user_today_learned(user_id, today)
        streak = await self.db.get_global_streak(user_id)
        last_checkin = await self.db.get_user_last_checkin(user_id)

        d = "━━━━━━━━━━━━━━"
        lines = ["📊 我的学习进度", d]
        lines.append(f"🔥 连续打卡: {streak} 天")
        lines.append(f"📚 累计学习: {total} 词")
        lines.append(f"📊 今日已学: {today_learned} 词")
        lines.append(f"📅 最后打卡: {last_checkin or '无'}")
        lines.append(f"🎯 每日目标: {user.get('daily_target', 10)} 词")
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

        records = await self.db.get_user_recent_words(user_id, limit)
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
                push_cfg["platform_name"] = event.get_platform_name()
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
            push_cfg["platform_name"] = event.get_platform_name()
            self.config["daily_push"] = push_cfg
            if hasattr(self.config, "save_config"):
                self.config.save_config()
            await self.scheduler.schedule(self.config)
            yield event.plain_result(f"📢 已设置自动推送到 {arg}，将在每天 {push_cfg.get('push_time', '08:00')} 推送！")
