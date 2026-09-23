# Клиент для взаимодействия с базой данных Redis
import asyncio

from redis.asyncio import Redis
from app.config.config import config

class RedisClient:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self.client: Redis | None = None

    async def get_client(self) -> Redis:
        """Получить Redis клиент (создается один раз)"""
        if self.client is None:
            self.client = Redis.from_url(self._redis_url, decode_responses=True)
        return self.client

    async def close(self):
        """Закрыть Redis соединение при shutdown"""
        if self.client:
            await self.client.close()
            self.client = None


redis_client = RedisClient(config.redis_url)