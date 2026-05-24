from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    """Configuration"""

    # Database
    database_url: str

    # Redis
    redis_url: str

    # API
    api_url: str
    api_key: str

    # Developer
    developer_key: str

    # Timezone
    timezone_offset: int  # Смещение от UTC в часах (например, 3 для UTC+3)

    # CORS settings
    cors_origins: list[str]
    cors_methods: list[str]
    cors_headers: list[str]
    cors_credentials: bool

    # Notification service
    notification_retries: int
    notification_delay: int
    
    # Scheduler settings
    reminder_minutes_before: int  # За сколько минут до записи отправлять напоминание
    event_cleanup_days: int  # Через сколько дней удалять старые отправленные события
    
    # Booking settings
    min_booking_buffer_minutes: int  # Минимальный буфер времени для записи (от текущего момента)
    free_days_lookahead: int  # На сколько дней вперед показывать свободные дни
    max_displayed_days: int  # Максимум дней для отображения в боте
    
    # Logging settings
    log_level: str  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_file_path: str  # Путь к файлу логов
    log_json_format: bool  # Использовать JSON формат для логов

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables"""
        return cls(
            # Database
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),

            # API
            api_url=os.getenv("API_URL", "http://localhost:8000/api/v1"),
            api_key=os.getenv("API_KEY", "48f4b83087153abdf3fc895c8efdb45a"),

            # Developer
            developer_key=os.getenv("DEVELOPER_KEY", ""),

            # Timezone (по умолчанию UTC+3 для России/Москвы)
            timezone_offset=int(os.getenv("TIMEZONE_OFFSET", "3")),

            # CORS settings
            cors_origins=["*"],
            cors_methods=["*"],
            cors_headers=["*"],
            cors_credentials=True,

            # Notification service
            notification_retries=3,
            notification_delay=5,
            
            # Scheduler settings
            reminder_minutes_before=int(os.getenv("REMINDER_MINUTES_BEFORE", "60")),
            event_cleanup_days=int(os.getenv("EVENT_CLEANUP_DAYS", "7")),
            
            # Booking settings
            min_booking_buffer_minutes=int(os.getenv("MIN_BOOKING_BUFFER_MINUTES", "30")),
            free_days_lookahead=int(os.getenv("FREE_DAYS_LOOKAHEAD", "30")),
            max_displayed_days=int(os.getenv("MAX_DISPLAYED_DAYS", "14")),
            
            # Logging settings
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file_path=os.getenv("LOG_FILE_PATH", "logs/app.log"),
            log_json_format=os.getenv("LOG_JSON_FORMAT", "true").lower() == "true",
        )


# Global config instance
config = Config.from_env()

