# Кэширование данных в Redis

import json
from typing import Any
from datetime import datetime
from app.redis.client import get_redis_client
from app.utils.logger import logger
from datetime import time, datetime


class DatetimeEncoder(json.JSONEncoder):
    """JSON encoder для datetime и других non-JSON типов"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def serialize_business(business) -> dict:
    """Преобразует SQLAlchemy BusinessModel в словарь для JSON сериализации"""
    return {
        "id": business.id,
        "name": business.name,
        "working_time_start": business.working_time_start.isoformat() if business.working_time_start else None,
        "working_time_end": business.working_time_end.isoformat() if business.working_time_end else None,
        "break_start": business.break_start.isoformat() if business.break_start else None,
        "break_end": business.break_end.isoformat() if business.break_end else None,
        "weekend_days": business.weekend_days,
        "created_at": business.created_at.isoformat() if business.created_at else None,
        "is_active": business.is_active,
        "owner_tg_id": business.owner_tg_id,
        "api_key": business.api_key,
        "subscription_plan": business.subscription_plan,
        "subscription_expires_at": business.subscription_expires_at.isoformat() if business.subscription_expires_at else None,
        "subscription_notified_at": business.subscription_notified_at.isoformat() if business.subscription_notified_at else None,
    }


def deserialize_business(data: dict) -> dict:
    """Восстанавливает time-поля бизнеса из строк после JSON."""
    time_fields = ["working_time_start", "working_time_end", "break_start", "break_end"]
    for field in time_fields:
        val = data.get(field)
        if isinstance(val, str):
            # "09:00:00" или "09:00" → time(9, 0)
            parts = val.split(":")
            data[field] = time(int(parts[0]), int(parts[1]))
    return data


async def set_cache(key: str, value: Any, expire_seconds: int = 3600):
    """Сохранить данные в Redis с указанием времени жизни"""
    try:
        redis = await get_redis_client()
        value_json = json.dumps(value, cls=DatetimeEncoder)
        await redis.set(key, value_json, ex=expire_seconds)
        logger.info(f"Cache set for key: {key} with expiration: {expire_seconds} seconds")
    except Exception as e:
        logger.error(f"Error setting cache for key: {key} - {str(e)}")


async def get_cache(key: str) -> Any | None:
    """Получить данные из Redis по ключу"""
    try:
        redis = await get_redis_client()
        value_json = await redis.get(key)
        if value_json is not None:
            logger.info(f"Cache hit for key: {key}")
            return json.loads(value_json)
        else:
            logger.info(f"Cache miss for key: {key}")
            return None
    except Exception as e:
        logger.error(f"Error getting cache for key: {key} - {str(e)}")
        return None
    

async def delete_cache(key: str):
    """Удалить данные из Redis по ключу"""
    try:
        redis = await get_redis_client()
        await redis.delete(key)
        logger.info(f"Cache deleted for key: {key}")
    except Exception as e:
        logger.error(f"Error deleting cache for key: {key} - {str(e)}")


async def cache_delete_pattern(pattern: str) -> None:
    """
    Удалить все ключи по паттерну используя SCAN вместо KEYS (не блокирует Redis).
    Например: 'cache:slots:business_id:5:*'
    """
    redis = await get_redis_client()
    try:
        cursor = 0
        deleted_count = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                deleted_count += await redis.delete(*keys)
            if cursor == 0:
                break
        if deleted_count > 0:
            logger.info(f"Cache pattern deleted", pattern=pattern, deleted_count=deleted_count)
    except Exception as e:
        logger.warning("cache_delete_pattern_failed", pattern=pattern, error=str(e))