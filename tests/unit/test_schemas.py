"""
Unit тесты для Pydantic схем.

Тестируем валидаторы схем без обращения к БД.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from app.schemas.appointment import AppointmentCreateSchema
from app.schemas.business import BusinessCreateSchema
from app.schemas.service import ServiceCreateSchema
from app.schemas.staff import StaffCreateSchema


class TestAppointmentCreateSchema:
    """Тесты схемы создания записи."""

    def _future_dt(self, offset_hours=2):
        return datetime.now(timezone.utc) + timedelta(hours=offset_hours)

    def test_valid_appointment(self):
        start = self._future_dt(2)
        end = start + timedelta(hours=1)
        schema = AppointmentCreateSchema(
            client_id=1, client_name="Иван Иванов",
            staff_id=1, service_id=1, start_time=start, end_time=end,
        )
        assert schema.client_id == 1
        assert schema.client_name == "Иван Иванов"

    def test_start_time_in_past_raises(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc) + timedelta(hours=1)
        with pytest.raises(ValidationError):
            AppointmentCreateSchema(
                client_id=1, client_name="Тест",
                staff_id=1, service_id=1, start_time=past, end_time=end,
            )

    def test_end_before_start_raises(self):
        start = self._future_dt(2)
        end = start - timedelta(minutes=30)
        with pytest.raises(ValidationError):
            AppointmentCreateSchema(
                client_id=1, client_name="Тест",
                staff_id=1, service_id=1, start_time=start, end_time=end,
            )

    def test_end_equals_start_raises(self):
        start = self._future_dt(2)
        with pytest.raises(ValidationError):
            AppointmentCreateSchema(
                client_id=1, client_name="Тест",
                staff_id=1, service_id=1, start_time=start, end_time=start,
            )

    def test_start_time_converted_to_naive_utc(self):
        start = self._future_dt(2)
        end = start + timedelta(hours=1)
        schema = AppointmentCreateSchema(
            client_id=1, client_name="Тест",
            staff_id=1, service_id=1, start_time=start, end_time=end,
        )
        assert schema.start_time.tzinfo is None
        assert schema.end_time.tzinfo is None


class TestBusinessCreateSchema:
    """Тесты схемы создания бизнеса."""

    def test_valid_business(self):
        schema = BusinessCreateSchema(
            name="Мой салон", working_hours_start="09:00",
            working_hours_end="20:00", owner_tg_id=123456789,
        )
        assert schema.name == "Мой салон"

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            BusinessCreateSchema(
                name="А", working_hours_start="09:00",
                working_hours_end="20:00", owner_tg_id=123456789,
            )

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            BusinessCreateSchema(
                name="А" * 51, working_hours_start="09:00",
                working_hours_end="20:00", owner_tg_id=123456789,
            )

    def test_invalid_time_format_raises(self):
        with pytest.raises(ValidationError):
            BusinessCreateSchema(
                name="Салон", working_hours_start="9:00",
                working_hours_end="20:00", owner_tg_id=123456789,
            )

    def test_invalid_hours_raises(self):
        with pytest.raises(ValidationError):
            BusinessCreateSchema(
                name="Салон", working_hours_start="25:00",
                working_hours_end="20:00", owner_tg_id=123456789,
            )

    def test_optional_break_fields(self):
        schema = BusinessCreateSchema(
            name="Салон", working_hours_start="09:00",
            working_hours_end="20:00", owner_tg_id=123456789,
        )
        assert schema.break_start is None
        assert schema.break_end is None

    def test_with_break(self):
        schema = BusinessCreateSchema(
            name="Салон", working_hours_start="09:00",
            working_hours_end="20:00", break_start="13:00",
            break_end="14:00", owner_tg_id=123456789,
        )
        assert schema.break_start == "13:00"
        assert schema.break_end == "14:00"

    def test_subscription_plan_null_defaults_to_base(self):
        schema = BusinessCreateSchema(
            name="Салон", working_hours_start="09:00",
            working_hours_end="20:00", owner_tg_id=123456789,
            subscription_plan=None,
        )
        assert schema.subscription_plan == "Base"


class TestServiceCreateSchema:
    """Тесты схемы создания услуги."""

    def test_valid_service(self):
        schema = ServiceCreateSchema(
            business_id=1, name="Маникюр", price=1200, duration_minutes=60,
        )
        assert schema.name == "Маникюр"
        assert schema.price == 1200

    def test_description_is_optional(self):
        schema = ServiceCreateSchema(
            business_id=1, name="Маникюр", price=1200, duration_minutes=60,
        )
        assert schema.description is None


class TestStaffCreateSchema:
    """Тесты схемы создания сотрудника."""

    def test_valid_staff(self):
        schema = StaffCreateSchema(name="Анна", business_id=1, role="Мастер")
        assert schema.name == "Анна"
        assert schema.role == "Мастер"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            StaffCreateSchema(business_id=1, role="Мастер")

    def test_missing_role_raises(self):
        with pytest.raises(ValidationError):
            StaffCreateSchema(name="Анна", business_id=1)