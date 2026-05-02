# Новые правильные тесты для API
import os
# Принудительно используем SQLite для тестов (временная БД в памяти)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_new.db"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from datetime import datetime, timedelta, timezone
from app.db.database import engine
from app.models.base import Base
from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.appointments import AppointmentModel
from app.models.clients import ClientModel
from app.db.database import new_session
from sqlalchemy import select, delete

TEST_API_KEY = "test-api-key-12345"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    """Настройка БД для каждого теста"""
    # Создаем таблицы (если не созданы)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Очищаем старые данные
    async with new_session() as session:
        await session.execute(delete(AppointmentModel))
        await session.execute(delete(ClientModel))
        await session.execute(delete(StaffModel))
        await session.execute(delete(ServiceModel))
        await session.commit()
    
    # Создаем тестовые данные
    async with new_session() as session:
        # Создаем тестовый бизнес
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.api_key == TEST_API_KEY)
        )
        test_business = result.scalars().first()
        
        if not test_business:
            test_business = BusinessModel(
                name="Test Business",
                owner_tg_id=123456789,
                api_key=TEST_API_KEY
            )
            session.add(test_business)
            await session.commit()
            await session.refresh(test_business)
        
        # Создаем сотрудников
        staff_result = await session.execute(
            select(StaffModel).where(StaffModel.business_id == test_business.id)
        )
        if not staff_result.scalars().first():
            staff1 = StaffModel(name="Иван Иванов", business_id=test_business.id, role="Мастер маникюра")
            staff2 = StaffModel(name="Мария Петрова", business_id=test_business.id, role="Парикмахер")
            session.add_all([staff1, staff2])
        
        # Создаем услуги
        service_result = await session.execute(
            select(ServiceModel).where(ServiceModel.business_id == test_business.id)
        )
        if not service_result.scalars().first():
            service1 = ServiceModel(name="Маникюр", business_id=test_business.id, price=1500, description="Классический маникюр", duration_minutes=60)
            service2 = ServiceModel(name="Стрижка", business_id=test_business.id, price=2000, description="Мужская/женская стрижка", duration_minutes=45)
            service3 = ServiceModel(name="Окрашивание", business_id=test_business.id, price=3500, description="Окрашивание волос", duration_minutes=120)
            session.add_all([service1, service2, service3])
        
        await session.commit()


@pytest.mark.asyncio
async def test_get_staffs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/staffs/",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Минимум 2 сотрудника


@pytest.mark.asyncio
async def test_get_services():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/services/",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Минимум 3 услуги


@pytest.mark.asyncio
async def test_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/staffs/")
        assert response.status_code == 422  # Missing header


@pytest.mark.asyncio
async def test_invalid_api_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/staffs/",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_or_create_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 999999, "client_name": "Test Client"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["tg_id"] == 999999
        assert data["name"] == "Test Client"


@pytest.mark.asyncio
async def test_get_free_days():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Получаем ID сотрудника
        staffs_response = await client.get("/api/v1/staffs/", headers={"X-API-Key": TEST_API_KEY})
        staff_id = staffs_response.json()[0]["id"]

        # Получаем ID услуги
        services_response = await client.get("/api/v1/services/", headers={"X-API-Key": TEST_API_KEY})
        service_id = services_response.json()[0]["id"]

        response = await client.get(
            f"/api/v1/staffs/{staff_id}/free-days/",
            params={"service_id": service_id},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_free_slots():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Получаем ID сотрудника и услуги
        staffs_response = await client.get("/api/v1/staffs/", headers={"X-API-Key": TEST_API_KEY})
        staff_id = staffs_response.json()[0]["id"]
        services_response = await client.get("/api/v1/services/", headers={"X-API-Key": TEST_API_KEY})
        service_id = services_response.json()[0]["id"]

        # Дата через неделю
        test_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

        response = await client.get(
            f"/api/v1/staffs/{staff_id}/free-slots/",
            params={"date": test_date, "service_id": service_id},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_appointment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 888888, "client_name": "Appointment Test User"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        client_id = client_response.json()["id"]

        # Получаем сотрудника и услугу
        staffs_response = await client.get("/api/v1/staffs/", headers={"X-API-Key": TEST_API_KEY})
        staff_id = staffs_response.json()[0]["id"]
        services_response = await client.get("/api/v1/services/", headers={"X-API-Key": TEST_API_KEY})
        service_id = services_response.json()[0]["id"]

        # Создаем запись на уникальное время
        start_time = (datetime.now(timezone.utc) + timedelta(days=10)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        response = await client.post(
            "/api/v1/appointments/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "client_id" in data
        assert "staff_id" in data
        assert "service_id" in data
        assert "start_time" in data
        assert "end_time" in data


@pytest.mark.asyncio
async def test_get_client_appointments():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 777777, "client_name": "Client Appointments User"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        client_id = client_response.json()["id"]

        response = await client.get(
            f"/api/v1/clients/{client_id}/appointments/",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_appointment_overlap_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 666666, "client_name": "Overlap Test User"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        client_id = client_response.json()["id"]

        # Получаем сотрудника и услугу
        staffs_response = await client.get("/api/v1/staffs/", headers={"X-API-Key": TEST_API_KEY})
        staff_id = staffs_response.json()[0]["id"]
        services_response = await client.get("/api/v1/services/", headers={"X-API-Key": TEST_API_KEY})
        service_id = services_response.json()[0]["id"]

        # Создаем первую запись
        start_time = (datetime.now(timezone.utc) + timedelta(days=15)).replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        response1 = await client.post(
            "/api/v1/appointments/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response1.status_code == 200

        # Пытаемся создать пересекающуюся запись
        response2 = await client.post(
            "/api/v1/appointments/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start_time.isoformat(),  # То же время
                "end_time": end_time.isoformat()
            },
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response2.status_code == 400


@pytest.mark.asyncio
async def test_appointment_time_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 555555, "client_name": "Time Validation User"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        client_id = client_response.json()["id"]

        # Получаем сотрудника и услугу
        staffs_response = await client.get("/api/v1/staffs/", headers={"X-API-Key": TEST_API_KEY})
        staff_id = staffs_response.json()[0]["id"]
        services_response = await client.get("/api/v1/services/", headers={"X-API-Key": TEST_API_KEY})
        service_id = services_response.json()[0]["id"]

        # Пытаемся создать запись в прошлом
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = past_time + timedelta(hours=1)

        response = await client.post(
            "/api/v1/appointments/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": past_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_cancel_appointment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 444444, "client_name": "Cancel Test User"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        client_id = client_response.json()["id"]

        # Создаем запись
        staffs_response = await client.get("/api/v1/staffs/", headers={"X-API-Key": TEST_API_KEY})
        staff_id = staffs_response.json()[0]["id"]
        services_response = await client.get("/api/v1/services/", headers={"X-API-Key": TEST_API_KEY})
        service_id = services_response.json()[0]["id"]

        start_time = (datetime.now(timezone.utc) + timedelta(days=20)).replace(hour=11, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        appointment_response = await client.post(
            "/api/v1/appointments/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            headers={"X-API-Key": TEST_API_KEY}
        )
        appointment_id = appointment_response.json()["id"]

        # Отменяем запись
        response = await client.post(
            f"/api/v1/clients/{client_id}/appointments/{appointment_id}/",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Запись успешно отменена"