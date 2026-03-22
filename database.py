import os
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursorlogger = logging.getLogger(__name__)
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                is_recurring INTEGER DEFAULT 0,
                recur_rule TEXT,
                sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT now()::text
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                done INTEGER DEFAULT 0,
                monday_item_id TEXT,
                created_at TEXT DEFAULT now()::text,
                done_at TEXT
            );
            CREATE TABLE IF NOT EXISTS memory (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT now()::text,
                UNIQUE(category, key)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT now()::text
            );
        """)
    logger.info("Database ready")

async def add_reminder(text, remind_at, is_recurring=False, recur_rule=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO reminders (text, remind_at, is_recurring, recur_rule) VALUES ($1, $2, $3, $4) RETURNING id",
            text, remind_at.isoformat(), int(is_recurring), recur_rule)
        return row["id"]

async def get_pending_reminders(now):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM reminders WHERE remind_at <= $1 AND sent = 0 ORDER BY remind_at",
            now.isoformat())
        return [dict(r) for r in rows]

async def mark_reminder_sent(reminder_id, next_time=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if next_time:
            await conn.execute("UPDATE reminders SET remind_at = $1 WHERE id = $2",
                             next_time.isoformat(), reminder_id)
        else:
            await conn.execute("UPDATE reminders SET sent = 1 WHERE id = $1", reminder_id)

async def list_reminders():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM reminders WHERE sent = 0 ORDER BY remind_at")
        return [dict(r) for r in rows]

async def add_task(text, priority="normal", monday_item_id=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO tasks (text, priority, monday_item_id) VALUES ($1, $2, $3) RETURNING id",
            text, priority, monday_item_id)
        return row["id"]

async def list_tasks(include_done=False):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if include_done:
            rows = await conn.fetch("SELECT * FROM tasks ORDER BY done, created_at")
        else:
            rows = await conn.fetch("SELECT * FROM tasks WHERE done = 0 ORDER BY priority DESC, created_at")
        return [dict(r) for r in rows]

async def get_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
        return dict(row) if row else None

async def complete_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE tasks SET done = 1, done_at = now()::text WHERE id = $1", task_id)

async def delete_task(task_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)

async def save_memory(category, key, value):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO memory (category, key, value) VALUES ($1, $2, $3) "
            "ON CONFLICT(category, key) DO UPDATE SET value=$3, updated_at=now()::text",
            category, key, value)

async def get_all_memory():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM memory ORDER BY category, key")
        return [dict(r) for r in rows]

async def save_message(role, content):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO messages (role, content) VALUES ($1, $2)", role, content)

async def get_recent_messages(limit=16):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT $1", limit)
        return [dict(r) for r in reversed(rows)]
