import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"

async def create_monday_task(task_name: str, priority: str = "normal") -> str | None:
    """פותח משימה חדשה ב-Monday ומחזיר את ה-ID שלה"""
    priority_map = {"high": "High", "normal": "Medium", "low": "Low"}
    monday_priority = priority_map.get(priority, "Medium")

    query = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
        create_item (
            board_id: $board_id,
            item_name: $item_name,
            column_values: $column_values
        ) {
            id
        }
    }
    """
    variables = {
        "board_id": settings.MONDAY_BOARD_ID,
        "item_name": task_name,
        "column_values": "{\"priority\": \"" + monday_priority + "\"}"
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                MONDAY_API_URL,
                json={"query": query, "variables": variables},
                headers={
                    "Authorization": settings.MONDAY_API_KEY,
                    "Content-Type": "application/json"
                }
            )
            resp.raise_for_status()
            data = resp.json()
            item_id = data["data"]["create_item"]["id"]
            logger.info(f"Monday task created: {item_id} - {task_name}")
            return item_id
    except Exception as e:
        logger.error(f"Failed to create Monday task: {e}")
        return None


async def close_monday_task(item_id: str) -> bool:
    """סוגר משימה ב-Monday (מעביר לסטטוס Done)"""
    query = """
    mutation ($item_id: ID!, $board_id: ID!, $column_values: JSON!) {
        change_multiple_column_values (
            item_id: $item_id,
            board_id: $board_id,
            column_values: $column_values
        ) {
            id
        }
    }
    """
    variables = {
        "item_id": item_id,
        "board_id": settings.MONDAY_BOARD_ID,
        "column_values": "{\"status__1\": {\"label\": \"הושלם\"}}"
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                MONDAY_API_URL,
                json={"query": query, "variables": variables},
                headers={
                    "Authorization": settings.MONDAY_API_KEY,
                    "Content-Type": "application/json"
                }
            )
            resp.raise_for_status()
            logger.info(f"Monday task closed: {item_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to close Monday task: {e}")
        return False
