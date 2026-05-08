# Утилиты для работы с datetime - единый подход (naive UTC везде)

from datetime import datetime, timezone


def now_utc() -> datetime:
    """
    Возвращает текущее время в UTC без timezone (naive).
    Используется везде в проекте для консистентности.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    """
    Конвертирует datetime в naive UTC.
    
    Args:
        dt: datetime объект (может быть aware или naive)
    
    Returns:
        naive datetime в UTC
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Уже naive, предполагаем что это UTC
        return dt
    else:
        # Конвертируем в UTC и убираем timezone
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
