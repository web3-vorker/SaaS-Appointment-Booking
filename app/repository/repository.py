# Repository РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С…, РёРЅРєР°РїСЃСѓР»РёСЂСѓСЋС‰РёР№ Р»РѕРіРёРєСѓ РґРѕСЃС‚СѓРїР° Рє РґР°РЅРЅС‹Рј Рё РїСЂРѕРІРµСЂРєРё Р±РёР·РЅРµСЃ-РїСЂР°РІРёР»

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

    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ Р±РёР·РЅРµСЃС‹
    async def get_all_businesses(self) -> list[BusinessModel]:
        try:
            result = await self.session.execute(select(BusinessModel))
            return result.scalars().all()
        except Exception as e:
            logger.error("error_fetching_businesses", error=str(e), error_type=type(e).__name__, exc_info=True)
            raise

    # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ РґР»СЏ Р±РёР·РЅРµСЃР°
    async def get_business_staffs(self, business_id: int) -> list[StaffModel]:
        try:
            staffs = await self.session.execute(
              select(StaffModel)
              .where(StaffModel.business_id == business_id)
            )
            return staffs.scalars().all()
        except Exception as e:
            logger.error("error_fetching_business_staffs", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј РјР°СЃС‚РµСЂРѕРІ РґР»СЏ СѓСЃР»СѓРіРё
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
            logger.error("error_fetching_service_staffs", business_id=business_id, service_id=service_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise
        

    # РџСЂРѕРІРµСЂСЏРµРј РїСЂРёРЅР°РґР»РµР¶РЅРѕСЃС‚СЊ РєР»РёРµРЅС‚Р° Рё СЃРѕС‚СЂСѓРґРЅРёРєР° Рє Р±РёР·РЅРµСЃСѓ
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
            logger.error("error_checking_client_staff_existence", business_id=business_id, client_id=client_id, staff_id=staff_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџСЂРѕРІРµСЂСЏРµРј РЅРµС‚ Р»Рё РїРµСЂРµСЃРµС‡РµРЅРёР№ СЃ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРјРё Р·Р°РїРёСЃСЏРјРё РґР»СЏ СЌС‚РѕРіРѕ СЃРѕС‚СЂСѓРґРЅРёРєР°
    async def has_overlapping_appointments(self, business_id: int, appointment_data: AppointmentCreateSchema) -> bool:
        try:
            # РџСЂРёРІРѕРґРёРј Рє naive UTC
            start_time = to_naive_utc(appointment_data.start_time)
            end_time = to_naive_utc(appointment_data.end_time)
            
            result = await self.session.execute(
                select(AppointmentModel)
                .with_for_update()  # Р‘Р»РѕРєРёСЂСѓРµРј СЃС‚СЂРѕРєРё РґР»СЏ РїСЂРµРґРѕС‚РІСЂР°С‰РµРЅРёСЏ race condition
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.staff_id == appointment_data.staff_id)
                .where(AppointmentModel.status == 'scheduled')  # РџСЂРѕРІРµСЂСЏРµРј С‚РѕР»СЊРєРѕ Р°РєС‚РёРІРЅС‹Рµ Р·Р°РїРёСЃРё
                .where(
                    (AppointmentModel.start_time < end_time) &
                    (AppointmentModel.end_time > start_time)
                )
                .limit(1)
            )
            return result.scalars().first() is not None
        except Exception as e:
            logger.error("error_checking_overlaps", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise
        

    # РџРѕР»СѓС‡Р°РµРј Р·Р°РЅСЏС‚С‹Рµ СЃР»РѕС‚С‹ РґР»СЏ СЃРѕС‚СЂСѓРґРЅРёРєР° РІ Р·Р°РґР°РЅРЅС‹Р№ РґРµРЅСЊ
    async def get_busy_slots(self, business_id: int, staff_id: int, date: datetime) -> list[AppointmentModel]:
        # РџСЂРёРІРѕРґРёРј Рє naive UTC
        date = to_naive_utc(date)
        
        start_of_day = datetime(date.year, date.month, date.day)
        next_day = start_of_day + timedelta(days=1)

        try:
            # Р—Р°РіСЂСѓР¶Р°РµРј С‚РѕР»СЊРєРѕ РЅСѓР¶РЅС‹Рµ РїРѕР»СЏ - start_time Рё end_time
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
            logger.error("error_fetching_busy_slots", business_id=business_id, staff_id=staff_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise
    

    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ Р·Р°РїРёСЃРё РєР»РёРµРЅС‚Р°
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
            logger.error("error_fetching_client_appointments_repo", business_id=business_id, client_id=client_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise
    
    
    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ Р·Р°РїРёСЃРё Р±РёР·РЅРµСЃР°
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
            logger.error("error_getting_business_appointments", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј РёСЃС‚РѕСЂРёСЋ Р·Р°РїРёСЃРµР№ Р±РёР·РЅРµСЃР° (РІСЃРµ Р·Р°РїРёСЃРё, РІРєР»СЋС‡Р°СЏ РѕС‚РјРµРЅРµРЅРЅС‹Рµ Рё РїСЂРѕС€РµРґС€РёРµ)
    async def get_business_appointment_history(self, business_id: int) -> list[AppointmentModel]:
        try:
            result = await self.session.execute(
                select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).options(
                    selectinload(AppointmentModel.client),
                    selectinload(AppointmentModel.staff),
                    selectinload(AppointmentModel.service)
                )
                .where(AppointmentModel.business_id == business_id)
                .where(AppointmentModel.end_time <= now_utc())
            )

            return result.scalars().all()
        except Exception as e:
            logger.error("error_getting_appointment_history", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise
    
    
    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ СѓСЃР»СѓРіРё Р±РёР·РЅРµСЃР°
    async def get_business_services(self, business_id: int) -> list[ServiceModel]:
        try:
            result = await self.session.execute(
                select(ServiceModel)
                .where(ServiceModel.business_id == business_id)
            )

            return result.scalars().all()
        except Exception as e:
            raise
        

    # РџРѕР»СѓС‡Р°РµРј СѓСЃР»СѓРіСѓ РїРѕ id
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


    # Р”РѕР±Р°РІР»СЏРµРј РЅРѕРІСѓСЋ Р·Р°РїРёСЃСЊ РІ Р±Р°Р·Сѓ РґР°РЅРЅС‹С…
    async def add_appointment(self, appointment: AppointmentModel) -> AppointmentModel:
      try: 
        self.session.add(appointment)
        return appointment
      except Exception as e:
        await self.session.rollback()
        raise
      

    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ РѕР¶РёРґР°СЋС‰РёРµ РѕС‚РїСЂР°РІРєРё СЃРѕР±С‹С‚РёСЏ РґР»СЏ Р±РёР·РЅРµСЃР°
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
            logger.error("error_fetching_pending_events_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise

    # РџРѕРјРµС‡Р°РµРј СЃРѕР±С‹С‚РёРµ РєР°Рє РѕС‚РїСЂР°РІР»РµРЅРЅРѕРµ
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
            logger.error("error_marking_event_sent_repo", event_id=event_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РћС‚РјРµРЅР° Р·Р°РїРёСЃРё РєР»РёРµРЅС‚Р°
    async def cancelled_appointment(self, appointment: AppointmentModel) -> dict:
        try:
            appointment.status = "cancelled"
            return {"success": "OK"}
        except Exception as e:
            logger.error("error_cancelling_appointment_repo", error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


# РС‰РµРј Р·Р°РїРёСЃСЊ РїРѕ id
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
          logger.error("error_get_appointment_by_id", business_id=business_id, client_id=client_id, appointment_id=appointment_id, error=str(e), error_type=type(e).__name__, exc_info=True)
          raise
      
      
    # РџРѕР»СѓС‡РµРЅРёРµ РёР»Рё СЃРѕР·РґР°РЅРёРµ РєР»РёРµРЅС‚Р°
    async def get_or_create_client(self, business_id: int, tg_id: int, client_name: str, phone: str = None) -> dict:
    # РџРѕР»СѓС‡Р°РµРј РєР»РёРµРЅС‚Р° РїРѕ tg_id Рё business_id, РµСЃР»Рё РЅРµС‚ - СЃРѕР·РґР°РµРј РЅРѕРІРѕРіРѕ
      try:
        # Р’Р°Р»РёРґРёСЂСѓРµРј Рё РЅРѕСЂРјР°Р»РёР·СѓРµРј С‚РµР»РµС„РѕРЅ РµСЃР»Рё РѕРЅ РїРµСЂРµРґР°РЅ
        normalized_phone = None
        if phone:
            normalized_phone = validate_phone(phone)
        
        result = await self.session.execute(
            select(ClientModel)
            .where(ClientModel.business_id == business_id)
            .where(ClientModel.tg_id == tg_id)
        )

        client = result.scalars().first()

        # РџРѕР»СѓС‡Р°РµРј Р±РёР·РЅРµСЃ, С‡С‚РѕР±С‹ РїРѕРЅСЏС‚СЊ СЏРІР»СЏРµС‚СЃСЏ Р»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ РІР»Р°РґРµР»СЊС†РµРј
        business = await self.get_business_by_id(business_id)
        is_owner = business and business.owner_tg_id == tg_id

        if client:
            # РћР±РЅРѕРІР»СЏРµРј РёРјСЏ Рё С‚РµР»РµС„РѕРЅ РµСЃР»Рё РѕРЅРё РёР·РјРµРЅРёР»РёСЃСЊ
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
        await self.session.flush()  # Flush РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ ID

        return {"client": new_client, "is_owner": is_owner, "updated": False}
      
      except Exception as e:
        logger.error("error_get_or_create_client_repo", business_id=business_id, tg_id=tg_id, error=str(e), error_type=type(e).__name__, exc_info=True)
        raise


    # РџРѕР»СѓС‡Р°РµРј Р±РёР·РЅРµСЃ РїРѕ API Key
    async def get_business_by_api_key(self, api_key: str) -> BusinessModel | None:
        try:
            result = await self.session.execute(
                select(BusinessModel)
                .where(BusinessModel.api_key == api_key)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error("error_fetching_business_by_api_key_repo", api_key=api_key, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise
    
    
    # РџРѕР»СѓС‡Р°РµРј Р±РёР·РЅРµСЃ РїРѕ id
    async def get_business_by_id(self, business_id: int) -> BusinessModel | None:
        try:
            result = await self.session.execute(
                select(BusinessModel)
                .where(BusinessModel.id == business_id)
            )
            return result.scalars().first()
        except Exception as e:
            raise


    # Получение бизнеса по токену бота
    async def get_business_by_bot_token(self, bot_token: str) -> BusinessModel | None:
        try:
            result = await self.session.execute(
                select(BusinessModel)
                .where(BusinessModel.bot_token == bot_token)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error("error_fetching_business_by_bot_token_repo", bot_token=bot_token, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЎРѕР·РґР°РµРј РЅРѕРІРѕРµ СЃРѕР±С‹С‚РёРµ
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
            logger.error("error_creating_event", event_type=event_type, business_id=business_id, appointment_id=appointment_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј РёСЃРєР»СЋС‡РµРЅРёРµ РІ РіСЂР°С„РёРєРµ РґР»СЏ РєРѕРЅРєСЂРµС‚РЅРѕР№ РґР°С‚С‹
    async def get_schedule_exception(self, business_id: int, date: datetime) -> ScheduleExceptionModel | None:
        try:
            result = await self.session.execute(
                select(ScheduleExceptionModel)
                .where(ScheduleExceptionModel.business_id == business_id)
                .where(ScheduleExceptionModel.date == date.date())
            )
            return result.scalars().first()
        except Exception as e:
            logger.error("error_fetching_schedule_exception", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ РґР»СЏ Р±РёР·РЅРµСЃР° РІ РґРёР°РїР°Р·РѕРЅРµ РґР°С‚
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
            logger.error("error_fetching_schedule_exceptions_range", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РР·РјРЅРµРЅРёРµ СЃС‚Р°С‚СѓСЃР° Р·Р°РїРёСЃРё (РґР»СЏ Р°РґРјРёРЅРєРё)
    async def update_appointment_status(self, appointment: AppointmentModel, new_status: str) -> dict:
        try:
            appointment.status = new_status
            return {"message": "РЎС‚Р°С‚СѓСЃ Р·Р°РїРёСЃРё СѓСЃРїРµС€РЅРѕ РѕР±РЅРѕРІР»РµРЅ"}
        except Exception as e:
            logger.error("error_updating_appointment_status_repo", error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј РЅРµРѕС‚РјРµС‡РµРЅРЅС‹Рµ Р·Р°РїРёСЃРё (РїСЂРѕС€РµРґС€РёРµ СЃРѕ СЃС‚Р°С‚СѓСЃРѕРј scheduled)
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
            logger.error("error_fetching_unmarked_appointments_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЎРѕР·РґР°РµРј СЃРѕС‚СЂСѓРґРЅРёРєР°
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
            logger.error("error_creating_staff_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј СЃРѕС‚СЂСѓРґРЅРёРєР° РїРѕ id
    async def get_staff_by_id(self, business_id: int, staff_id: int) -> StaffModel:
        try:
            result = await self.session.execute(
                select(StaffModel)
                .where(StaffModel.id == staff_id)
                .where(StaffModel.business_id == business_id)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error("error_fetching_staff_by_id", business_id=business_id, staff_id=staff_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise

    # РЈРґР°Р»СЏРµРј СЃРѕС‚СЂСѓРґРЅРёРєР°
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
            logger.error("error_deleting_staff_repo", business_id=business_id, staff_id=staff_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЎРѕР·РґР°РµРј СѓСЃР»СѓРіСѓ
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
            logger.error("error_creating_service_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЈРґР°Р»СЏРµРј СѓСЃР»СѓРіСѓ
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
            logger.error("error_deleting_service_repo", business_id=business_id, service_id=service_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЎРѕР·РґР°РµРј СЃРІСЏР·СЊ СЃРѕС‚СЂСѓРґРЅРёРє-СѓСЃР»СѓРіР°
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
            logger.error("error_creating_staff_service_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј Р·Р°РїРёСЃСЊ РїРѕ ID РґР»СЏ РѕС‚РјРµРЅС‹ Р°РґРјРёРЅРѕРј
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
            logger.error("error_fetching_appointment_for_cancel", business_id=business_id, client_id=result.client_id, appointment_id=appointment_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЎРѕР·РґР°РµРј РёСЃРєР»СЋС‡РµРЅРёРµ РІ РіСЂР°С„РёРєРµ
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
            logger.error("error_creating_schedule_exception_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РџРѕР»СѓС‡Р°РµРј РІСЃРµ РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ РґР»СЏ Р±РёР·РЅРµСЃР°
    async def get_all_schedule_exceptions(self, business_id: int) -> list[ScheduleExceptionModel]:
        try:
            result = await self.session.execute(
                select(ScheduleExceptionModel)
                .where(ScheduleExceptionModel.business_id == business_id)
                .order_by(ScheduleExceptionModel.date)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("error_fetching_schedule_exceptions_repo", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise


    # РЈРґР°Р»СЏРµРј РёСЃРєР»СЋС‡РµРЅРёРµ РІ РіСЂР°С„РёРєРµ
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
            logger.error("error_deleting_schedule_exception_repo", business_id=business_id, exception_id=exception_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            raise








