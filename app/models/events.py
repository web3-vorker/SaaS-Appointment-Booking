from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime, UniqueConstraint
from app.models.base import Base


class EventModel(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("type", "appointment_id", name="uq_event_type_appointment"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(100), nullable=False)
    business_id = Column(Integer, nullable=False)
    appointment_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    is_sent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
