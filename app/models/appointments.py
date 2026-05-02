# Модель данных для записей

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

class AppointmentModel(Base):
  __tablename__ = 'appointments'

  __table_args__ = (
    Index('ix_appointments_staff_time', 'business_id', 'staff_id', 'start_time'),
    # для списка записей клиента
    Index('ix_appointments_client_status_start', 'business_id', 'client_id', 'status', 'start_time'),
    # для быстрой фильтрации по времени
    Index('ix_appointments_start_time', 'start_time'),
    # внешние ключи (не обязательны, но ускорят JOIN'ы)
    Index('ix_appointments_business_id', 'business_id'),
    Index('ix_appointments_client_id', 'client_id'),
    Index('ix_appointments_staff_id', 'staff_id'),
    Index('ix_appointments_service_id', 'service_id'),
  )

  id = Column(Integer, primary_key=True)
  business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
  client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
  staff_id = Column(Integer, ForeignKey('staffs.id'), nullable=False)
  service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
  start_time = Column(DateTime, nullable=False)
  end_time = Column(DateTime, nullable=False)
  status = Column(String, nullable=False, default='scheduled')

  client = relationship('ClientModel', back_populates='appointments')
  staff = relationship('StaffModel', back_populates='appointments')
  business = relationship('BusinessModel', back_populates='appointments')
  service = relationship('ServiceModel', back_populates='appointments')