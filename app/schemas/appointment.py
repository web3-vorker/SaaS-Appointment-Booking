from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from app.utils.datetime_utils import now_utc, to_naive_utc


class AppointmentCreateSchema(BaseModel):
    client_id: int = Field(..., description="ID клиента")
    client_name: str = Field(..., description="Имя клиента")
    staff_id: int = Field(..., description="ID сотрудника")
    service_id: int = Field(..., description="ID услуги")
    start_time: datetime = Field(..., description="Время начала записи")
    end_time: datetime = Field(..., description="Время окончания записи")

    @field_validator('start_time')
    @classmethod
    def validate_start_time_in_future(cls, start_time: datetime) -> datetime:
        start_time = to_naive_utc(start_time)
        now = now_utc()
        if start_time <= now:
            raise ValueError('start_time должно быть в будущем')
        return start_time

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, end_time: datetime, info) -> datetime:
        end_time = to_naive_utc(end_time)
        start_time = info.data.get('start_time')
        if start_time is not None:
            if end_time <= start_time:
                raise ValueError('end_time должно быть больше start_time')
        return end_time
