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
            await db.execute("UPDATE reminders SET remind_at = ? WHERE id = ?",
                           (next_time.isoformat(), reminder_id))
        else:
            await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()

async def list_reminders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM reminders WHERE sent = 0 ORDER BY remind_at")
        return [dict(r) for r in await cur.fetchall()]

async def add_task(text, priority="normal", monday_item_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tasks (text, priority, monday_item_id) VALUES (?, ?, ?)",
            (text, priority, monday_item_id))
        await db.commit()
        return cur.lastrowid

async def list_tasks(include_done=False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_done:
            cur = await db.execute("SELECT * FROM tasks ORDER BY done, created_at")
        else:
            cur = await db.execute("SELECT * FROM tasks WHERE done = 0 ORDER BY priority DESC, created_at")
        return [dict(r) for r in await cur.fetchall()]

async def get_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def complete_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET done = 1, done_at = datetime('now') WHERE id = ?", (task_id,))
        await db.commit()

async def delete_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

async def save_memory(category, key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO memory (category, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(category, key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (category, key, value))
        await db.commit()

async def get_all_memory():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM memory ORDER BY category, key")
        return [dict(r) for r in await cur.fetchall()]

async def save_message(role, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        await db.commit()

async def get_recent_messages(limit=16):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        return [dict(r) for r in reversed(rows)]
