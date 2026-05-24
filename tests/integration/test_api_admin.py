"""
Интеграционные тесты для Admin API (/admin).
"""

import pytest
from datetime import datetime, timedelta, time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.clients import ClientModel
from app.models.appointments import AppointmentModel


class TestAdminServices:
    """Тесты управления услугами через admin API."""

    @pytest.mark.asyncio
    async def test_create_service(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Создание услуги через admin endpoint."""
        response = await api_client.post(
            "/admin/service/",
            json={
                "business_id": sample_business.id,
                "name": "Педикюр",
                "price": 1500,
                "duration_minutes": 90,
                "description": "Классический педикюр",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Педикюр"
        assert data["price"] == 1500
        assert data["business_id"] == sample_business.id

    @pytest.mark.asyncio
    async def test_get_services(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_service: ServiceModel
    ):
        """Получение списка услуг через admin."""
        response = await api_client.get(
            "/admin/services/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @pytest.mark.asyncio
    async def test_delete_service(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_service: ServiceModel
    ):
        """Удаление услуги через admin."""
        response = await api_client.delete(
            f"/admin/service/{sample_service.id}",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert "deleted" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_service_returns_404(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Удаление несуществующей услуги → 404."""
        response = await api_client.delete(
            "/admin/service/99999",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_service_for_other_business_returns_403(
        self, api_client: AsyncClient, sample_business: BusinessModel, db_session: AsyncSession
    ):
        """Создание услуги для чужого бизнеса → 403."""
        other_biz = BusinessModel(
            name="Other Business",
            working_time_start=time(9, 0),
            working_time_end=time(20, 0),
            owner_tg_id=888,
            api_key="other-biz-key-abc",
            is_active=True,
        )
        db_session.add(other_biz)
        await db_session.commit()
        await db_session.refresh(other_biz)

        response = await api_client.post(
            "/admin/service/",
            json={
                "business_id": other_biz.id,  # Чужой бизнес!
                "name": "Маникюр",
                "price": 1000,
                "duration_minutes": 60,
            },
            headers={"X-API-Key": sample_business.api_key}  # Ключ нашего бизнеса
        )
        assert response.status_code == 403


class TestAdminStaff:
    """Тесты управления сотрудниками через admin API."""

    @pytest.mark.asyncio
    async def test_create_staff(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Создание сотрудника через admin endpoint."""
        response = await api_client.post(
            "/admin/staff/",
            json={
                "business_id": sample_business.id,
                "name": "Елена",
                "role": "Косметолог",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Елена"
        assert data["role"] == "Косметолог"

    @pytest.mark.asyncio
    async def test_get_staffs(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_staff: StaffModel
    ):
        """Получение списка сотрудников через admin."""
        response = await api_client.get(
            "/admin/staffs/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @pytest.mark.asyncio
    async def test_delete_staff(
        self, api_client: AsyncClient, sample_business: BusinessModel, sample_staff: StaffModel
    ):
        """Удаление сотрудника через admin."""
        response = await api_client.delete(
            f"/admin/staff/{sample_staff.id}",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_nonexistent_staff_returns_404(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Удаление несуществующего сотрудника → 404."""
        response = await api_client.delete(
            "/admin/staff/99999",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 404


class TestAdminAppointments:
    """Тесты управления записями через admin API."""

    @pytest.mark.asyncio
    async def test_get_appointments(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        future_appointment: AppointmentModel,
    ):
        """Возвращаются будущие записи бизнеса."""
        response = await api_client.get(
            "/admin/appointments/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        ids = [a["id"] for a in data]
        assert future_appointment.id in ids

    @pytest.mark.asyncio
    async def test_get_appointment_history(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """История записей возвращается успешно."""
        response = await api_client.get(
            "/admin/appointments/history/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_unmarked_appointments(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Неотмеченные записи возвращаются успешно."""
        response = await api_client.get(
            "/admin/appointments/unmarked/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_cancel_appointment_by_admin(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        future_appointment: AppointmentModel,
    ):
        """Администратор успешно отменяет запись."""
        response = await api_client.post(
            f"/admin/appointments/{future_appointment.id}/cancel/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_404(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Отмена несуществующей записи → 404."""
        response = await api_client.post(
            "/admin/appointments/99999/cancel/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_appointment_status_to_completed(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        future_appointment: AppointmentModel,
    ):
        """Изменение статуса записи на 'completed' через admin."""
        response = await api_client.post(
            f"/admin/appointments/{future_appointment.id}/update-status/",
            params={
                "client_id": sample_client.id,
                "new_status": "completed",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_appointment_status_to_no_show(
        self,
        api_client: AsyncClient,
        sample_business: BusinessModel,
        sample_client: ClientModel,
        future_appointment: AppointmentModel,
    ):
        """Изменение статуса записи на 'no_show'."""
        response = await api_client.post(
            f"/admin/appointments/{future_appointment.id}/update-status/",
            params={
                "client_id": sample_client.id,
                "new_status": "no_show",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200


class TestAdminScheduleExceptions:
    """Тесты управления исключениями в графике."""

    @pytest.mark.asyncio
    async def test_create_day_off_exception(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Создание выходного дня через admin."""
        response = await api_client.post(
            "/admin/schedule-exception/",
            params={
                "date": "2027-01-01",
                "is_working": False,
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_working"] is False
        assert data["date"] == "2027-01-01"

    @pytest.mark.asyncio
    async def test_create_custom_hours_exception(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Создание дня с особым графиком."""
        response = await api_client.post(
            "/admin/schedule-exception/",
            params={
                "date": "2027-02-14",
                "is_working": True,
                "custom_start": "10:00",
                "custom_end": "16:00",
            },
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_working"] is True
        assert data["custom_start_time"] == "10:00"
        assert data["custom_end_time"] == "16:00"

    @pytest.mark.asyncio
    async def test_get_schedule_exceptions(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Получение списка исключений."""
        response = await api_client.get(
            "/admin/schedule-exceptions/",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_delete_schedule_exception(
        self, api_client: AsyncClient, sample_business: BusinessModel
    ):
        """Создание и удаление исключения."""
        # Создаём
        create_resp = await api_client.post(
            "/admin/schedule-exception/",
            params={"date": "2027-12-31", "is_working": False},
            headers={"X-API-Key": sample_business.api_key}
        )
        assert create_resp.status_code == 200
        exc_id = create_resp.json()["id"]

        # Удаляем
        delete_resp = await api_client.delete(
            f"/admin/schedule-exception/{exc_id}",
            headers={"X-API-Key": sample_business.api_key}
        )
        assert delete_resp.status_code == 200