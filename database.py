import os
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "/tmp/secretary.db"

def get_conn():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_sync():
    conn = get_conn()
    conn.executescript("""
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
            "INSERT INTO reminders (text, remind_at, is_recurring, recur_rule) VALUES (?, ?, ?, ?)",
            (text, remind_at.isoformat(), int(is_recurring), recur_rule))
        conn.commit(); row_id = cur.lastrowid; conn.close()
        return row_id
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_pending_reminders(now):
    def _run():
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM reminders WHERE remind_at <= ? AND sent = 0 ORDER BY remind_at",
            (now.isoformat(),)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def mark_reminder_sent(reminder_id, next_time=None):
    def _run():
        conn = get_conn()
        if next_time:
            conn.execute("UPDATE reminders SET remind_at = ? WHERE id = ?", (next_time.isoformat(), reminder_id))
        else:
            conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def list_reminders():
    def _run():
        conn = get_conn()
        rows = conn.execute("SELECT * FROM reminders WHERE sent = 0 ORDER BY remind_at").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def add_task(text, priority="normal", monday_item_id=None):
    def _run():
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO tasks (text, priority, monday_item_id) VALUES (?, ?, ?)",
            (text, priority, monday_item_id))
        conn.commit(); row_id = cur.lastrowid; conn.close()
        return row_id
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def list_tasks(include_done=False):
    def _run():
        conn = get_conn()
        if include_done:
            rows = conn.execute("SELECT * FROM tasks ORDER BY done, created_at").fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks WHERE done = 0 ORDER BY priority DESC, created_at").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_task(task_id):
    def _run():
        conn = get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return dict(row) if row else None
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def complete_task(task_id):
    def _run():
        conn = get_conn()
        conn.execute("UPDATE tasks SET done = 1, done_at = datetime('now') WHERE id = ?", (task_id,))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def delete_task(task_id):
    def _run():
        conn = get_conn()
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def save_memory(category, key, value):
    def _run():
        conn = get_conn()
        conn.execute(
            "INSERT INTO memory (category, key, value) VALUES (?, ?, ?) ON CONFLICT(category, key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (category, key, value))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_all_memory():
    def _run():
        conn = get_conn()
        rows = conn.execute("SELECT * FROM memory ORDER BY category, key").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)

async def save_message(role, content):
    def _run():
        conn = get_conn()
        conn.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        conn.commit(); conn.close()
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, _run)

async def get_recent_messages(limit=16):
    def _run():
        conn = get_conn()
        rows = conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return list(reversed([dict(r) for r in rows]))
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _run)
