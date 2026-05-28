import json
import os
import random
from pathlib import Path
from typing import Optional

from astrbot.api import logger


class WordBankLoader:
    def __init__(self, db, json_path: Optional[str] = None):
        self.db = db
        self.json_path = json_path or os.path.join(
            os.path.dirname(__file__), "cet4_words.json"
        )

    async def ensure_loaded(self, category: str = "cet4"):
        count = await self.db.count_words(category)
        if count > 0:
            return
        if not os.path.exists(self.json_path):
            logger.warning(f"Word bank JSON not found: {self.json_path}")
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                words = json.load(f)
            await self.db.import_words(words)
            logger.info(f"Imported {len(words)} words into word_bank.")
        except Exception as e:
            logger.error(f"Failed to load word bank: {e}")

    async def pick_new_word(self, user_id: str, group_id: str = "", category: str = None, include_learned: bool = False):
        learned = await self.db.get_user_learned_words(user_id)
        learned_set = {r["word"] for r in learned}

        if include_learned:
            exclude = []
        else:
            exclude = list(learned_set)

        words = await self.db.pick_random_words(exclude, category=category, limit=1)
        if not words:
            return None

        word = words[0]
        word["is_learned"] = word["word"] in learned_set
        return word

    async def pick_review_word(self, user_id: str, group_id: str = ""):
        learned = await self.db.get_user_learned_words(user_id)
        if not learned:
            return None
        word_entry = random.choice(learned)
        word_detail = await self.db.get_word(word_entry["word"])
        return word_detail
