import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import settings
from database import get_pending_reminders, mark_reminder_sent
from whatsapp_client import send_message
from ai_brain import generate_daily_summary, generate_weekly_summary

logger = logging.getLogger(__name__)
TZ = ZoneInfo(settings.TIMEZONE)
_running = True

async def start_scheduler():
    global _running
    _running = True
    logger.info("Scheduler started")
    while _running:
        try:
            now = datetime.now(tz=TZ)
            await check_reminders(now)
            await check_summaries(now)
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        await asyncio.sleep(30)

async def stop_scheduler():
    global _running
    _running = False

async def check_reminders(now):
    pending = await get_pending_reminders(now)
    for reminder in pending:
        text = f"🔔 *תזכורת:* {reminder['text']}"
        sent = await send_message(settings.MY_PHONE_NUMBER, text)
        if sent:
            if reminder["is_recurring"] and reminder["recur_rule"]:
                next_time = calc_next(
                    datetime.fromisoformat(reminder["remind_at"]).replace(tzinfo=TZ),
                    reminder["recur_rule"]
                )
                await mark_reminder_sent(reminder["id"], next_time)
            else:
                await mark_reminder_sent(reminder["id"])

async def check_summaries(now):
    dh, dm = map(int, settings.DAILY_SUMMARY_TIME.split(":"))
    wh, wm = map(int, settings.WEEKLY_SUMMARY_TIME.split(":"))
    if now.hour == dh and now.minute == dm:
        summary = await generate_daily_summary()
        await send_message(settings.MY_PHONE_NUMBER, f"☀️ *סיכום יומי*\n\n{summary}")
    if now.weekday() == settings.WEEKLY_SUMMARY_DAY and now.hour == wh and now.minute == wm:
        summary = await generate_weekly_summary()
        await send_message(settings.MY_PHONE_NUMBER, f"📊 *סיכום שבועי*\n\n{summary}")

def calc_next(current, rule):
    if rule == "daily":
        return current + timedelta(days=1)
    elif rule == "weekly":
        return current + timedelta(weeks=1)
    return current + timedelta(days=1)
