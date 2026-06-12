"""
Фикстуры для всех уровней тестирования.
Используется SQLite (aiosqlite) — не нужен PostgreSQL для запуска тестов.
Redis мокируется через pytest-mock.
"""

import pytest
import pytest_asyncio
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# ──────────────────────────────────────────────
# Патч конфига ДО импорта приложения
# ──────────────────────────────────────────────
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DEVELOPER_KEY", "test-dev-key-12345")
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("TIMEZONE_OFFSET", "3")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("LOG_FILE_PATH", "")
os.environ.setdefault("LOG_JSON_FORMAT", "false")


from app.models.base import Base
from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.clients import ClientModel
from app.models.appointments import AppointmentModel
from app.models.events import EventModel
from app.models.schedule_exceptions import ScheduleExceptionModel
from app.models.staff_services import StaffServiceModel


# ──────────────────────────────────────────────
# Асинхронный движок SQLite для тестов
# ──────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Используем стандартный event loop."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Создаёт свежий движок + таблицы для каждого теста."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Асинхронная сессия с автоматическим rollback после теста."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ──────────────────────────────────────────────
# Мок Redis
# ──────────────────────────────────────────────
@pytest.fixture()
def mock_redis():
    """
    Мок Redis-клиента (rate limiter всегда пропускает).

    ВАЖНО: redis.pipeline() в redis-py — синхронный метод, возвращающий
    объект-пайплайн, который используется как async context manager.
    Поэтому mock_redis.pipeline должен быть обычным MagicMock (не AsyncMock),
    а его return_value — поддерживать async with.
    """
    from unittest.mock import MagicMock

    # Объект пайплайна, который работает как `async with pipe`
    pipe = AsyncMock()
    pipe.zremrangebyscore = AsyncMock()
    pipe.zcard = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, 0])  # count=0 → не заблокирован

    # pipeline() — синхронный вызов, возвращает объект с __aenter__/__aexit__
    pipeline_cm = MagicMock()
    pipeline_cm.__aenter__ = AsyncMock(return_value=pipe)
    pipeline_cm.__aexit__ = AsyncMock(return_value=False)

    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=pipeline_cm)  # sync!
    redis.zadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    return redis


# ──────────────────────────────────────────────
# Фикстуры моделей
# ──────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_business(db_session: AsyncSession) -> BusinessModel:
    """Создаёт тестовый бизнес."""
    business = BusinessModel(
        name="Test Salon",
        working_time_start=time(9, 0),
        working_time_end=time(20, 0),
        owner_tg_id=123456789,
        api_key="test-api-key-12345",
        is_active=True,
        weekend_days=[],
    )
    db_session.add(business)
    await db_session.commit()
    await db_session.refresh(business)
    return business


@pytest_asyncio.fixture()
async def sample_staff(db_session: AsyncSession, sample_business: BusinessModel) -> StaffModel:
    """Создаёт тестового сотрудника."""
    staff = StaffModel(
        name="Анна Иванова",
        business_id=sample_business.id,
        role="Мастер маникюра",
    )
    db_session.add(staff)
    await db_session.commit()
    await db_session.refresh(staff)
    return staff


@pytest_asyncio.fixture()
async def sample_service(db_session: AsyncSession, sample_business: BusinessModel) -> ServiceModel:
    """Создаёт тестовую услугу (60 мин)."""
    service = ServiceModel(
        name="Маникюр",
        business_id=sample_business.id,
        price=1200,
        duration_minutes=60,
        description="Классический маникюр",
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service


@pytest_asyncio.fixture()
async def sample_client(db_session: AsyncSession, sample_business: BusinessModel) -> ClientModel:
    """Создаёт тестового клиента."""
    client = ClientModel(
        name="Мария Петрова",
        tg_id=987654321,
        phone="+79991234567",
        business_id=sample_business.id,
    )
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    return client


@pytest_asyncio.fixture()
async def sample_staff_service(
    db_session: AsyncSession,
    sample_business: BusinessModel,
    sample_staff: StaffModel,
    sample_service: ServiceModel,
) -> StaffServiceModel:
    """Привязывает услугу к сотруднику."""
    ss = StaffServiceModel(
        staff_id=sample_staff.id,
        service_id=sample_service.id,
        business_id=sample_business.id,
    )
    db_session.add(ss)
    await db_session.commit()
    await db_session.refresh(ss)
    return ss


@pytest_asyncio.fixture()
async def future_appointment(
    db_session: AsyncSession,
    sample_business: BusinessModel,
    sample_client: ClientModel,
    sample_staff: StaffModel,
    sample_service: ServiceModel,
) -> AppointmentModel:
    """Создаёт будущую запись (завтра в 10:00 UTC)."""
    tomorrow = datetime.utcnow().replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment = AppointmentModel(
        business_id=sample_business.id,
        client_id=sample_client.id,
        client_name=sample_client.name,
        staff_id=sample_staff.id,
        service_id=sample_service.id,
        start_time=tomorrow,
        end_time=tomorrow + timedelta(hours=1),
        status="scheduled",
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


# ──────────────────────────────────────────────
# FastAPI test client с подменой зависимостей
# ──────────────────────────────────────────────
@pytest_asyncio.fixture()
async def api_client(test_engine, mock_redis, monkeypatch):
    """
    HTTPX-клиент для интеграционных тестов.
    Подменяет БД-сессию на тестовую и Redis на мок.
    """
    from app.main import app
    import app.db.database as db_module
    import app.redis.client as client_module

    # Подменяем сессию
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[db_module.get_session] = override_get_session

    # Подменяем Redis
    monkeypatch.setattr(client_module, "redis_client", mock_redis)
    monkeypatch.setattr(client_module, "get_redis_client", AsyncMock(return_value=mock_redis))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def service(db_session, mock_redis, monkeypatch):
    """
    Фикстура для Service с моками БД и Redis для unit-тестов.
    """
    from app.services.service import Service
    from app.repository.repository import Repository
    import app.redis.client as client_module
    
    # Подменяем Redis
    monkeypatch.setattr(client_module, "redis_client", mock_redis)
    monkeypatch.setattr(client_module, "get_redis_client", AsyncMock(return_value=mock_redis))
    
    # Создаем mock repository
    mock_repository = AsyncMock(spec=Repository)
    
    # Создаем Service с мок-сессией и mock repository
    service_instance = Service(session=db_session, repository=mock_repository)
    
    return service_instance