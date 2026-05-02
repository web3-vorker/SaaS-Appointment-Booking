from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


def to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None)


class AppointmentCreateSchema(BaseModel):
    client_id: int = Field(..., description="ID клиента")
    staff_id: int = Field(..., description="ID сотрудника")
    service_id: int = Field(..., description="ID услуги")
    start_time: datetime = Field(..., description="Время начала записи")
    end_time: datetime = Field(..., description="Время окончания записи")

    @field_validator('start_time')
    @classmethod
    def validate_start_time_in_future(cls, start_time: datetime) -> datetime:
        start_time = to_utc_naive(start_time)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if start_time <= now:
            raise ValueError('start_time должно быть в будущем')
        return start_time

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, end_time: datetime, info) -> datetime:
        end_time = to_utc_naive(end_time)
        start_time = info.data.get('start_time')
        if start_time is not None:
            if end_time <= start_time:
                raise ValueError('end_time должно быть больше start_time')
        return end_time