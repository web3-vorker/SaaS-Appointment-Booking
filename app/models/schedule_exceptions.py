# Модель для исключений в графике работы бизнеса

from sqlalchemy import Column, Integer, ForeignKey, Date, Boolean, Time, Index
from sqlalchemy.orm import relationship

from app.models.base import Base


class ScheduleExceptionModel(Base):
    __tablename__ = 'schedule_exceptions'
    
    __table_args__ = (
        # Индекс для быстрого поиска исключений по бизнесу и дате
        Index('ix_schedule_exceptions_business_date', 'business_id', 'date'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    
    # Дата исключения
    date = Column(Date, nullable=False)
    
    # Работает ли бизнес в этот день
    # False = выходной день (полностью закрыто)
    # True = рабочий день с особым графиком
    is_working = Column(Boolean, nullable=False, default=True)
    
    # Кастомное рабочее время для этого дня (если is_working=True)
    # Если None, используется стандартное рабочее время бизнеса
    custom_start_time = Column(Time, nullable=True)
    custom_end_time = Column(Time, nullable=True)
    
    # Связь с бизнесом
    business = relationship('BusinessModel', back_populates='schedule_exceptions')
