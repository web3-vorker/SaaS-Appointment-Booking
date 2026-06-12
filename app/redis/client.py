# Клиент для взаимодействия с базой данных Redis
from redis.asyncio import Redis

from app.config.config import config


# Глобальный Redis клиент
redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """Получить Redis клиент (создается один раз)"""
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(config.redis_url, decode_responses=True)
    return redis_client


async def close_redis():
    """Закрыть Redis соединение при shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None