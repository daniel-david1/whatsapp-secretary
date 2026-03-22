import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GREEN_API_INSTANCE_ID: str = ""
    GREEN_API_TOKEN: str = ""
    GREEN_API_BASE_URL: str = "https://api.green-api.com"
    MY_PHONE_NUMBER: str = ""
    ANTHROPIC_API_KEY: str = ""
    MONDAY_API_KEY: str = ""
    MONDAY_BOARD_ID: str = ""
    DB_PATH: str = "data/secretary.db"
    TIMEZONE: str = "Asia/Jerusalem"
    DAILY_SUMMARY_TIME: str = "08:00"
    WEEKLY_SUMMARY_DAY: int = 0
    WEEKLY_SUMMARY_TIME: str = "09:00"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
