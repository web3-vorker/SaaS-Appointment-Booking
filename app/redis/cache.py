from typing import Any, Protocol


class CacheProtocol(Protocol):
    async def set_cache(
        self,
        key: str,
        value: Any,
        expire_seconds: int = 3600,
    ) -> None:
        ...

    async def get_cache(self, key: str) -> Any | None:
        ...

    async def delete_cache(self, key: str) -> None:
        ...

    async def cache_delete_pattern(self, pattern: str) -> None:
        ...