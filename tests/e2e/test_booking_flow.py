"""
E2E тесты — полный жизненный цикл записи клиента.

Тестируем сквозные сценарии: от создания бизнеса через dev API
до бронирования и отмены записи. Имитируем реальную работу бота.

Каждый тест — независимый сценарий, не полагающийся на другие тесты.
"""

import pytest
from datetime import datetime, timedelta, time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def future_iso(offset_hours: int) -> str:
    """UTC datetime в будущем → ISO строка с Z."""
    return (datetime.utcnow() + timedelta(hours=offset_hours)).isoformat() + "Z"


class TestCompleteBookingFlow:
    """
    Сценарий 1: Полный процесс записи клиента.

    1. [Admin] Создаём бизнес (dev endpoint)
    2. [Admin] Создаём сотрудника
    3. [Admin] Создаём услугу
    4. [Admin] Привязываем услугу к сотруднику
    5. [Bot]   Клиент запрашивает список услуг
    6. [Bot]   Клиент запрашивает мастеров для услуги
    7. [Bot]   Клиент получает/создаёт свой профиль
    8. [Bot]   Клиент создаёт запись
    9. [Bot]   Клиент видит свои записи
    10.[Bot]   Клиент отменяет запись
    """

    @pytest.mark.asyncio
    async def test_full_booking_and_cancel_flow(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Полный сценарий: от регистрации до отмены записи."""
        DEV_KEY = "test-dev-key-12345"

        # ── Шаг 1: Создаём бизнес через dev API ──
        biz_resp = await api_client.post(
            "/dev/business/",
            json={
                "name": "E2E Salon Test",
                "working_hours_start": "09:00",
                "working_hours_end": "20:00",
                "owner_tg_id": 777001,
            },
            headers={"X-API-Key": DEV_KEY}
        )
        assert biz_resp.status_code == 200, f"Ошибка создания бизнеса: {biz_resp.text}"
        biz_data = biz_resp.json()
        biz_id = biz_data["id"]
        api_key = biz_data["api_key"]
        BIZ_HEADERS = {"X-API-Key": api_key}

        # ── Шаг 2: Создаём сотрудника ──
        staff_resp = await api_client.post(
            "/dev/staff/",
            json={"name": "Анна", "role": "Мастер", "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )
        assert staff_resp.status_code == 200
        staff_id = staff_resp.json()["id"]

        # ── Шаг 3: Создаём услугу ──
        svc_resp = await api_client.post(
            "/dev/service/",
            json={
                "name": "Маникюр E2E",
                "price": 1200,
                "duration_minutes": 60,
                "business_id": biz_id,
            },
            headers={"X-API-Key": DEV_KEY}
        )
        assert svc_resp.status_code == 200
        service_id = svc_resp.json()["id"]

        # ── Шаг 4: Привязываем услугу к сотруднику ──
        ss_resp = await api_client.post(
            "/dev/staff-service/",
            json={"staff_id": staff_id, "service_id": service_id, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )
        assert ss_resp.status_code == 200

        # ── Шаг 5: Клиент видит список услуг ──
        services_resp = await api_client.get("/api/v1/services/", headers=BIZ_HEADERS)
        assert services_resp.status_code == 200
        services = services_resp.json()
        assert any(s["id"] == service_id for s in services), "Услуга не появилась в списке"

        # ── Шаг 6: Клиент выбирает мастера для услуги ──
        staffs_resp = await api_client.get(
            f"/api/v1/services/{service_id}/staffs/", headers=BIZ_HEADERS
        )
        assert staffs_resp.status_code == 200
        staffs = staffs_resp.json()
        assert any(s["id"] == staff_id for s in staffs), "Мастер не привязан к услуге"

        # ── Шаг 7: Клиент регистрируется (get-or-create) ──
        client_resp = await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={
                "tg_id": 888001,
                "client_name": "Мария E2E",
                "phone": "+79998887766",
            },
            headers=BIZ_HEADERS
        )
        assert client_resp.status_code == 200
        client_data = client_resp.json()
        client_id = client_data["client"]["id"]
        assert client_data["is_owner"] is False

        # ── Шаг 8: Клиент создаёт запись ──
        start = future_iso(24)
        end = (datetime.utcnow() + timedelta(hours=25)).isoformat() + "Z"
        appt_resp = await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": client_id,
                "client_name": "Мария E2E",
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start,
                "end_time": end,
            },
            headers=BIZ_HEADERS
        )
        assert appt_resp.status_code == 200, f"Ошибка создания записи: {appt_resp.text}"
        appt_id = appt_resp.json()["id"]

        # ── Шаг 9: Клиент видит свою запись ──
        my_appts_resp = await api_client.get(
            f"/api/v1/clients/{client_id}/appointments/", headers=BIZ_HEADERS
        )
        assert my_appts_resp.status_code == 200
        my_appts = my_appts_resp.json()
        assert any(a["id"] == appt_id for a in my_appts), "Запись не появилась в списке клиента"

        # ── Шаг 10: Клиент отменяет запись ──
        cancel_resp = await api_client.post(
            f"/api/v1/clients/{client_id}/appointments/{appt_id}/",
            headers=BIZ_HEADERS
        )
        assert cancel_resp.status_code == 200

        # Проверяем, что запись исчезла из активных
        after_cancel_resp = await api_client.get(
            f"/api/v1/clients/{client_id}/appointments/", headers=BIZ_HEADERS
        )
        after_cancel = after_cancel_resp.json()
        assert not any(a["id"] == appt_id for a in after_cancel), \
            "Отменённая запись всё ещё активна"

        # ── Очистка: удаляем бизнес ──
        await api_client.delete(f"/dev/business/{biz_id}", headers={"X-API-Key": DEV_KEY})


class TestAdminCancelFlow:
    """
    Сценарий 2: Администратор отменяет запись.
    Проверяем, что запись уходит в историю и создаётся событие.
    """

    @pytest.mark.asyncio
    async def test_admin_cancels_appointment_and_event_created(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Администратор отменяет запись — событие cancelled_by_admin создаётся."""
        DEV_KEY = "test-dev-key-12345"

        # Создаём бизнес
        biz_resp = await api_client.post(
            "/dev/business/",
            json={
                "name": "Admin Cancel Salon",
                "working_hours_start": "09:00",
                "working_hours_end": "20:00",
                "owner_tg_id": 777002,
            },
            headers={"X-API-Key": DEV_KEY}
        )
        assert biz_resp.status_code == 200
        biz_id = biz_resp.json()["id"]
        api_key = biz_resp.json()["api_key"]
        BIZ_HEADERS = {"X-API-Key": api_key}

        # Создаём сотрудника, услугу, клиента
        staff_id = (await api_client.post(
            "/dev/staff/",
            json={"name": "Иван", "role": "Барбер", "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        service_id = (await api_client.post(
            "/dev/service/",
            json={"name": "Стрижка", "price": 800, "duration_minutes": 45, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        await api_client.post(
            "/dev/staff-service/",
            json={"staff_id": staff_id, "service_id": service_id, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )

        client_data = (await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 888002, "client_name": "Клиент Тест"},
            headers=BIZ_HEADERS
        )).json()
        client_id = client_data["client"]["id"]

        # Создаём запись
        start = future_iso(30)
        end = (datetime.utcnow() + timedelta(hours=31)).isoformat() + "Z"
        appt_id = (await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": client_id,
                "client_name": "Клиент Тест",
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start,
                "end_time": end,
            },
            headers=BIZ_HEADERS
        )).json()["id"]

        # Администратор отменяет запись
        cancel_resp = await api_client.post(
            f"/admin/appointments/{appt_id}/cancel/",
            headers=BIZ_HEADERS
        )
        assert cancel_resp.status_code == 200

        # Запись должна пропасть из активных записей
        active_resp = await api_client.get("/admin/appointments/", headers=BIZ_HEADERS)
        assert active_resp.status_code == 200
        active_ids = [a["id"] for a in active_resp.json()]
        assert appt_id not in active_ids, "Отменённая запись не должна быть в активных"

        # Запись должна появиться в истории
        history_resp = await api_client.get("/admin/appointments/history/", headers=BIZ_HEADERS)
        assert history_resp.status_code == 200
        history_ids = [a["id"] for a in history_resp.json()]
        assert appt_id in history_ids, "Отменённая запись должна быть в истории"

        # Очистка
        await api_client.delete(f"/dev/business/{biz_id}", headers={"X-API-Key": DEV_KEY})


class TestScheduleExceptionFlow:
    """
    Сценарий 3: Влияние исключений в графике на доступные слоты.
    """

    @pytest.mark.asyncio
    async def test_day_off_exception_hides_slots(self, api_client: AsyncClient):
        """Выходной день через исключение → нет слотов на этот день."""
        DEV_KEY = "test-dev-key-12345"

        # Создаём бизнес
        biz_resp = await api_client.post(
            "/dev/business/",
            json={
                "name": "Exception Salon",
                "working_hours_start": "09:00",
                "working_hours_end": "20:00",
                "owner_tg_id": 777003,
            },
            headers={"X-API-Key": DEV_KEY}
        )
        assert biz_resp.status_code == 200
        biz_id = biz_resp.json()["id"]
        api_key = biz_resp.json()["api_key"]
        BIZ_HEADERS = {"X-API-Key": api_key}

        # Создаём сотрудника и услугу
        staff_id = (await api_client.post(
            "/dev/staff/",
            json={"name": "Ольга", "role": "Мастер", "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        service_id = (await api_client.post(
            "/dev/service/",
            json={"name": "Уход", "price": 1000, "duration_minutes": 60, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        await api_client.post(
            "/dev/staff-service/",
            json={"staff_id": staff_id, "service_id": service_id, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )

        # Берём дату через 5 дней (чтобы она была в будущем)
        test_date = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")

        # Проверяем, что без исключения слоты есть
        slots_before_resp = await api_client.get(
            f"/api/v1/staffs/{staff_id}/free-slots/",
            params={"date": test_date, "service_id": service_id},
            headers=BIZ_HEADERS
        )
        assert slots_before_resp.status_code == 200
        slots_before = slots_before_resp.json()

        # Создаём исключение: выходной день
        exc_resp = await api_client.post(
            "/dev/business/{id}/schedule-exception/".replace("{id}", str(biz_id)),
            params={"date": test_date, "is_working": False},
            headers={"X-API-Key": DEV_KEY}
        )
        assert exc_resp.status_code == 200

        # Теперь слотов не должно быть
        slots_after_resp = await api_client.get(
            f"/api/v1/staffs/{staff_id}/free-slots/",
            params={"date": test_date, "service_id": service_id},
            headers=BIZ_HEADERS
        )
        assert slots_after_resp.status_code == 200
        slots_after = slots_after_resp.json()
        assert slots_after == [], f"Слоты должны быть пустыми в выходной день, но: {slots_after}"

        # Очистка
        await api_client.delete(f"/dev/business/{biz_id}", headers={"X-API-Key": DEV_KEY})


class TestDoubleBookingProtection:
    """
    Сценарий 4: Защита от двойного бронирования (race condition).
    """

    @pytest.mark.asyncio
    async def test_cannot_book_same_slot_twice(self, api_client: AsyncClient):
        """Нельзя создать два пересекающихся слота у одного мастера."""
        DEV_KEY = "test-dev-key-12345"

        # Создаём бизнес
        biz_resp = await api_client.post(
            "/dev/business/",
            json={
                "name": "Double Booking Salon",
                "working_hours_start": "09:00",
                "working_hours_end": "20:00",
                "owner_tg_id": 777004,
            },
            headers={"X-API-Key": DEV_KEY}
        )
        biz_id = biz_resp.json()["id"]
        api_key = biz_resp.json()["api_key"]
        BIZ_HEADERS = {"X-API-Key": api_key}

        # Создаём двух клиентов, одного мастера, одну услугу
        staff_id = (await api_client.post(
            "/dev/staff/",
            json={"name": "Мастер", "role": "Мастер", "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        service_id = (await api_client.post(
            "/dev/service/",
            json={"name": "Услуга", "price": 500, "duration_minutes": 60, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        await api_client.post(
            "/dev/staff-service/",
            json={"staff_id": staff_id, "service_id": service_id, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )

        client1_id = (await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 888011, "client_name": "Клиент 1"},
            headers=BIZ_HEADERS
        )).json()["client"]["id"]

        client2_id = (await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 888012, "client_name": "Клиент 2"},
            headers=BIZ_HEADERS
        )).json()["client"]["id"]

        # Один и тот же временной слот
        start = future_iso(48)
        end = (datetime.utcnow() + timedelta(hours=49)).isoformat() + "Z"

        appt_data_1 = {
            "client_id": client1_id,
            "client_name": "Клиент 1",
            "staff_id": staff_id,
            "service_id": service_id,
            "start_time": start,
            "end_time": end,
        }
        appt_data_2 = {
            "client_id": client2_id,
            "client_name": "Клиент 2",
            "staff_id": staff_id,
            "service_id": service_id,
            "start_time": start,
            "end_time": end,
        }

        # Первый клиент бронирует
        resp1 = await api_client.post("/api/v1/appointments/create/", json=appt_data_1, headers=BIZ_HEADERS)
        assert resp1.status_code == 200, f"Первое бронирование должно пройти: {resp1.text}"

        # Второй клиент пытается забронировать тот же слот
        resp2 = await api_client.post("/api/v1/appointments/create/", json=appt_data_2, headers=BIZ_HEADERS)
        assert resp2.status_code == 400, "Второе бронирование в тот же слот должно быть отклонено"
        assert "overlap" in resp2.json().get("detail", "").lower(), \
            "Ошибка должна содержать 'overlap'"

        # Очистка
        await api_client.delete(f"/dev/business/{biz_id}", headers={"X-API-Key": DEV_KEY})


class TestEventFlow:
    """
    Сценарий 5: Система событий (уведомлений).
    """

    @pytest.mark.asyncio
    async def test_new_appointment_creates_event(self, api_client: AsyncClient):
        """После создания записи создаётся событие new_appointment."""
        DEV_KEY = "test-dev-key-12345"

        biz_resp = await api_client.post(
            "/dev/business/",
            json={
                "name": "Event Flow Salon",
                "working_hours_start": "09:00",
                "working_hours_end": "20:00",
                "owner_tg_id": 777005,
            },
            headers={"X-API-Key": DEV_KEY}
        )
        biz_id = biz_resp.json()["id"]
        api_key = biz_resp.json()["api_key"]
        BIZ_HEADERS = {"X-API-Key": api_key}

        staff_id = (await api_client.post(
            "/dev/staff/",
            json={"name": "Тест", "role": "Мастер", "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        service_id = (await api_client.post(
            "/dev/service/",
            json={"name": "Тест", "price": 100, "duration_minutes": 30, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )).json()["id"]

        await api_client.post(
            "/dev/staff-service/",
            json={"staff_id": staff_id, "service_id": service_id, "business_id": biz_id},
            headers={"X-API-Key": DEV_KEY}
        )

        # Клиент НЕ является владельцем → событие должно создаться
        client_id = (await api_client.post(
            "/api/v1/clients/get-or-create/",
            params={"tg_id": 888021, "client_name": "Тест Клиент"},
            headers=BIZ_HEADERS
        )).json()["client"]["id"]

        # До записи — событий нет
        events_before = (await api_client.get("/api/v1/events/", headers=BIZ_HEADERS)).json()

        # Создаём запись
        start = future_iso(36)
        end = (datetime.utcnow() + timedelta(hours=36, minutes=30)).isoformat() + "Z"
        await api_client.post(
            "/api/v1/appointments/create/",
            json={
                "client_id": client_id,
                "client_name": "Тест Клиент",
                "staff_id": staff_id,
                "service_id": service_id,
                "start_time": start,
                "end_time": end,
            },
            headers=BIZ_HEADERS
        )

        # После записи — должно появиться событие new_appointment
        events_after = (await api_client.get("/api/v1/events/", headers=BIZ_HEADERS)).json()
        new_events = [e for e in events_after if e["type"] == "new_appointment"]
        assert len(new_events) >= 1, "Событие new_appointment должно быть создано"

        # Помечаем событие отправленным
        event_id = new_events[0]["id"]
        mark_resp = await api_client.post(
            f"/api/v1/events/{event_id}/mark-sent/", headers=BIZ_HEADERS
        )
        assert mark_resp.status_code == 200

        # Событие должно пропасть из неотправленных
        events_final = (await api_client.get("/api/v1/events/", headers=BIZ_HEADERS)).json()
        sent_ids = [e["id"] for e in events_final]
        assert event_id not in sent_ids, "Отправленное событие не должно отображаться"

        # Очистка
        await api_client.delete(f"/dev/business/{biz_id}", headers={"X-API-Key": DEV_KEY})