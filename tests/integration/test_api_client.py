"""
Интеграционные тесты для публичного API (/api/v1).

Тестируем HTTP endpoints через HTTPX с реальной SQLite БД.
Redis и планировщик событий мокируются.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.clients import ClientModel
from app.models.appointments import AppointmentModel
from app.models.staff_services import StaffServiceModel


# ──────────────────────────────────────────────
# Аутентификация
# ──────────────────────────────────────────────

class TestAuthentication:
    """Тесты аутентификации через X-API-Key."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self, api_client: AsyncClient):
        """Запрос без X-API-Key → 401 или 422."""
        response = await api_client.get("/api/v1/services/")
        assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, api_client: AsyncClient):
        """Неверный API Key → 401."""
        response = await api_client.get(
            "/api/v1/services/",
            headers={"X-API-Key": "wrong-key-xxxxxx"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_api_key_returns_200(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Верный API Key → 200."""
        response = await api_client.get(
            "/api/v1/services/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_inactive_business_returns_403(
        self, api_client: AsyncClient, db_session: AsyncSession
    ):
        """Деактивированный бизнес → 403."""
        inactive_biz = BusinessModel(
            name="Inactive",
            working_time_start=__import__("datetime").time(9, 0),
            working_time_end=__import__("datetime").time(20, 0),
            owner_tg_id=111111,
            api_key="inactive-api-key-test",
            is_active=False,
        )
        db_session.add(inactive_biz)
        await db_session.commit()

        response = await api_client.get(
            "/api/v1/services/",
            headers={"X-API-Key": "inactive-api-key-test"}
        )
        assert response.status_code == 403


# ──────────────────────────────────────────────
# GET /api/v1/services/
# ──────────────────────────────────────────────

class TestGetServices:
    """Тесты получения списка услуг."""

    @pytest.mark.asyncio
    async def test_empty_services_returns_empty_list(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Если услуг нет — возвращается пустой список."""
        response = await api_client.get(
            "/api/v1/services/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_business_services(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_service: ServiceModel
    ):
        """Возвращаются услуги конкретного бизнеса."""
        response = await api_client.get(
            "/api/v1/services/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_service.name
        assert data[0]["price"] == sample_service.price
        assert data[0]["duration_minutes"] == sample_service.duration_minutes

    @pytest.mark.asyncio
    async def test_services_contain_required_fields(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_service: ServiceModel
    ):
        """Каждая услуга содержит обязательные поля."""
        response = await api_client.get(
            "/api/v1/services/",
            headers={"X-API-Key": sample_business.api_key}
        )
        service = response.json()[0]
        assert "id" in service
        assert "name" in service
        assert "price" in service
        assert "duration_minutes" in service
        assert "business_id" in service


# ──────────────────────────────────────────────
# GET /api/v1/services/{id}/staffs/
# ──────────────────────────────────────────────

class TestGetServiceStaffs:
    """Тесты получения мастеров для услуги."""

    @pytest.mark.asyncio
    async def test_returns_staffs_for_service(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_service: ServiceModel,
        sample_staff_service: StaffServiceModel,
        sample_staff: StaffModel,
    ):
        """Возвращаются мастера, привязанные к услуге."""
        response = await api_client.get(
            f"/api/v1/services/{sample_service.id}/staffs/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_staff.id
        assert data[0]["name"] == sample_staff.name

    @pytest.mark.asyncio
    async def test_service_without_staffs_returns_empty(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_service: ServiceModel
    ):
        """Услуга без мастеров — пустой список."""
        response = await api_client.get(
            f"/api/v1/services/{sample_service.id}/staffs/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert response.json() == []


# ──────────────────────────────────────────────
# POST /api/v1/clients/get-or-create/
# ──────────────────────────────────────────────

class TestGetOrCreateClient:
    """Тесты получения или создания клиента."""

    @pytest.mark.asyncio
    async def test_creates_new_client(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Новый клиент создаётся успешно."""
        response = await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={
                "tg_id": 555123456,
                "client_name": "Новый Клиент",
                "phone": "+79991234567",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "client" in data
        assert data["client"]["name"] == "Новый Клиент"
        assert data["client"]["tg_id"] == 555123456

    @pytest.mark.asyncio
    async def test_returns_existing_client(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
    ):
        """Существующий клиент возвращается без дублирования."""
        response = await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={
                "tg_id": sample_client.tg_id,
                "client_name": sample_client.name,
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["client"]["id"] == sample_client.id

    @pytest.mark.asyncio
    async def test_owner_flagged_as_is_owner(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Владелец бизнеса получает флаг is_owner=True."""
        response = await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={
                "tg_id": sample_business.owner_tg_id,
                "client_name": "Владелец",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert response.json()["is_owner"] is True

    @pytest.mark.asyncio
    async def test_regular_client_not_owner(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Обычный клиент получает is_owner=False."""
        response = await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={
                "tg_id": 999888777,
                "client_name": "Клиент",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert response.json()["is_owner"] is False


# ──────────────────────────────────────────────
# POST /api/v1/appointments/create/
# ──────────────────────────────────────────────

class TestCreateAppointment:
    """Тесты создания записи."""

    def _future_datetime(self, offset_hours=24):
        return (datetime.utcnow() + timedelta(hours=offset_hours)).isoformat() + "Z"

    @pytest.mark.asyncio
    async def test_creates_appointment_successfully(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        sample_staff: StaffModel,
        sample_service: ServiceModel,
    ):
        """Запись успешно создаётся при валидных данных."""
        start = self._future_datetime(24)
        end = (datetime.utcnow() + timedelta(hours=25)).isoformat() + "Z"

        response = await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": sample_client.id,
                "client_name": sample_client.name,
                "staff_id": sample_staff.id,
                "service_id": sample_service.id,
                "start_time": start,
                "end_time": end,
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "start_time" in data

    @pytest.mark.asyncio
    async def test_overlapping_appointment_returns_400(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        sample_staff: StaffModel,
        sample_service: ServiceModel,
        future_appointment: AppointmentModel,
    ):
        """Создание записи с пересечением → 400."""
        # Пытаемся создать запись в то же время что и future_appointment
        start = future_appointment.start_time.isoformat() + "Z"
        end = future_appointment.end_time.isoformat() + "Z"

        response = await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": sample_client.id,
                "client_name": sample_client.name,
                "staff_id": sample_staff.id,
                "service_id": sample_service.id,
                "start_time": start,
                "end_time": end,
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_appointment_in_past_returns_422(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        sample_staff: StaffModel,
        sample_service: ServiceModel,
    ):
        """Запись в прошлом → 422 (валидация Pydantic)."""
        past = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
        past_end = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"

        response = await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": sample_client.id,
                "client_name": sample_client.name,
                "staff_id": sample_staff.id,
                "service_id": sample_service.id,
                "start_time": past,
                "end_time": past_end,
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_wrong_business_client_returns_400(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
        sample_business: BusinessModel,
        sample_staff: StaffModel,
        sample_service: ServiceModel,
    ):
        """Клиент из другого бизнеса → 400."""
        from datetime import time
        other_biz = BusinessModel(
            name="Other Biz",
            working_time_start=time(9, 0),
            working_time_end=time(20, 0),
            owner_tg_id=999,
            api_key="other-api-key-xyz",
            is_active=True,
        )
        db_session.add(other_biz)
        other_client = ClientModel(
            name="Чужой клиент",
            tg_id=77777777,
            business_id=other_biz.id if other_biz.id else 999,
        )
        db_session.add(other_client)
        await db_session.commit()
        await db_session.refresh(other_biz)
        await db_session.refresh(other_client)
        other_client.business_id = other_biz.id
        await db_session.commit()

        start = self._future_datetime(24)
        end = self._future_datetime(25)
        response = await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": other_client.id,
                "client_name": "Чужой клиент",
                "staff_id": sample_staff.id,
                "service_id": sample_service.id,
                "start_time": start,
                "end_time": end,
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 400


# ──────────────────────────────────────────────
# GET /api/v1/clients/{id}/appointments/
# ──────────────────────────────────────────────

class TestGetClientAppointments:
    """Тесты получения записей клиента."""

    @pytest.mark.asyncio
    async def test_returns_future_appointments(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        future_appointment: AppointmentModel,
    ):
        """Возвращаются будущие записи клиента."""
        response = await api_client.get(
            f"/api/v1/clients/{sample_client.id}/appointments/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == future_appointment.id

    @pytest.mark.asyncio
    async def test_empty_when_no_appointments(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
    ):
        """Если записей нет — пустой список."""
        response = await api_client.get(
            f"/api/v1/clients/{sample_client.id}/appointments/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert response.json() == []


# ──────────────────────────────────────────────
# POST /api/v1/clients/{id}/appointments/{id}/  (отмена)
# ──────────────────────────────────────────────

class TestCancelAppointment:
    """Тесты отмены записи клиентом."""

    @pytest.mark.asyncio
    async def test_client_cancels_own_appointment(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        future_appointment: AppointmentModel,
    ):
        """Клиент успешно отменяет свою запись."""
        response = await api_client.post(
            f"/api/v1/clients/{sample_client.id}/appointments/{future_appointment.id}/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_404(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
    ):
        """Отмена несуществующей записи → 404."""
        response = await api_client.post(
            f"/api/v1/clients/{sample_client.id}/appointments/99999/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 404


# ──────────────────────────────────────────────
# GET /api/v1/events/
# ──────────────────────────────────────────────

class TestGetEvents:
    """Тесты получения событий."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_events(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Без событий — пустой список."""
        response = await api_client.get(
            "/api/v1/events/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert response.json() == []