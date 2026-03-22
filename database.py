import aiosqlite
import logging
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)
DB_PATH = settings.DB_PATH

async def init_db():
    import os
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                is_recurring INTEGER DEFAULT 0,
                recur_rule TEXT,
                sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                done INTEGER DEFAULT 0,
                monday_item_id TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                done_at TEXT
            );
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(category, key)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()
    logger.info("Database ready")

async def add_reminder(text, remind_at, is_recurring=False, recur_rule=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO reminders (text, remind_at, is_recurring, recur_rule) VALUES (?, ?, ?, ?)",
            (text, remind_at.isoformat(), int(is_recurring), recur_rule))
        await db.commit()
        return cur.lastrowid

async def get_pending_reminders(now):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM reminders WHERE remind_at <= ? AND sent = 0 ORDER BY remind_at",
            (now.isoformat(),))
        return [dict(r) for r in await cur.fetchall()]

async def mark_reminder_sent(reminder_id, next_time=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if next_time:
            await db.execute("UPDATE reminders SET remind_at = ? WHERE
