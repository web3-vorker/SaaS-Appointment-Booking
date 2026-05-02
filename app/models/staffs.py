# Модель данных для сотрудников

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

class StaffModel(Base):
  __tablename__ = 'staffs'

  __table_args__ = (
      Index('ix_staffs_business_id', 'business_id'),
  )

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
  role = Column(String, nullable=False)

  business = relationship('BusinessModel', back_populates='staffs')
  appointments = relationship('AppointmentModel', back_populates='staff', cascade='all, delete')