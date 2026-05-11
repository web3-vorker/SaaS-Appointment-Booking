# Модель данных для бизнесов

from sqlalchemy import Boolean, Column, DateTime, Integer, String, BigInteger, Time, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base

class BusinessModel(Base):
  __tablename__ = 'businesses'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  
  # Стандартное рабочее время
  working_time_start = Column(Time, nullable=False)  # Начало рабочего дня
  working_time_end = Column(Time, nullable=False)    # Конец рабочего дня
  
  # Перерыв (обед)
  break_start = Column(Time, nullable=True)  # Начало перерыва
  break_end = Column(Time, nullable=True)    # Конец перерыва
  
  # Выходные дни (список номеров дней недели: 0=Пн, 6=Вс)
  # Хранится как JSON массив, например: [5, 6] для Сб и Вс
  weekend_days = Column(JSON, nullable=True, default=list)
  
  created_at = Column(DateTime, default=datetime.now)
  is_active = Column(Boolean, default=True)
  bot_token = Column(String, unique=True)
  owner_tg_id = Column(BigInteger, nullable=False)
  api_key = Column(String, default=lambda: str(uuid.uuid4()), unique=True)

  staffs = relationship('StaffModel', back_populates='business', cascade='all, delete')
  services = relationship('ServiceModel', back_populates='business', cascade='all, delete')
  clients = relationship('ClientModel', back_populates='business', cascade='all, delete')
  appointments = relationship('AppointmentModel', back_populates='business', cascade='all, delete')
  staff_services = relationship('StaffServiceModel', back_populates='business', cascade='all, delete')
  schedule_exceptions = relationship('ScheduleExceptionModel', back_populates='business', cascade='all, delete')