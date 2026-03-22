import os
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_db_sync():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
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
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database ready")

async def init_db():
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, init_db_sync)

async def add_reminder(text, remind_at, is_recurring=False, recur_rule=None):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reminders (text, remind_at, is_recurring, recur_rule) VALUES (%s, %s, %s, %s) RETURNING id",
            (text, remind_at.isoformat(), int(is_recurring), recur_rule))
        row_id = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return row_id
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_pending_reminders(now):
    def _run():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM reminders WHERE remind_at <= %s AND sent = 0 ORDER BY remind_at", (now.isoformat(),))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def mark_reminder_sent(reminder_id, next_time=None):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        if next_time:
            cur.execute("UPDATE reminders SET remind_at = %s WHERE id = %s", (next_time.isoformat(), reminder_id))
        else:
            cur.execute("UPDATE reminders SET sent = 1 WHERE id = %s", (reminder_id,))
        conn.commit(); cur.close(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def list_reminders():
    def _run():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM reminders WHERE sent = 0 ORDER BY remind_at")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def add_task(text, priority="normal", monday_item_id=None):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tasks (text, priority, monday_item_id) VALUES (%s, %s, %s) RETURNING id",
            (text, priority, monday_item_id))
        row_id = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return row_id
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def list_tasks(include_done=False):
    def _run():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if include_done:
            cur.execute("SELECT * FROM tasks ORDER BY done, created_at")
        else:
            cur.execute("SELECT * FROM tasks WHERE done = 0 ORDER BY priority DESC, created_at")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_task(task_id):
    def _run():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        return dict(row) if row else None
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def complete_task(task_id):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE tasks SET done = 1, done_at = now()::text WHERE id = %s", (task_id,))
        conn.commit(); cur.close(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def delete_task(task_id):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit(); cur.close(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def save_memory(category, key, value):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO memory (category, key, value) VALUES (%s, %s, %s) ON CONFLICT(category, key) DO UPDATE SET value=%s, updated_at=now()::text",
            (category, key, value, value))
        conn.commit(); cur.close(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_all_memory():
    def _run():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM memory ORDER BY category, key")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def save_message(role, content):
    def _run():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (role, content) VALUES (%s, %s)", (role, content))
        conn.commit(); cur.close(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_recent_messages(limit=16):
    def _run():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT %s", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return list(reversed(rows))
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)
