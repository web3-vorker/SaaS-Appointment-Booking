from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import Any, Dict
from datetime import datetime


class EventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    business_id: int
    appointment_id: int
    payload: Dict[str, Any]  # Гибкий payload для разных типов событий
    is_sent: bool
    created_at: datetime
