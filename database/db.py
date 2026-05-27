import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class WordDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self):
        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                native_id TEXT NOT NULL,
                streak_days INTEGER DEFAULT 0,
                last_checkin TEXT,
                total_learned INTEGER DEFAULT 0,
                daily_target INTEGER DEFAULT 10,
                today_learned INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                groups TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                word TEXT NOT NULL,
                first_learned TEXT NOT NULL,
                last_review TEXT,
                review_count INTEGER DEFAULT 0,
                proficiency REAL DEFAULT 0.0,
                UNIQUE(user_id, word)
            );
            CREATE TABLE IF NOT EXISTS word_bank (
                word TEXT PRIMARY KEY,
                phonetic TEXT,
                meaning TEXT NOT NULL,
                example TEXT,
                category TEXT NOT NULL,
                frequency INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_lr_user ON learning_records(user_id);
            CREATE INDEX IF NOT EXISTS idx_wb_category ON word_bank(category);
            """
        )
        # Migration: add today_learned if missing
        async with self._conn.execute("PRAGMA table_info(users)") as cursor:
            cols = {row[1] async for row in cursor}
        if "today_learned" not in cols:
            await self._conn.execute("ALTER TABLE users ADD COLUMN today_learned INTEGER DEFAULT 0")
        if "groups" not in cols:
            await self._conn.execute("ALTER TABLE users ADD COLUMN groups TEXT DEFAULT '[]'")
        await self._conn.commit()

    # --- users ---
    async def get_user(self, user_id: str):
        async with self._conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_user(self, user_id: str, platform: str, native_id: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self._conn.execute(
            "INSERT INTO users (user_id, platform, native_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, platform, native_id, now),
        )
        await self._conn.commit()

    async def update_user_checkin(self, user_id: str, today: str, streak: int, total: int, today_learned: int):
        await self._conn.execute(
            "UPDATE users SET last_checkin = ?, streak_days = ?, total_learned = ?, today_learned = ? WHERE user_id = ?",
            (today, streak, total, today_learned, user_id),
        )
        await self._conn.commit()

    async def update_user_target(self, user_id: str, target: int):
        await self._conn.execute(
            "UPDATE users SET daily_target = ? WHERE user_id = ?",
            (target, user_id),
        )
        await self._conn.commit()

    async def update_user_groups(self, user_id: str, group_id: str):
        user = await self.get_user(user_id)
        if not user:
            return
        groups = set(json.loads(user.get("groups") or "[]"))
        groups.add(group_id)
        await self._conn.execute(
            "UPDATE users SET groups = ? WHERE user_id = ?",
            (json.dumps(list(groups)), user_id),
        )
        await self._conn.commit()

    async def get_today_learned(self, user_id: str, today: str) -> int:
        user = await self.get_user(user_id)
        if not user:
            return 0
        if user.get("last_checkin") == today:
            return user.get("today_learned", 0)
        return 0

    async def get_group_users(self, group_id: str, limit: int = 10):
        async with self._conn.execute(
            "SELECT * FROM users WHERE groups LIKE ? ORDER BY total_learned DESC LIMIT ?",
            (f'%"{group_id}"%', limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_users_rank(self, limit: int = 10):
        async with self._conn.execute(
            "SELECT * FROM users ORDER BY total_learned DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- learning_records ---
    async def get_learned_words(self, user_id: str):
        async with self._conn.execute(
            "SELECT word, review_count FROM learning_records WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_recent_words(self, user_id: str, limit: int = 10):
        async with self._conn.execute(
            "SELECT word, first_learned, review_count FROM learning_records WHERE user_id = ? ORDER BY first_learned DESC LIMIT ?",
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_learning_record(self, user_id: str, word: str, today: str):
        await self._conn.execute(
            "INSERT OR IGNORE INTO learning_records (user_id, word, first_learned, last_review, review_count) VALUES (?, ?, ?, ?, ?)",
            (user_id, word, today, today, 1),
        )
        await self._conn.commit()

    async def update_review(self, user_id: str, word: str, today: str):
        await self._conn.execute(
            "UPDATE learning_records SET last_review = ?, review_count = review_count + 1 WHERE user_id = ? AND word = ?",
            (today, user_id, word),
        )
        await self._conn.commit()

    # --- word_bank ---
    async def import_words(self, words: list[dict]):
        for w in words:
            await self._conn.execute(
                "INSERT OR IGNORE INTO word_bank (word, phonetic, meaning, example, category, frequency) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    w["word"],
                    w.get("phonetic", ""),
                    w["meaning"],
                    w.get("example", ""),
                    w.get("category", "cet4"),
                    w.get("frequency", 0),
                ),
            )
        await self._conn.commit()

    async def count_words(self, category: str = None):
        sql = "SELECT COUNT(*) FROM word_bank"
        params = ()
        if category:
            sql += " WHERE category = ?"
            params = (category,)
        async with self._conn.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def pick_random_words(self, exclude: list[str], category: str = None, limit: int = 1):
        placeholders = ",".join(["?"] * len(exclude)) if exclude else ""
        sql = "SELECT * FROM word_bank"
        params = []
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if exclude:
            conditions.append(f"word NOT IN ({placeholders})")
            params.extend(exclude)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)
        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_word(self, word: str):
        async with self._conn.execute(
            "SELECT * FROM word_bank WHERE word = ?", (word,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
