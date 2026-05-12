from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class DevBotConfig:
    """Configuration for the Developer Telegram bot"""

    telegram_bot_token: str
    developer_key: str
    api_url: str = os.getenv("API_URL", "http://localhost:8000")

    @classmethod
    def from_env(cls) -> "DevBotConfig":
        """Create dev bot config from environment variables"""
        return cls(
            telegram_bot_token=os.getenv("DEV_BOT_TOKEN"),
            developer_key=os.getenv("DEVELOPER_KEY"),
        )


# Global dev bot config instance
dev_bot_config = DevBotConfig.from_env()
