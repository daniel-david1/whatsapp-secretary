import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from config import settings
from database import add_reminder, add_task, complete_task, delete_task, save_memory, save_message, get_task
from ai_brain import process_message
from whatsapp_client import parse_incoming, send_message
from monday_client import create_monday_task, close_monday_task

logger = logging.getLogger(__name__)
TZ = ZoneInfo(settings.TIMEZONE)

async def handle_incoming_message(body: dict):
    msg = parse_incoming(body)
    if not msg:
        return
    phone = msg["phone"]
    text = msg["text"]
    logger.info(f"Message from {phone}: {text[:80]}")
    await save_message("user", text)
    result = await process_message(text)
    cal_links = []
    for action in result.get("actions", []):
        cal_link = await execute_action(action)
        if cal_link:
            cal_links.append(cal_link)
    if cal_links:
        result["reply"] = result.get("reply", "") + "\n\n📅 הוסף ליומן: " + cal_links[0]
    reply = result.get("reply", "")
    if reply:
        await save_message("assistant", reply)
        await send_message(phone, reply)

async def execute_action(action: dict):
    action_type = action.get("type", "")
    logger.info(f"Executing: {action_type}")
    try:
        if action_type == "add_reminder":
            remind_at = datetime.fromisoformat(action["remind_at"]).replace(tzinfo=TZ)
            await add_reminder(
                text=action["text"],
                remind_at=remind_at,
                is_recurring=action.get("is_recurring", False),
                recur_rule=action.get("recur_rule")
            )
            # הוסף קישור Google Calendar לתשובה
            cal_text = action["text"].replace(" ", "+")
            cal_start = remind_at.strftime("%Y%m%dT%H%M%S")
            cal_end = remind_at.strftime("%Y%m%dT%H%M%S")
          cal_link = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={cal_text}&dates={cal_start}/{cal_end}"
            return cal_link

        elif action_type == "add_task":
            monday_id = await create_monday_task(action["text"], action.get("priority", "normal"))
            await add_task(
                text=action["text"],
                priority=action.get("priority", "normal"),
                monday_item_id=monday_id
            )

        elif action_type == "complete_task":
            task = await get_task(action["task_id"])
            if task and task.get("monday_item_id"):
                await close_monday_task(task["monday_item_id"])
            await complete_task(action["task_id"])

        elif action_type == "delete_task":
            await delete_task(action["task_id"])

        elif action_type == "save_memory":
            await save_memory(action["category"], action["key"], action["value"])

    except Exception as e:
        logger.error(f"Error in action {action_type}: {e}", exc_info=True)
