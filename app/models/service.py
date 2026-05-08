# Модель данных для услуг

from sqlalchemy import Column, Integer, ForeignKey, String, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

class ServiceModel(Base):
  __tablename__ = 'services'

  __table_args__ = (
    Index('ix_services_business_id', 'business_id'),
  )

  id = Column(Integer, primary_key=True)
  business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
  name = Column(String, nullable=False)
  price = Column(Integer, nullable=False)
  description = Column(String, nullable=True)
  duration_minutes = Column(Integer, nullable=False)

  business = relationship('BusinessModel', back_populates='services')
  appointments = relationship('AppointmentModel', back_populates='service')
  staffs = relationship('StaffServiceModel', back_populates='service', cascade='all, delete')