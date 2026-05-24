"""
Backward compatibility wrapper для существующего кода
Теперь использует structlog под капотом
"""

from app.utils.structured_logger import get_logger

# Экспортируем get_logger для нового кода
__all__ = ["logger", "get_logger"]

# Для обратной совместимости со старым кодом
logger = get_logger(__name__)