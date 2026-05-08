# Модель для связи между сотрудниками и услугами, которые они предоставляют

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

class StaffServiceModel(Base):
  __tablename__ = 'staff_services'

  __table_args__ = (
      Index('ix_staff_services_business_id', 'business_id'),
  )

  id = Column(Integer, primary_key=True)
  staff_id = Column(Integer, ForeignKey('staffs.id'), nullable=False)
  service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
  business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)

  staff = relationship('StaffModel', back_populates='services')
  service = relationship('ServiceModel', back_populates='staffs')
  business = relationship('BusinessModel', back_populates='staff_services')