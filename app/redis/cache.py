# Кэширование данных в Redis

import json
from typing import Any
from datetime import datetime
from app.redis.client import get_redis_client
from app.utils.logger import logger


class DatetimeEncoder(json.JSONEncoder):
    """JSON encoder для datetime и других non-JSON типов"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


async def set_cache(key: str, value: Any, expire_seconds: int = 3600):
    """Сохранить данные в Redis с указанием времени жизни"""
    try:
        redis = await get_redis_client()
        value_json = json.dumps(value, cls=DatetimeEncoder)
        await redis.set(key, value_json, ex=expire_seconds)
        logger.info(f"Cache set for key: {key} with expiration: {expire_seconds} seconds")
    except Exception as e:
        logger.error(f"Error setting cache for key: {key} - {str(e)}")
        raise


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