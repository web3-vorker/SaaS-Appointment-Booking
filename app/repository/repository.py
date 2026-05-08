# Repository для работы с базой данных, инкапсулирующий логику доступа к данным и проверки бизнес-правил

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload, noload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointments import AppointmentModel
from app.models.events import EventModel
from app.models.service import ServiceModel
from app.models.staffs import StaffModel
from app.models.clients import ClientModel
from app.models.business import BusinessModel
from app.models.staff_services import StaffServiceModel
from app.schemas.appointment import AppointmentCreateSchema
from app.utils.logger import logger
from app.utils.datetime_utils import now_utc, to_naive_utc
from app.utils.validators import validate_phone


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Получаем все бизнесы
    async def get_all_businesses(self) -> list[BusinessModel]:
        try:
            result = await self.session.execute(select(BusinessModel))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching businesses: {e}")
            raise

    # Получаем список сотрудников для бизнеса
    async def get_business_staffs(self, business_id: int) -> list[StaffModel]:
        try:
            staffs = await self.session.execute(
              select(StaffModel)
              .where(StaffModel.business_id == business_id)
            )
            return staffs.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching business staffs: {e}")
            raise


    # Получаем мастеров для услуги
    async def get_service_staffs(self, business_id: int, service_id: int) -> list[StaffModel]:
        try:
            staffs = await self.session.execute(
                select(StaffModel)
                .join(StaffServiceModel, StaffModel.id == StaffServiceModel.staff_id)
                .where(StaffModel.business_id == business_id)
                .where(StaffServiceModel.service_id == service_id)
            )
            return staffs.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching service staffs: {e}")
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
            logger.error(f"Error checking client and staff existence: {e}")
            raise


    # Проверяем нет ли пересечений с существующими записями для этого сотрудника
    async def has_overlapping_appointments(self, business_id: int, appointment_data: AppointmentCreateSchema) -> bool:
        try:
            # Приводим к naive UTC
            start_time = to_naive_utc(appointment_data.start_time)
            end_time = to_naive_utc(appointment_data.end_time)
            
            result = await self.session.execute(
                select(AppointmentModel)
                .with_for_update()  # Блокируем строки для предотвращения race condition
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.staff_id == appointment_data.staff_id)
                .where(AppointmentModel.status == 'scheduled')  # Проверяем только активные записи
                .where(
                    (AppointmentModel.start_time < end_time) &
                    (AppointmentModel.end_time > start_time)
                )
                .limit(1)
            )
            return result.scalars().first() is not None
        except Exception as e:
            logger.error(f"Error checking overlaps: {e}")
            raise
        

    # Получаем занятые слоты для сотрудника в заданный день
    async def get_busy_slots(self, business_id: int, staff_id: int, date: datetime) -> list[AppointmentModel]:
        # Приводим к naive UTC
        date = to_naive_utc(date)
        
        start_of_day = datetime(date.year, date.month, date.day)
        next_day = start_of_day + timedelta(days=1)

        try:
            # Загружаем только нужные поля - start_time и end_time
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
            result = await self.session.execute(
                select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).options(
                    selectinload(AppointmentModel.client),
                    selectinload(AppointmentModel.staff),
                    selectinload(AppointmentModel.service)
                )
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.client_id == client_id)
                .where(AppointmentModel.status == 'scheduled')
                .where(AppointmentModel.end_time > now_utc)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching client appointments: {e}")
            raise
    
    
    # Получаем все записи бизнеса
    async def get_business_appointments(self, business_id: int) -> list[AppointmentModel]:
        try:
            result = await self.session.execute(
                select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).options(
                    selectinload(AppointmentModel.client),
                    selectinload(AppointmentModel.staff),
                    selectinload(AppointmentModel.service)
                )
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.status == 'scheduled')
                .where(AppointmentModel.end_time > now_utc())
            )

            return result.scalars().all()
        
        except Exception as e:
            logger.error(f"Error getting business appointments: {e}")
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
            # Не делаем commit здесь - это ответственность service слоя
            return event
        except Exception as e:
            logger.error(f"Error marking event sent: {e}")
            raise


    # Отмена записи клиента
    async def cancelled_appointment(self, appointment: AppointmentModel) -> dict:
        try:
            appointment.status = "cancelled"
            # Не делаем commit здесь - это ответственность service слоя
            return {"success": "OK"}
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            raise


    # Ищем запись по id
    async def get_appointment_by_id(self, business_id: int, client_id: int, appointment_id: int) -> AppointmentModel:
      try:
        logger.info(f"Searching for appointment: business_id={business_id}, client_id={client_id}, appointment_id={appointment_id}")

        # Сначала проверим, существует ли запись вообще (без фильтра по статусу)
        result_all = await self.session.execute(
            select(AppointmentModel)
            .where(AppointmentModel.id == appointment_id)
        )
        appointment_all = result_all.scalars().first()
        if appointment_all:
            logger.info(f"Appointment exists with status: {appointment_all.status}, business: {appointment_all.business_id}, client: {appointment_all.client_id}")
        else:
            logger.warning(f"Appointment with id={appointment_id} does not exist at all")

        result = await self.session.execute(
            select(AppointmentModel)
            .options(
                selectinload(AppointmentModel.service), 
                selectinload(AppointmentModel.client),
                selectinload(AppointmentModel.staff)
            )
            .where(AppointmentModel.business_id == business_id)
            .where(AppointmentModel.client_id == client_id)
            .where(AppointmentModel.id == appointment_id)
            .where(AppointmentModel.status == "scheduled")
        )

        appointment = result.scalars().first()
        logger.info(f"Found appointment with filters: {appointment.id if appointment else 'None'}")

        return appointment

      except Exception as e:
        logger.error(f"Error in get_appointment_by_id: {e}")
        raise
      
      
    # Получение или создание клиента
    async def get_or_create_client(self, business_id: int, tg_id: int, client_name: str, phone: str = None) -> dict:
    # Получаем клиента по tg_id и business_id, если нет - создаем нового
      try:
        # Валидируем и нормализуем телефон если он передан
        normalized_phone = None
        if phone:
            normalized_phone = validate_phone(phone)
        
        result = await self.session.execute(
            select(ClientModel)
            .where(ClientModel.business_id == business_id)
            .where(ClientModel.tg_id == tg_id)
        )

        client = result.scalars().first()

        # Получаем бизнес, чтобы понять является ли пользователь владельцем
        business = await self.get_business_by_id(business_id)
        is_owner = business and business.owner_tg_id == tg_id

        if client:
            # Обновляем имя и телефон если они изменились
            updated = False
            if client.name != client_name:
                client.name = client_name
                updated = True
            if normalized_phone and client.phone != normalized_phone:
                client.phone = normalized_phone
                updated = True
            
            # Не делаем commit здесь - это ответственность service слоя
            return {"client": client, "is_owner": is_owner, "updated": updated}
        
        new_client = ClientModel(
            name=client_name,
            tg_id=tg_id,
            phone=normalized_phone,
            business_id=business_id
        )

        self.session.add(new_client)
        # Не делаем commit здесь - это ответственность service слоя
        await self.session.flush()  # Flush для получения ID

        return {"client": new_client, "is_owner": is_owner, "updated": False}
      
      except Exception as e:
        logger.error(f"Error in get_or_create_client: {e}")
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
    
    
    # Получаем бизнес по id
    async def get_business_by_id(self, business_id: int) -> BusinessModel | None:
        try:
            result = await self.session.execute(
                select(BusinessModel)
                .where(BusinessModel.id == business_id)
            )
            return result.scalars().first()
        except Exception as e:
            raise


    # Создаем новое событие
    async def create_event(self, event_type: str, business_id: int, appointment_id: int, payload: dict) -> EventModel:
        try:
            event = EventModel(
                type=event_type,
                business_id=business_id,
                appointment_id=appointment_id,
                payload=payload
            )
            self.session.add(event)
            return event
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise
