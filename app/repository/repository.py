# Repository для работы с базой данных, инкапсулирующий логику доступа к данным и проверки бизнес-правил

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointments import AppointmentModel
from app.models.events import EventModel
from app.models.service import ServiceModel
from app.models.staffs import StaffModel
from app.models.clients import ClientModel
from app.models.business import BusinessModel
from app.schemas.appointment import AppointmentCreateSchema
from app.utils.logger import logger


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Получаем список сотрудников для бизнеса
    async def get_business_staffs(self, business_id: int) -> list[StaffModel]:
        try:
            staffs = await self.session.execute(
              select(StaffModel)
              .where(StaffModel.business_id == business_id)
            )
            return staffs.scalars().all()
        except Exception as e:
            raise
        

    # Проверяем принадлежность клиента и сотрудника к бизнесу
    async def client_and_staff_exists(self, business_id: int, client_id: int, staff_id: int) -> bool:
        try:
            client_result = await self.session.execute(
                select(ClientModel)
                .where(ClientModel.business_id == business_id)
                .where(ClientModel.id == client_id)
            )
            staff_result = await self.session.execute(
                select(StaffModel)
                .where(StaffModel.business_id == business_id)
                .where(StaffModel.id == staff_id)
            )

            if not client_result.scalars().first():
                return False
                
            if not staff_result.scalars().first():
                return False

            return True
        
        except Exception as e:
            raise


    # Проверяем нет ли пересечений с существующими записями для этого сотрудника
    async def has_overlapping_appointments(self, business_id: int, appointment_data: AppointmentCreateSchema) -> bool:
        try:
            # Приводим к naive datetime
            start_time = appointment_data.start_time.replace(tzinfo=None) if appointment_data.start_time.tzinfo else appointment_data.start_time
            end_time = appointment_data.end_time.replace(tzinfo=None) if appointment_data.end_time.tzinfo else appointment_data.end_time
            
            result = await self.session.execute(
                select(AppointmentModel).limit(1)
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.staff_id == appointment_data.staff_id)
                .where(
                    (AppointmentModel.start_time < end_time) &
                    (AppointmentModel.end_time > start_time)
                )
            )
            return result.scalars().first() is not None
        except Exception as e:
            logger.error(f"Error checking overlaps: {e}")
            raise
        

    # Получаем занятые слоты для сотрудника в заданный день
    async def get_busy_slots(self, business_id: int, staff_id: int, date: datetime) -> list[AppointmentModel]:
        # Убираем timezone из date и работаем с naive UTC
        if date.tzinfo is not None:
            date = date.astimezone(timezone.utc).replace(tzinfo=None)
        
        start_of_day = datetime(date.year, date.month, date.day)
        next_day = start_of_day + timedelta(days=1)
        
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            result = await self.session.execute(
                select(AppointmentModel)
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.staff_id == staff_id)
                .where(AppointmentModel.status == "scheduled")
                .where(
                    (AppointmentModel.start_time < next_day) &
                    (AppointmentModel.end_time > start_of_day)
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching busy slots: {e}")
            raise
    

    # Получаем все записи клиента
    async def get_client_appointments(self, business_id: int, client_id: int) -> list[AppointmentModel]:
        try:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            
            result = await self.session.execute(
                select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).options(
                    selectinload(AppointmentModel.client),
                    selectinload(AppointmentModel.staff),
                    selectinload(AppointmentModel.service)
                )
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.client_id == client_id)
                .where(AppointmentModel.status == 'scheduled')
                .where(AppointmentModel.start_time > now_utc)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching client appointments: {e}")
            raise
    
    
    # Получаем все услуги бизнеса
    async def get_business_services(self, business_id: int) -> list[ServiceModel]:
        try:
            result = await self.session.execute(
                select(ServiceModel)
                .where(ServiceModel.business_id == business_id)
            )

            return result.scalars().all()
        except Exception as e:
            raise
        

    # Получаем услугу по id
    async def get_service_by_id(self, business_id: int, service_id: int) -> ServiceModel:
        try:
            result = await self.session.execute(
                select(ServiceModel)
                .where(ServiceModel.business_id == business_id)
                .where(ServiceModel.id == service_id)
            )

            return result.scalars().first()
        
        except Exception as e:
           raise


    # Добавляем новую запись в базу данных
    async def add_appointment(self, appointment: AppointmentModel) -> AppointmentModel:
      try: 
        self.session.add(appointment)
        return appointment
      except Exception as e:
        await self.session.rollback()
        raise
      

    # Получаем все ожидающие отправки события для бизнеса
    async def get_pending_events(self, business_id: int) -> list[EventModel]:
        try:
            result = await self.session.execute(
                select(EventModel)
                .where(EventModel.business_id == business_id)
                .where(EventModel.is_sent == False)
                .order_by(EventModel.created_at.asc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching pending events: {e}")
            raise

    # Помечаем событие как отправленное
    async def mark_event_sent(self, event_id: int, business_id: int) -> EventModel:
        try:
            result = await self.session.execute(
                select(EventModel)
                .where(EventModel.id == event_id)
                .where(EventModel.business_id == business_id)
            )
            event = result.scalars().first()
            if not event:
                return None
            event.is_sent = True
            return event
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error marking event sent: {e}")
            raise


    # Отмена записи клиента
    async def cancelled_appointment(self, appointment: AppointmentModel) -> dict:
        try:
            appointment.status = "cancelled"
            return {"success": "OK"}
        except Exception as e:
            await self.session.rollback()
            raise


    # Ищем запись по id
    async def get_appointment_by_id(self, business_id: int, client_id: int, appointment_id: int) -> AppointmentModel:
      try:
        result = await self.session.execute(
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.service), selectinload(AppointmentModel.client))
            .where(AppointmentModel.business_id == business_id)
            .where(AppointmentModel.client_id == client_id)
            .where(AppointmentModel.id == appointment_id)
            .where(AppointmentModel.status == "scheduled")
            .where(AppointmentModel.start_time > datetime.now().replace(tzinfo=None))
        )

        return result.scalars().first()
      
      except Exception as e:
        raise
      
      
    # Получение или создание клиента
    async def get_or_create_client(self, business_id: int, tg_id: int, client_name: str) -> ClientModel:
      try:
        result = await self.session.execute(
            select(ClientModel)
            .where(ClientModel.business_id == business_id)
            .where(ClientModel.tg_id == tg_id)
        )

        client = result.scalars().first()

        if client:
            return client
        
        new_client = ClientModel(
            name=client_name,
            tg_id=tg_id,
            business_id=business_id
        )

        self.session.add(new_client)
        await self.session.commit()
        await self.session.refresh(new_client)

        return new_client
      
      except Exception as e:
        await self.session.rollback()
        raise


    # Получаем бизнес по API Key
    async def get_business_by_api_key(self, api_key: str) -> BusinessModel | None:
        try:
            result = await self.session.execute(
                select(BusinessModel)
                .where(BusinessModel.api_key == api_key)
            )
            return result.scalars().first()
        except Exception as e:
            raise
