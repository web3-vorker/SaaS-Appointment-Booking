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
    
    # Logging settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file_path: str = os.getenv("LOG_FILE_PATH", "logs/dev_bot.log")
    log_json_format: bool = os.getenv("LOG_JSON_FORMAT", "true").lower() == "true"
    
    # Error monitoring settings
    error_monitor_enabled: bool = os.getenv("ERROR_MONITOR_ENABLED", "true").lower() == "true"
    error_log_path: str = os.getenv("ERROR_LOG_PATH", "logs/error.log")
    developer_tg_id: int = int(os.getenv("DEVELOPER_TG_ID", "0"))
    alert_rate_limit_window: int = int(os.getenv("ALERT_RATE_LIMIT_WINDOW", "60"))
    alert_max_per_window: int = int(os.getenv("ALERT_MAX_PER_WINDOW", "10"))

    @classmethod
    def from_env(cls) -> "DevBotConfig":
        """Create dev bot config from environment variables"""
        return cls(
            telegram_bot_token=os.getenv("DEV_BOT_TOKEN"),
            developer_key=os.getenv("DEVELOPER_KEY"),
        )


# Global dev bot config instance
dev_bot_config = DevBotConfig.from_env()
