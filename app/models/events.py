from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime, UniqueConstraint, Index
from app.models.base import Base


class EventModel(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("type", "appointment_id", name="uq_event_type_appointment"),
        # Индекс для быстрого поиска неотправленных событий по бизнесу
        Index('ix_events_business_pending', 'business_id', 'is_sent'),
        # Индекс для очистки старых событий
        Index('ix_events_sent_created', 'is_sent', 'created_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(100), nullable=False)
    business_id = Column(Integer, nullable=False)
    appointment_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    is_sent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
