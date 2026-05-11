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
from app.models.schedule_exceptions import ScheduleExceptionModel
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

            client = client_result.scalars().first()
            staff = staff_result.scalars().first()
            
            if not client or not staff:
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
                .where(AppointmentModel.end_time > now_utc())
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


    # Получаем историю записей бизнеса (все записи, включая отмененные и прошедшие)
    async def get_business_appointment_history(self, business_id: int) -> list[AppointmentModel]:
        try:
            result = await self.session.execute(
                select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).options(
                    selectinload(AppointmentModel.client),
                    selectinload(AppointmentModel.staff),
                    selectinload(AppointmentModel.service)
                )
                .where(AppointmentModel.business_id == business_id)
            )

            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting business appointment history: {e}")
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
            logger.error(f"Error marking event sent: {e}")
            raise


    # Отмена записи клиента
    async def cancelled_appointment(self, appointment: AppointmentModel) -> dict:
        try:
            appointment.status = "cancelled"
            return {"success": "OK"}
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            raise


# Ищем запись по id
    async def get_appointment_by_id(self, business_id: int, client_id: int, appointment_id: int) -> AppointmentModel:
      try:
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

        return result.scalars().first()

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
            
            return {"client": client, "is_owner": is_owner, "updated": updated}
        
        new_client = ClientModel(
            name=client_name,
            tg_id=tg_id,
            phone=normalized_phone,
            business_id=business_id
        )

        self.session.add(new_client)
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


    # Получаем исключение в графике для конкретной даты
    async def get_schedule_exception(self, business_id: int, date: datetime) -> ScheduleExceptionModel | None:
        try:
            result = await self.session.execute(
                select(ScheduleExceptionModel)
                .where(ScheduleExceptionModel.business_id == business_id)
                .where(ScheduleExceptionModel.date == date.date())
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching schedule exception: {e}")
            raise


    # Получаем все исключения в графике для бизнеса в диапазоне дат
    async def get_schedule_exceptions_range(self, business_id: int, start_date: datetime, end_date: datetime) -> list[ScheduleExceptionModel]:
        try:
            result = await self.session.execute(
                select(ScheduleExceptionModel)
                .where(ScheduleExceptionModel.business_id == business_id)
                .where(ScheduleExceptionModel.date >= start_date.date())
                .where(ScheduleExceptionModel.date <= end_date.date())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching schedule exceptions range: {e}")
            raise


    # Измнение статуса записи (для админки)
    async def update_appointment_status(self, appointment: AppointmentModel, new_status: str) -> dict:
        try:
            appointment.status = new_status
            return {"message": "Статус записи успешно обновлен"}
        except Exception as e:
            logger.error(f"Error updating appointment status: {e}")
            raise


    # Получаем неотмеченные записи (прошедшие со статусом scheduled)
    async def get_unmarked_appointments(self, business_id: int) -> list[AppointmentModel]:
        try:
            result = await self.session.execute(
                select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).options(
                    selectinload(AppointmentModel.client),
                    selectinload(AppointmentModel.staff),
                    selectinload(AppointmentModel.service)
                )
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.status == 'scheduled')
                .where(AppointmentModel.end_time <= now_utc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching unmarked appointments: {e}")
            raise


    # Создаем сотрудника
    async def create_staff(self, business_id: int, name: str, role: str) -> StaffModel:
        try:
            new_staff = StaffModel(
                name=name,
                business_id=business_id,
                role=role
            )
            self.session.add(new_staff)
            return new_staff
        except Exception as e:
            logger.error(f"Error creating staff: {e}")
            raise


    # Удаляем сотрудника
    async def delete_staff(self, business_id: int, staff_id: int) -> StaffModel:
        try:
            result = await self.session.execute(
                select(StaffModel)
                .where(StaffModel.id == staff_id)
                .where(StaffModel.business_id == business_id)
            )
            staff = result.scalars().first()
            if not staff:
                return None
            await self.session.delete(staff)
            return staff
        except Exception as e:
            logger.error(f"Error deleting staff: {e}")
            raise


    # Создаем услугу
    async def create_service(self, business_id: int, name: str, price: int, description: str, duration_minutes: int) -> ServiceModel:
        try:
            new_service = ServiceModel(
                name=name,
                business_id=business_id,
                price=price,
                description=description,
                duration_minutes=duration_minutes
            )
            self.session.add(new_service)
            return new_service
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise


    # Удаляем услугу
    async def delete_service(self, business_id: int, service_id: int) -> ServiceModel:
        try:
            result = await self.session.execute(
                select(ServiceModel)
                .where(ServiceModel.id == service_id)
                .where(ServiceModel.business_id == business_id)
            )
            service = result.scalars().first()
            if not service:
                return None
            await self.session.delete(service)
            return service
        except Exception as e:
            logger.error(f"Error deleting service: {e}")
            raise


    # Создаем связь сотрудник-услуга
    async def create_staff_service(self, business_id: int, staff_id: int, service_id: int) -> StaffServiceModel:
        try:
            new_staff_service = StaffServiceModel(
                staff_id=staff_id,
                service_id=service_id,
                business_id=business_id
            )
            self.session.add(new_staff_service)
            return new_staff_service
        except Exception as e:
            logger.error(f"Error creating staff service: {e}")
            raise


    # Получаем запись по ID для отмены админом
    async def get_appointment_for_cancel(self, business_id: int, appointment_id: int) -> AppointmentModel:
        try:
            result = await self.session.execute(
                select(AppointmentModel)
                .options(selectinload(AppointmentModel.client))
                .where(AppointmentModel.id == appointment_id)
                .where(AppointmentModel.business_id == business_id)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching appointment for cancel: {e}")
            raise


    # Создаем исключение в графике
    async def create_schedule_exception(self, business_id: int, date: str, is_working: bool, custom_start: str = None, custom_end: str = None) -> ScheduleExceptionModel:
        try:
            from datetime import time
            exc = ScheduleExceptionModel(
                business_id=business_id,
                date=datetime.strptime(date, "%Y-%m-%d").date(),
                is_working=is_working
            )
            
            if custom_start:
                h, m = map(int, custom_start.split(':'))
                exc.custom_start_time = time(h, m)
            
            if custom_end:
                h, m = map(int, custom_end.split(':'))
                exc.custom_end_time = time(h, m)
            
            self.session.add(exc)
            return exc
        except Exception as e:
            logger.error(f"Error creating schedule exception: {e}")
            raise


    # Получаем все исключения в графике для бизнеса
    async def get_all_schedule_exceptions(self, business_id: int) -> list[ScheduleExceptionModel]:
        try:
            result = await self.session.execute(
                select(ScheduleExceptionModel)
                .where(ScheduleExceptionModel.business_id == business_id)
                .order_by(ScheduleExceptionModel.date)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching schedule exceptions: {e}")
            raise


    # Удаляем исключение в графике
    async def delete_schedule_exception(self, business_id: int, exception_id: int) -> ScheduleExceptionModel:
        try:
            result = await self.session.execute(
                select(ScheduleExceptionModel)
                .where(ScheduleExceptionModel.id == exception_id)
                .where(ScheduleExceptionModel.business_id == business_id)
            )
            exception = result.scalars().first()
            if not exception:
                return None
            await self.session.delete(exception)
            return exception
        except Exception as e:
            logger.error(f"Error deleting schedule exception: {e}")
            raise
