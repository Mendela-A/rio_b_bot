import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    admin_chat_id: int
    webhook_url: str | None
    webhook_secret: str | None


def load_config() -> Config:
    def require(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

    return Config(
        bot_token=require("BOT_TOKEN"),
        db_host=require("DB_HOST"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=require("DB_NAME"),
        db_user=require("DB_USER"),
        db_password=require("DB_PASSWORD"),
        admin_chat_id=int(os.getenv("ADMIN_CHAT_ID") or "0"),
        webhook_url=os.getenv("WEBHOOK_URL") or None,
        webhook_secret=os.getenv("WEBHOOK_SECRET") or None,
    )
