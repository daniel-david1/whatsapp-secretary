import json
import logging
from datetime import datetime
from anthropic import AsyncAnthropic
from config import settings
from database import get_recent_messages, get_all_memory, list_tasks, list_reminders

logger = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """אתה מזכירה אישית חכמה בוואטסאפ. אתה עוזר למשתמש לנהל תזכורות, משימות, וזיכרון אישי.
כל משימה שנוצרת נפתחת גם ב-Monday CRM אוטומטית, וכשהמשתמש אומר שסיים — היא נסגרת שם.

הזמן הנוכחי: {current_time}
אזור זמן: {timezone}

== מידע שמור על המשתמש ==
{memory}

== משימות פתוחות ==
{tasks}

== תזכורות קרובות ==
{reminders}

החזר JSON בלבד, ללא טקסט נוסף:

{{
  "actions": [],
  "reply": "התשובה שתשלח למשתמש"
}}

סוגי פעולות אפשריות:

הוספת משימה (נפתחת גם ב-Monday):
{{"type": "add_task", "text": "שם המשימה", "priority": "normal"}}
priority: low / normal / high

סימון משימה כהושלמה (נסגרת גם ב-Monday):
{{"type": "complete_task", "task_id": 3}}

הוספת תזכורת:
{{"type": "add_reminder", "text": "טקסט", "remind_at": "2024-01-15T09:00:00", "is_recurring": false, "recur_rule": null}}

תזכורת חוזרת יומית:
{{"type": "add_reminder", "text": "לשתות מים", "remind_at": "2024-01-15T08:00:00", "is_recurring": true, "recur_rule": "daily"}}

שמירת מידע אישי:
{{"type": "save_memory", "category": "preference", "key": "מפתח", "value": "ערך"}}

הנחיות תשובה:
- דבר בעברית, ידידותי וקצר
- אשר פעולות שביצעת
- השתמש ב ✅ 🔔 📝 לרשימות
- ציין מתי תישלח תזכורת
- כשמוסיף משימה — ציין שנפתחה גם ב-Monday
"""

async def build_context() -> dict:
    memory = await get_all_memory()
    tasks = await list_tasks()
    reminders = await list_reminders()

    memory_str = "\n".join(
        f"  [{m['category']}] {m['key']}: {m['value']}" for m in memory
    ) or "  (אין מידע שמור)"

    tasks_str = "\n".join(
        f"  #{t['id']} [{t['priority']}] {t['text']}" for t in tasks
    ) or "  (אין משימות פתוחות)"

    reminders_str = "\n".join(
        f"  #{r['id']} {r['remind_at']}: {r['text']}" for r in reminders[:10]
    ) or "  (אין תזכורות)"

    return {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M (%A)"),
        "timezone": settings.TIMEZONE,
        "memory": memory_str,
        "tasks": tasks_str,
        "reminders": reminders_str,
    }

async def process_message(user_message: str) -> dict:
    context = await build_context()
    system = SYSTEM_PROMPT.format(**context)
    history = await get_recent_messages(limit=16)
    messages = history + [{"role": "user", "content": user_message}]

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=messages
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        logger.error(f"Claude error: {e}", exc_info=True)
        return {"actions": [], "reply": "שגיאה זמנית, נסה שוב 🙏"}

async def generate_daily_summary() -> str:
    context = await build_context()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": f"צור סיכום בוקר קצר עם ברכה, משימות פתוחות ותזכורות להיום:\nמשימות: {context['tasks']}\nתזכורות: {context['reminders']}"}]
    )
    return response.content[0].text

async def generate_weekly_summary() -> str:
    context = await build_context()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": f"צור סיכום שבועי קצר עם משימות פתוחות ותזכורות לשבוע:\nמשימות: {context['tasks']}\nתזכורות: {context['reminders']}"}]
    )
    return response.content[0].text
