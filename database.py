import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_conn():
    import psycopg
    return psycopg.connect(DATABASE_URL)

def init_db_sync():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            is_recurring INTEGER DEFAULT 0,
            recur_rule TEXT,
            sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT now()::text
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            priority TEXT DEFAULT 'normal',
            done INTEGER DEFAULT 0,
            monday_item_id TEXT,
            created_at TEXT DEFAULT now()::text,
            done_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT now()::text,
            UNIQUE(category, key)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT now()::text
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database ready")

async def init_db():
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, init_db_sync)

async def add_reminder(text, remind_at, is_recurring=False, recur_rule=None):
    def _run():
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO reminders (text, remind_at, is_recurring, recur_rule) VALUES (%s, %s, %s, %s) RETURNING id",
            (text, remind_at.isoformat(), int(is_recurring), recur_rule))
        row_id = cur.fetchone()[0]
        conn.commit(); conn.close()
        return row_id
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_pending_reminders(now):
    def _run():
        conn = get_conn()
        cur = conn.execute(
            "SELECT id, text, remind_at, is_recurring, recur_rule, sent FROM reminders WHERE remind_at <= %s AND sent = 0 ORDER BY remind_at",
            (now.isoformat(),))
        rows = [{"id": r[0], "text": r[1], "remind_at": r[2], "is_recurring": r[3], "recur_rule": r[4], "sent": r[5]} for r in cur.fetchall()]
        conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def mark_reminder_sent(reminder_id, next_time=None):
    def _run():
        conn = get_conn()
        if next_time:
            conn.execute("UPDATE reminders SET remind_at = %s WHERE id = %s", (next_time.isoformat(), reminder_id))
        else:
            conn.execute("UPDATE reminders SET sent = 1 WHERE id = %s", (reminder_id,))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def list_reminders():
    def _run():
        conn = get_conn()
        cur = conn.execute("SELECT id, text, remind_at, is_recurring, recur_rule FROM reminders WHERE sent = 0 ORDER BY remind_at")
        rows = [{"id": r[0], "text": r[1], "remind_at": r[2], "is_recurring": r[3], "recur_rule": r[4]} for r in cur.fetchall()]
        conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def add_task(text, priority="normal", monday_item_id=None):
    def _run():
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO tasks (text, priority, monday_item_id) VALUES (%s, %s, %s) RETURNING id",
            (text, priority, monday_item_id))
        row_id = cur.fetchone()[0]
        conn.commit(); conn.close()
        return row_id
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def list_tasks(include_done=False):
    def _run():
        conn = get_conn()
        if include_done:
            cur = conn.execute("SELECT id, text, priority, done, monday_item_id FROM tasks ORDER BY done, created_at")
        else:
            cur = conn.execute("SELECT id, text, priority, done, monday_item_id FROM tasks WHERE done = 0 ORDER BY priority DESC, created_at")
        rows = [{"id": r[0], "text": r[1], "priority": r[2], "done": r[3], "monday_item_id": r[4]} for r in cur.fetchall()]
        conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_task(task_id):
    def _run():
        conn = get_conn()
        cur = conn.execute("SELECT id, text, priority, done, monday_item_id FROM tasks WHERE id = %s", (task_id,))
        r = cur.fetchone()
        conn.close()
        if r:
            return {"id": r[0], "text": r[1], "priority": r[2], "done": r[3], "monday_item_id": r[4]}
        return None
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def complete_task(task_id):
    def _run():
        conn = get_conn()
        conn.execute("UPDATE tasks SET done = 1, done_at = now()::text WHERE id = %s", (task_id,))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def delete_task(task_id):
    def _run():
        conn = get_conn()
        conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def save_memory(category, key, value):
    def _run():
        conn = get_conn()
        conn.execute(
            "INSERT INTO memory (category, key, value) VALUES (%s, %s, %s) ON CONFLICT(category, key) DO UPDATE SET value=%s, updated_at=now()::text",
            (category, key, value, value))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_all_memory():
    def _run():
        conn = get_conn()
        cur = conn.execute("SELECT category, key, value FROM memory ORDER BY category, key")
        rows = [{"category": r[0], "key": r[1], "value": r[2]} for r in cur.fetchall()]
        conn.close()
        return rows
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def save_message(role, content):
    def _run():
        conn = get_conn()
        conn.execute("INSERT INTO messages (role, content) VALUES (%s, %s)", (role, content))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_recent_messages(limit=16):
    def _run():
        conn = get_conn()
        cur = conn.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT %s", (limit,))
        rows = [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
        conn.close()
        return list(reversed(rows))
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)
