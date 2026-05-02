# Тесты для developer endpoints

import os
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
from app.db.database import new_session
from sqlalchemy import select

# Устанавливаем переменные окружения ДО импорта
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
DEVELOPER_KEY = "test-dev-key-12345"
os.environ["DEVELOPER_KEY"] = DEVELOPER_KEY

API_URL = "/dev"  # Prefix for developer routes


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Инициализация БД перед всеми тестами"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    
    # Опционально: очистка после тестов
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_dev_business_create_unauthorized():
    """Тест создания бизнеса без developer key"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Test Business Dev",
                "owner_tg_id": 111111
            }
        )
        assert response.status_code == 401
        assert "Developer key required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dev_business_create_wrong_key():
    """Тест создания бизнеса с неправильным developer key"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Test Business Dev 2",
                "owner_tg_id": 111112
            },
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401
        assert "Invalid developer key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dev_business_create_success():
    """Тест успешного создания бизнеса с правильным developer key"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Test Business Dev Success",
                "owner_tg_id": 111113
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Business Dev Success"
        assert data["owner_tg_id"] == 111113
        assert "id" in data
        assert "api_key" in data
        assert isinstance(data["api_key"], str)
        assert len(data["api_key"]) > 0


@pytest.mark.asyncio
async def test_dev_business_duplicate_name():
    """Тест на попытку создать бизнес с уже существующим именем"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем первый бизнес
        response1 = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Duplicate Business",
                "owner_tg_id": 111114
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response1.status_code == 200
        
        # Пытаемся создать второй бизнес с тем же именем
        response2 = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Duplicate Business",
                "owner_tg_id": 111115
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_dev_staff_create_success():
    """Тест успешного создания сотрудника"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем бизнес
        business_response = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Business for Staff",
                "owner_tg_id": 111116
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert business_response.status_code == 200
        business_id = business_response.json()["id"]
        
        # Создаем сотрудника
        staff_response = await client.post(
            f"{API_URL}/staff/",
            json={
                "name": "Test Staff",
                "business_id": business_id,
                "role": "Мастер"
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert staff_response.status_code == 200
        staff_data = staff_response.json()
        assert staff_data["name"] == "Test Staff"
        assert staff_data["business_id"] == business_id
        assert staff_data["role"] == "Мастер"
        assert "id" in staff_data


@pytest.mark.asyncio
async def test_dev_staff_create_business_not_found():
    """Тест создания сотрудника для несуществующего бизнеса"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_URL}/staff/",
            json={
                "name": "Test Staff",
                "business_id": 99999,
                "role": "Мастер"
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response.status_code == 404
        assert "Business not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dev_service_create_success():
    """Тест успешного создания услуги"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем бизнес
        business_response = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Business for Service",
                "owner_tg_id": 111117
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert business_response.status_code == 200
        business_id = business_response.json()["id"]
        
        # Создаем услугу
        service_response = await client.post(
            f"{API_URL}/service/",
            json={
                "name": "Test Service",
                "business_id": business_id,
                "price": 1000,
                "description": "Test description",
                "duration_minutes": 30
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert service_response.status_code == 200
        service_data = service_response.json()
        assert service_data["name"] == "Test Service"
        assert service_data["business_id"] == business_id
        assert service_data["price"] == 1000
        assert service_data["description"] == "Test description"
        assert service_data["duration_minutes"] == 30
        assert "id" in service_data


@pytest.mark.asyncio
async def test_dev_service_create_business_not_found():
    """Тест создания услуги для несуществующего бизнеса"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_URL}/service/",
            json={
                "name": "Test Service",
                "business_id": 99999,
                "price": 1000,
                "description": "Test",
                "duration_minutes": 30
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response.status_code == 404
        assert "Business not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dev_appointment_create_success():
    """Тест успешного создания записи через developer endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем бизнес
        business_response = await client.post(
            f"{API_URL}/business/",
            json={
                "name": "Business for Appointment",
                "owner_tg_id": 111118
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert business_response.status_code == 200
        business_data = business_response.json()
        business_id = business_data["id"]
        business_api_key = business_data["api_key"]
        
        # Создаем сотрудника
        staff_response = await client.post(
            f"{API_URL}/staff/",
            json={
                "name": "Test Staff for Appointment",
                "business_id": business_id,
                "role": "Мастер"
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert staff_response.status_code == 200
        staff_id = staff_response.json()["id"]
        
        # Создаем услугу
        service_response = await client.post(
            f"{API_URL}/service/",
            json={
                "name": "Test Service for Appointment",
                "business_id": business_id,
                "price": 2000,
                "description": "Test service description",
                "duration_minutes": 60
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert service_response.status_code == 200
        service_id = service_response.json()["id"]
        
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 999999, "client_name": "Test Client for Appointment"},
            headers={"X-API-Key": business_api_key}
        )
        assert client_response.status_code == 200
        client_id = client_response.json()["id"]
        
        # Создаем запись через developer endpoint
        start_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        appointment_response = await client.post(
            f"{API_URL}/appointment/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert appointment_response.status_code == 200
        appointment_data = appointment_response.json()
        assert appointment_data["client_id"] == client_id
        assert appointment_data["staff_id"] == staff_id
        assert appointment_data["service_id"] == service_id
        assert "id" in appointment_data
        
        # Проверяем, что запись действительно создана
        get_appointment_response = await client.get(
            f"/api/v1/clients/{client_id}/appointments/",
            headers={"X-API-Key": business_api_key}
        )
        assert get_appointment_response.status_code == 200
        appointments = get_appointment_response.json()
        assert len(appointments) == 1
        assert appointments[0]["id"] == appointment_data["id"]


@pytest.mark.asyncio
async def test_dev_appointment_create_staff_not_found():
    """Тест создания записи с несуществующим сотрудником"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{API_URL}/appointment/",
            json={
                "client_id": 1,
                "staff_id": 99999,
                "service_id": 1,
                "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response.status_code == 404
        assert "Staff not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dev_appointment_create_service_not_found():
    """Тест создания записи с несуществующей услугой"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Сначала создаем бизнес и сотрудника
        business_response = await client.post(
            f"{API_URL}/business/",
            json={"name": "Business for Test", "owner_tg_id": 111119},
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        business_id = business_response.json()["id"]
        
        staff_response = await client.post(
            f"{API_URL}/staff/",
            json={"name": "Test Staff", "business_id": business_id, "role": "Tester"},
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        staff_id = staff_response.json()["id"]
        
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 888888, "client_name": "Test Client"},
            headers={"X-API-Key": business_response.json()["api_key"]}
        )
        client_id = client_response.json()["id"]
        
        response = await client.post(
            f"{API_URL}/appointment/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": 99999,
                "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dev_appointment_create_staff_service_diff_business():
    """Тест создания записи, где сотрудник и услуга из разных бизнесов"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем два бизнеса
        business1 = await client.post(
            f"{API_URL}/business/",
            json={"name": "Business 1", "owner_tg_id": 111120},
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        business2 = await client.post(
            f"{API_URL}/business/",
            json={"name": "Business 2", "owner_tg_id": 111121},
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        business1_id = business1.json()["id"]
        business2_id = business2.json()["id"]
        
        # Создаем сотрудника в бизнесе 1
        staff_response = await client.post(
            f"{API_URL}/staff/",
            json={"name": "Staff B1", "business_id": business1_id, "role": "Tester"},
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        staff_id = staff_response.json()["id"]
        
        # Создаем услугу в бизнесе 2
        service_response = await client.post(
            f"{API_URL}/service/",
            json={"name": "Service B2", "business_id": business2_id, "price": 100, "duration_minutes": 30},
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        service_id = service_response.json()["id"]
        
        # Создаем клиента
        client_response = await client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 777777, "client_name": "Test Client"},
            headers={"X-API-Key": business1.json()["api_key"]}
        )
        client_id = client_response.json()["id"]
        
        response = await client.post(
            f"{API_URL}/appointment/",
            json={
                "client_id": client_id,
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
            },
            headers={"X-API-Key": DEVELOPER_KEY}
        )
        assert response.status_code == 400
        assert "Staff and service belong to different businesses" in response.json()["detail"]