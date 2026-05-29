import os
import subprocess
from datetime import datetime
import random
import urllib.request
import io

from astrbot.api import logger
from astrbot.core.platform.message_session import MessageSession
from astrbot.core.platform.message_type import MessageType
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.api.message_components import Image, Plain

from PIL import Image as PILImage, ImageDraw, ImageFont


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

class PushScheduler:
    def __init__(self, context, db, wordbank_loader):
        self.context = context
        self.db = db
        self.wordbank_loader = wordbank_loader
        self._job_id = None
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.bg_cache_dir = os.path.join(plugin_dir, "bg_cache")
        os.makedirs(self.bg_cache_dir, exist_ok=True)

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
                "platform_name": push_cfg.get("platform_name", "aiocqhttp"),
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
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bundled = os.path.join(plugin_dir, "assets", "font.ttf")
        if os.path.exists(bundled):
            try:
                return ImageFont.truetype(bundled, size)
            except Exception:
                pass

        # 1. Dynamic discovery via fontconfig (Linux)
        path = PushScheduler._find_font_by_fc("zh")
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

        logger.warning("No CJK font found, Chinese characters will render as boxes. "
                       "Install fonts-wqy-zenhei or fonts-noto-cjk on your server.")

        # 3. Auto-download fallback
        path = PushScheduler._ensure_cjk_font()
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
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        path = PushScheduler._find_font_by_fc("en")
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
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    def _render_word_image(self, word: dict) -> str:
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
        draw.text((W // 2, 30), "今日单词推送", fill="#ffffff", font=ft_tag, anchor="mt")

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

        # Footer (no emoji)
        draw.text((W // 2, H - 30), "早安！新的一天从学习开始 ~", fill="#e2e8f0", font=ft_stat, anchor="mm")

        # Save to AstrBot temp dir
        temp_dir = get_astrbot_temp_path()
        os.makedirs(temp_dir, exist_ok=True)
        fname = f"word_push_{word.get('word','')}_{int(datetime.now().timestamp())}.png"
        out_path = os.path.join(temp_dir, fname)
        img.save(out_path, "PNG")
        return out_path

    async def _on_push(self, target_type: str, target_id: str, platform_name: str = "aiocqhttp", include_learned: bool = False):
        logger.info(f"Daily push triggered for {platform_name}:{target_type}:{target_id}")

        today = datetime.now().strftime("%Y-%m-%d")
        group_id = target_id if target_type == "group" else ""

        user_id = f"cron_{target_id}"
        user = await self.db.get_user(user_id)
        if not user:
            await self.db.create_user(user_id, "cron", target_id)
            user = await self.db.get_user(user_id)

        word = await self.wordbank_loader.pick_new_word(user_id, group_id=group_id, include_learned=include_learned)
        if not word:
            logger.info("No new words available for push.")
            return

        await self.db.add_learning_record(user_id, group_id, word["word"], today)

        # Query fresh stats from DB (not stale user snapshot)
        total = await self.db.get_global_total_learned(user_id)
        last_checkin = await self.db.get_user_last_checkin(user_id)

        streak = 1
        if last_checkin and last_checkin != today:
            last_dt = datetime.strptime(last_checkin, "%Y-%m-%d")
            if (datetime.now() - last_dt).days == 1:
                streak = await self.db.get_global_streak(user_id)
        if last_checkin == today:
            streak = await self.db.get_global_streak(user_id)

        today_learned = await self.db.get_user_today_learned(user_id, today)
        await self.db.update_user_checkin(user_id, today, streak, total, today_learned)

        img_path = self._render_word_image(word)

        # Find the platform adapter that matches the stored platform name
        platform_inst = None
        for p in self.context.platform_manager.get_insts():
            if p.meta().name == platform_name:
                platform_inst = p
                break

        if platform_inst is None:
            logger.error(f"Failed to send push: no platform adapter found with name '{platform_name}'.")
            return

        mt = MessageType.FRIEND_MESSAGE if target_type == "private" else MessageType.GROUP_MESSAGE
        session = MessageSession(
            platform_name=platform_inst.meta().id,
            message_type=mt,
            session_id=target_id,
        )

        try:
            from astrbot.api.message_components import Plain
            text = "🌅 早安！今日单词已送达 ~\n💡 发送 /今日单词 开始学习，/复习单词 巩固记忆"
            chain = [Plain(text), Image.fromFileSystem(img_path)]
            await platform_inst.send_by_session(session, chain)
            logger.info("Daily push sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send push message: {e}")
