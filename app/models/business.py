# Модель данных для бизнесов

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base

class BusinessModel(Base):
  __tablename__ = 'businesses'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  created_at = Column(DateTime, default=datetime.now)
  is_active = Column(Boolean, default=True)
  bot_token = Column(String, unique=True)
  owner_tg_id = Column(Integer, nullable=False)
  api_key = Column(String, default=lambda: str(uuid.uuid4()), unique=True)

  staffs = relationship('StaffModel', back_populates='business', cascade='all, delete')
  services = relationship('ServiceModel', back_populates='business', cascade='all, delete')
  clients = relationship('ClientModel', back_populates='business', cascade='all, delete')
  appointments = relationship('AppointmentModel', back_populates='business', cascade='all, delete')