"""
Unit тесты для app/redis/limiter.py — класс RateLimiter.
Redis мокируется, сетевых вызовов нет.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.redis.limiter import RateLimiter


def make_redis_mock(current_count: int = 0):
    """
    Создаёт мок Redis, где zcard возвращает current_count.

    redis.pipeline() — синхронный вызов в redis-py, возвращающий объект,
    поддерживающий `async with`. Поэтому .pipeline должен быть MagicMock (sync),
    а его return_value — иметь __aenter__/__aexit__.
    """
    from unittest.mock import MagicMock

    pipe = AsyncMock()
    pipe.zremrangebyscore = AsyncMock()
    pipe.zcard = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, current_count])

    pipeline_cm = MagicMock()
    pipeline_cm.__aenter__ = AsyncMock(return_value=pipe)
    pipeline_cm.__aexit__ = AsyncMock(return_value=False)

    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=pipeline_cm)  # sync, не async!
    redis.zadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)

    return redis


class TestRateLimiter:
    """Тесты класса RateLimiter."""

    @pytest.mark.asyncio
    async def test_not_limited_when_count_below_max(self):
        """Запрос не ограничивается, если количество < max_requests."""
        redis = make_redis_mock(current_count=5)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        result = await limiter.is_limited("user123", "test_endpoint")

        assert result is False

    @pytest.mark.asyncio
    async def test_limited_when_count_equals_max(self):
        """Запрос ограничивается, когда count == max_requests."""
        redis = make_redis_mock(current_count=10)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        result = await limiter.is_limited("user123", "test_endpoint")

        assert result is True

    @pytest.mark.asyncio
    async def test_limited_when_count_exceeds_max(self):
        """Запрос ограничивается, когда count > max_requests."""
        redis = make_redis_mock(current_count=15)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        result = await limiter.is_limited("user123", "test_endpoint")

        assert result is True

    @pytest.mark.asyncio
    async def test_zadd_called_when_not_limited(self):
        """При разрешённом запросе вызывается zadd (добавление записи)."""
        redis = make_redis_mock(current_count=0)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        await limiter.is_limited("user123", "test_endpoint")

        redis.zadd.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_zadd_not_called_when_limited(self):
        """При заблокированном запросе zadd НЕ вызывается."""
        redis = make_redis_mock(current_count=10)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        await limiter.is_limited("user123", "test_endpoint")

        redis.zadd.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_expire_called_when_not_limited(self):
        """При разрешённом запросе обновляется TTL ключа."""
        redis = make_redis_mock(current_count=0)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        await limiter.is_limited("user123", "test_endpoint")

        redis.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_key_format_includes_endpoint_and_identifier(self):
        """Ключ Redis включает endpoint и идентификатор."""
        redis = make_redis_mock(current_count=0)
        limiter = RateLimiter(redis, max_requests=10, time_window=60)

        await limiter.is_limited("user_abc", "my_endpoint")

        # Проверяем, что expire вызван с правильным ключом
        call_args = redis.expire.call_args
        key = call_args[0][0]
        assert "my_endpoint" in key
        assert "user_abc" in key

    @pytest.mark.asyncio
    async def test_zero_count_always_allowed(self):
        """При нулевом счётчике запрос всегда разрешён."""
        redis = make_redis_mock(current_count=0)
        limiter = RateLimiter(redis, max_requests=1, time_window=60)

        result = await limiter.is_limited("user", "endpoint")
        assert result is False

    @pytest.mark.asyncio
    async def test_different_endpoints_independent(self):
        """Разные endpoints не влияют друг на друга."""
        # Endpoint 1 — под лимитом
        redis1 = make_redis_mock(current_count=10)
        limiter1 = RateLimiter(redis1, max_requests=10, time_window=60)
        assert await limiter1.is_limited("user", "endpoint_a") is True

        # Endpoint 2 — ещё не под лимитом
        redis2 = make_redis_mock(current_count=5)
        limiter2 = RateLimiter(redis2, max_requests=10, time_window=60)
        assert await limiter2.is_limited("user", "endpoint_b") is False