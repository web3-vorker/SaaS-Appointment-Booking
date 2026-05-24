"""
Структурированное логирование для dev_bot
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_bot_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Добавляет контекст бота к логам"""
    event_dict["app"] = "dev_bot"
    return event_dict


def setup_bot_logging(
    log_level: str = "INFO",
    log_file_path: str | None = None,
    json_format: bool = True,
) -> None:
    """
    Настройка структурированного логирования для бота
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Путь к файлу логов (если None - только в консоль)
        json_format: Использовать JSON формат (True) или человекочитаемый (False)
    """
    
    # Преобразуем строку уровня в константу logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Настройка стандартного logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=[],
    )
    
    # Процессоры для structlog
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_bot_context,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Добавляем форматирование exception'ов
    if json_format:
        processors.append(structlog.processors.format_exc_info)
    else:
        processors.append(structlog.dev.set_exc_info)
    
    # Финальный процессор (рендерер)
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Конфигурация structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Настройка handlers для вывода
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # File handler (если указан путь)
    if log_file_path:
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Используем RotatingFileHandler для ротации логов
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=30,  # Храним 30 файлов
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Получить структурированный логгер для бота
    
    Args:
        name: Имя логгера (обычно __name__ модуля)
    
    Returns:
        Настроенный structlog логгер
    """
    return structlog.get_logger(name)
