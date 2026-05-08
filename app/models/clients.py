# Модель данных для клиентов

from datetime import datetime
from pydantic import EmailStr, Field
from app.models.base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, UniqueConstraint, Index, BigInteger
from sqlalchemy.orm import relationship


class ClientModel(Base):
    __tablename__ = 'clients'

    __table_args__ = (
        UniqueConstraint('business_id', 'tg_id', name='uq_client_business_tg'),
        Index('ix_clients_business_id', 'business_id'),
        Index('ix_clients_business_client', 'business_id', 'id'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    tg_id = Column(BigInteger, nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    appointments = relationship('AppointmentModel', back_populates='client', cascade='all, delete')
    business = relationship('BusinessModel', back_populates='clients')
