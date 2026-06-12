from redis.asyncio import Redis
from fastapi import Depends, HTTPException, Header, Request
from time import time

from app.redis.client import get_redis_client


class RateLimiter:
    def __init__(self, redis: Redis, max_requests: int, time_window: int):
        self._redis = redis
        self.max_requests = max_requests
        self.time_window = time_window


    async def is_limited(self, identifier: str, endpoint: str) -> bool:
        key = f"rate_limit:{endpoint}:{identifier}"
        now = int(time() * 1000)
        window_start = now - self.time_window * 1000

        async with self._redis.pipeline() as pipe:
            await pipe.zremrangebyscore(key, 0, window_start)
            await pipe.zcard(key)
            results = await pipe.execute()
        
        # results[0] - результат zremrangebyscore, results[1] - результат zcard
        count = results[1]

        if count >= self.max_requests:
            return True

        await self._redis.zadd(key, {str(now): now})
        await self._redis.expire(key, self.time_window)

        return False


def rate_limiter(max_requests: int, time_window: int, endpoint: str):
    async def dependency(
        request: Request,
        tg_id: int | None = Header(None, alias="X-TG-ID"),
        redis: Redis = Depends(get_redis_client)
    ):
        try:
            identifier = str(tg_id) if tg_id is not None else request.client.host
            limiter = RateLimiter(redis, max_requests, time_window)

            if await limiter.is_limited(identifier, endpoint):
                raise HTTPException(status_code=429, detail="Too many requests")
        except HTTPException:
            raise
        except Exception as e:
            # Если Redis недоступен, логируем но не блокируем запрос
            from app.utils.logger import logger
            logger.error(f"Rate limiter error for {endpoint}", error=str(e))

    return dependency