from pydantic import BaseModel, Field
from typing import Optional

class ScheduleExceptionCreateSchema(BaseModel):
    business_id: int
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")  # Дата в формате YYYY-MM-DD
    is_working_day: bool = Field(default=False)  # Является ли этот день рабочим
    work_start: Optional[str] = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")  # Время начала работы в этот день (если рабочий день)
    work_end: Optional[str] = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")  # Время окончания работы в этот день (если рабочий день)