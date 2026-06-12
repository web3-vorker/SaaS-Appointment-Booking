from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointments import AppointmentModel
from app.models.clients import ClientModel
from app.models.service import ServiceModel
from app.models.staffs import StaffModel
from app.models.business import BusinessModel
from app.schemas.appointment import AppointmentCreateSchema
from app.repository.repository import Repository
from app.utils.datetime_utils import now_utc
from app.utils.free_slots import get_free_slots
from app.utils.logger import logger
from app.redis.cache import get_cache, set_cache, delete_cache, cache_delete_pattern
from app.redis.cache_keys import TTL_APPOINTMENTS, TTL_FREE_DAYS, TTL_FREE_SLOTS, TTL_STAFFS, key_business_appointments, key_client_appointments, key_free_days, key_free_slots, key_services, TTL_SERVICES, key_staffs_for_service, pattern_all_free_days, pattern_all_slots


class Service:
  def __init__(self, session: AsyncSession, repository: Repository):
      self.session = session
      self.repository = repository


  # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ РґР»СЏ Р±РёР·РЅРµСЃР°
  async def get_business_staffs(self, business_id: int) -> list[dict]:
    try: 
      staffs = await self.repository.get_business_staffs(business_id)
      if not staffs:
        return []
      
      # РЎРµСЂРёР°Р»РёР·СѓРµРј СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ (РѕРїС‚РёРјРёР·РёСЂРѕРІР°РЅРѕ С‡РµСЂРµР· list comprehension)
      return [
        {
          "id": staff.id,
          "name": staff.name,
          "role": staff.role,
          "business_id": staff.business_id
        }
        for staff in staffs
      ]
    except Exception as e:
      logger.error(
          "error_fetching_business_staffs",
          business_id=business_id,
          error=str(e),
          error_type=type(e).__name__,
          exc_info=True,
      )
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РџРѕР»СѓС‡Р°РµРј РјР°СЃС‚РµСЂРѕРІ РґР»СЏ СѓСЃР»СѓРіРё
  async def get_service_staffs(self, business_id: int, service_id: int) -> list[dict]:
    try:
      # Проверяем кэш в Redis
      cached_staffs = await get_cache(key_staffs_for_service(business_id, service_id))

      if cached_staffs is not None:
        logger.info(f"Cache hit for service staffs, business_id: {business_id}, service_id: {service_id}")
        return cached_staffs

      staffs = await self.repository.get_service_staffs(business_id, service_id)
      if not staffs:
        return []
      
      # РЎРµСЂРёР°Р»РёР·СѓРµРј СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ
      result = []
      for staff in staffs:
        result.append({
          "id": staff.id,
          "name": staff.name,
          "role": staff.role,
          "business_id": staff.business_id
        })

      # Сохраняем результат в кэш Redis
      await set_cache(key_staffs_for_service(business_id, service_id), result, TTL_STAFFS)
      
      return result
    except Exception as e:
      logger.error(
          "error_fetching_service_staffs",
          business_id=business_id,
          service_id=service_id,
          error=str(e),
          error_type=type(e).__name__,
          exc_info=True,
      )
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РџРѕР»СѓС‡Р°РµРј Р·Р°РЅСЏС‚С‹Рµ СЃР»РѕС‚С‹ РґР»СЏ СЃРѕС‚СЂСѓРґРЅРёРєР° РІ Р·Р°РґР°РЅРЅС‹Р№ РґРµРЅСЊ
  async def get_busy_slots(self, business_id: int, staff_id: int, date: datetime) -> list[AppointmentModel]:
    try:
      appointments = await self.repository.get_busy_slots(business_id, staff_id, date)
      return appointments
    
    except Exception as e:
      logger.error(
          "error_fetching_busy_slots",
          business_id=business_id,
          staff_id=staff_id,
          date=date.isoformat(),
          error=str(e),
          error_type=type(e).__name__,
          exc_info=True,
      )
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РџРѕР»СѓС‡Р°РµРј СЃРІРѕР±РѕРґРЅС‹Рµ СЃР»РѕС‚С‹ РґР»СЏ СЃРѕС‚СЂСѓРґРЅРёРєР° РІ Р·Р°РґР°РЅРЅС‹Р№ РґРµРЅСЊ
  async def get_available_slots(self, business: BusinessModel, staff_id: int, service_id: int, date: str) -> list[dict]:
    try:
        # Проверяем кэш в Redis
        cached_slots = await get_cache(key_free_slots(business.id, staff_id, service_id, date))

        if cached_slots is not None:
            logger.info(f"Cache hit for free slots, business_id: {business.id}, staff_id: {staff_id}, service_id: {service_id}, date: {date}")
            return cached_slots
        
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        # РџРѕР»СѓС‡Р°РµРј РґР»РёС‚РµР»СЊРЅРѕСЃС‚СЊ СѓСЃР»СѓРіРё
        service_obj = await self.get_service_by_id(business.id, service_id)
        if not service_obj or service_obj["business_id"] != business.id:
            logger.warning(
                "service_not_found_available_slots",
                service_id=service_id,
                business_id=business.id,
            )
            raise HTTPException(status_code=404, detail="Service not found")
        
        duration_minutes = service_obj["duration_minutes"]
        
        # РџСЂРѕРІРµСЂСЏРµРј РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ РґР»СЏ СЌС‚РѕР№ РґР°С‚С‹
        schedule_exception = await self.repository.get_schedule_exception(business.id, date_obj)
        
        # Р•СЃР»Рё РґРµРЅСЊ РЅРµ СЂР°Р±РѕС‡РёР№ - РІРѕР·РІСЂР°С‰Р°РµРј РїСѓСЃС‚РѕР№ СЃРїРёСЃРѕРє
        if schedule_exception and not schedule_exception.is_working:
            return []
        
        # Если кэша нет, получаем данные из базы данных и считаем свободные слоты
        
        busy_slots = await self.get_busy_slots(business.id, staff_id, date_obj)
        
        free_slots = await get_free_slots(
            busy_slots, 
            date_obj, 
            duration_minutes=duration_minutes, 
            work_start=business.working_time_start, 
            work_end=business.working_time_end,
            business=business,
            schedule_exception=schedule_exception
        )

        # Сохраняем результат в кэш Redis
        await set_cache(key_free_slots(business.id, staff_id, service_id, date), free_slots, TTL_FREE_SLOTS)

        return free_slots
    except Exception as e:
        logger.error(
            "error_get_available_slots",
            business_id=business.id,
            staff_id=staff_id,
            service_id=service_id,
            date=date,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")

  # РџРѕР»СѓС‡Р°РµРј СЃРІРѕР±РѕРґРЅС‹Рµ РґРЅРё РґР»СЏ СЃРѕС‚СЂСѓРґРЅРёРєР° РЅР° РјРµСЃСЏС†
  async def get_free_days(self, business: BusinessModel, staff_id: int, service_id: int) -> list[dict]:
        # Проверяем кэш в Redis
        cached_free_days = await get_cache(key_free_days(business.id, staff_id, service_id))

        if cached_free_days is not None:
            logger.info(f"Cache hit for free days, business_id: {business.id}, staff_id: {staff_id}, service_id: {service_id}")
            return cached_free_days

        # РќР°С‡РёРЅР°РµРј СЃ СЃРµРіРѕРґРЅСЏС€РЅРµРіРѕ РґРЅСЏ (naive UTC)
        today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        free_days = []

        # РџРѕР»СѓС‡Р°РµРј РґР»РёС‚РµР»СЊРЅРѕСЃС‚СЊ СѓСЃР»СѓРіРё РѕРґРёРЅ СЂР°Р·
        service_obj = await self.get_service_by_id(business.id, service_id)
        if not service_obj or service_obj["business_id"] != business.id:
            logger.warning(
                "service_not_found_free_days",
                service_id=service_id,
                business_id=business.id,
            )
            raise HTTPException(status_code=404, detail="Service not found")
        
        duration_minutes = service_obj["duration_minutes"]
        
        # РџРѕР»СѓС‡Р°РµРј РІС‹С…РѕРґРЅС‹Рµ РґРЅРё Р±РёР·РЅРµСЃР°
        weekend_days = business.weekend_days or []
        
        # РџСЂРѕРІРµСЂСЏРµРј N РґРЅРµР№ РІРїРµСЂРµРґ (РёР· РєРѕРЅС„РёРіР°)
        from app.config.config import config
        end_date = today + timedelta(days=config.free_days_lookahead)
        
        # РџРѕР»СѓС‡Р°РµРј РІСЃРµ РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ РґР»СЏ СЌС‚РѕРіРѕ РґРёР°РїР°Р·РѕРЅР°
        schedule_exceptions = await self.repository.get_schedule_exceptions_range(business.id, today, end_date)
        exceptions_dict = {exc.date: exc for exc in schedule_exceptions}
        
        for i in range(config.free_days_lookahead):
            check_date = today + timedelta(days=i)
            
            # РџСЂРѕРІРµСЂСЏРµРј РґРµРЅСЊ РЅРµРґРµР»Рё (0=РџРЅ, 6=Р’СЃ)
            weekday = check_date.weekday()
            
            # РџСЂРѕРІРµСЂСЏРµРј РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ
            exception = exceptions_dict.get(check_date.date())
            
            # Р•СЃР»Рё РµСЃС‚СЊ РёСЃРєР»СЋС‡РµРЅРёРµ Рё РґРµРЅСЊ РЅРµ СЂР°Р±РѕС‡РёР№ - РїСЂРѕРїСѓСЃРєР°РµРј
            if exception and not exception.is_working:
                continue
            
            # Р•СЃР»Рё РЅРµС‚ РёСЃРєР»СЋС‡РµРЅРёСЏ, РЅРѕ РґРµРЅСЊ РІ СЃРїРёСЃРєРµ РІС‹С…РѕРґРЅС‹С… - РїСЂРѕРїСѓСЃРєР°РµРј
            if not exception and weekday in weekend_days:
                continue
            
            # РџРѕР»СѓС‡Р°РµРј Р·Р°РЅСЏС‚С‹Рµ СЃР»РѕС‚С‹
            busy_slots = await self.get_busy_slots(business.id, staff_id, check_date)
            
            # Р“РµРЅРµСЂРёСЂСѓРµРј СЃРІРѕР±РѕРґРЅС‹Рµ СЃР»РѕС‚С‹ СЃ СѓС‡РµС‚РѕРј РёСЃРєР»СЋС‡РµРЅРёР№
            free_slots = await get_free_slots(
                busy_slots, 
                check_date, 
                duration_minutes, 
                business.working_time_start, 
                business.working_time_end,
                business=business,
                schedule_exception=exception
            )
            
            # Р•СЃР»Рё РµСЃС‚СЊ С…РѕС‚СЏ Р±С‹ РѕРґРёРЅ СЃРІРѕР±РѕРґРЅС‹Р№ СЃР»РѕС‚, РґРѕР±Р°РІР»СЏРµРј РґРµРЅСЊ
            if free_slots:
                free_days.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "slots_count": len(free_slots)
                })

        # Сохраняем результат в кэш Redis
        await set_cache(key_free_days(business.id, staff_id, service_id), free_days, TTL_FREE_DAYS)

        return free_days


  # РџРѕР»СѓС‡Р°РµРј РІСЃРµ Р·Р°РїРёСЃРё РєР»РёРµРЅС‚Р°
  async def get_client_appointments(self, business_id: int, client_id: int) -> list[dict]:
    try: 
      # Проверям кэш в Redis
      cache_key = key_client_appointments(client_id, business_id)
      cached_client_appointments = await get_cache(cache_key)
      if cached_client_appointments is not None:
        logger.info(f"Cache hit for client appointments, client_id: {client_id}, business_id: {business_id}")
        return cached_client_appointments

      appointments = await self.repository.get_client_appointments(business_id, client_id)

      if not appointments:
        return []

      # РЎРµСЂРёР°Р»РёР·СѓРµРј Р·Р°РїРёСЃРё
      result = []
      for apt in appointments:
        result.append({
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        })

      # Добавляем результат в кэш Redis
      await set_cache(cache_key, result, TTL_APPOINTMENTS)
      
      return result
    
    except Exception as e:
      logger.error("error_fetching_client_appointments", business_id=business_id, client_id=client_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РџРѕР»СѓС‡Р°РµРј РІСЃРµ СѓСЃР»СѓРіРё Р±РёР·РЅРµСЃР°
  async def get_business_services(self, business_id: int) -> list[dict]:
    try:
      # Проверяем кэш в Redis
      cache_key = key_services(business_id)
      cached_services = await get_cache(cache_key)

      if cached_services is not None:
        logger.info(f"Cache hit for business services, business_id: {business_id}")
        return cached_services
      
      # Если кэша нет, получаем данные из базы данных
      services = await self.repository.get_business_services(business_id)

      if not services:
        return []

      # Сериализуем услуги, сохраняем в кэш Redis и возвращаем результат
      serialized_services = [
        {
          "id": service.id,
          "name": service.name,
          "price": service.price,
          "description": service.description,
          "duration_minutes": service.duration_minutes,
          "business_id": service.business_id
        }
        for service in services
      ]

      await set_cache(cache_key, serialized_services, TTL_SERVICES)

      return serialized_services
      
    except Exception as e:
      logger.error("error_fetching_business_services", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РџРѕР»СѓС‡Р°РµРј РІСЃРµ Р·Р°РїРёСЃРё Р±РёР·РЅРµСЃР°
  async def get_business_appointments(self, business_id: int) -> list[dict]:
    try:
      # Проверяем кэш в Redis
      cache_key = key_business_appointments(business_id)
      cached_appointments = await get_cache(cache_key)

      if cached_appointments is not None:
        logger.info(f"Cache hit for business appointments, business_id: {business_id}")
        return cached_appointments

      # Если кэша нет, получаем данные из базы данных
      appointments = await self.repository.get_business_appointments(business_id)

      if not appointments:
        return []

      # РЎРµСЂРёР°Р»РёР·СѓРµРј Р·Р°РїРёСЃРё (РѕРїС‚РёРјРёР·РёСЂРѕРІР°РЅРѕ С‡РµСЂРµР· list comprehension)
      serialized_appointments = [
        {
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        }
        for apt in appointments
      ]

      # Сохраняем результат в кэш Redis
      await set_cache(cache_key, serialized_appointments, TTL_APPOINTMENTS)

      return serialized_appointments
    except Exception as e:
      logger.error("error_fetching_business_appointments", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

    # РџРѕР»СѓС‡РµРЅРёРµ РёСЃС‚РѕСЂРёРё Р·Р°РїРёСЃРµР№ Р±РёР·РЅРµСЃР° (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def get_business_appointment_history(self, business_id: int) -> list[dict]:
    try:
      appointments = await self.repository.get_business_appointment_history(business_id)

      if not appointments:
        return []

      # РЎРµСЂРёР°Р»РёР·СѓРµРј Р·Р°РїРёСЃРё (РѕРїС‚РёРјРёР·РёСЂРѕРІР°РЅРѕ С‡РµСЂРµР· list comprehension)
      return [
        {
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        }
        for apt in appointments
      ]
    except Exception as e:
      logger.error("error_fetching_appointment_history", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РџРѕР»СѓС‡Р°РµРј СѓСЃР»СѓРіСѓ РїРѕ id
  async def get_service_by_id(self, business_id: int, service_id: int) -> dict:
    try: 
      service = await self.repository.get_service_by_id(business_id, service_id)

      if not service:
        return None

      # РЎРµСЂРёР°Р»РёР·СѓРµРј СѓСЃР»СѓРіСѓ
      return {
        "id": service.id,
        "business_id": service.business_id,
        "name": service.name,
        "price": service.price,
        "description": service.description,
        "duration_minutes": service.duration_minutes
      }
      
    except Exception as e:
      logger.error("error_fetching_business_services", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РџРѕР»СѓС‡Р°РµРј РѕР¶РёРґР°СЋС‰РёРµ РѕС‚РїСЂР°РІРєРё СЃРѕР±С‹С‚РёСЏ РґР»СЏ Р±РёР·РЅРµСЃР°
  async def get_pending_events(self, business_id: int) -> list[dict]:
    try:
      events = await self.repository.get_pending_events(business_id)
      if not events:
        return []
      
      # РЎРµСЂРёР°Р»РёР·СѓРµРј СЃРѕР±С‹С‚РёСЏ
      result = []
      for event in events:
        result.append({
          "id": event.id,
          "type": event.type,
          "business_id": event.business_id,
          "appointment_id": event.appointment_id,
          "payload": event.payload,
          "is_sent": event.is_sent,
          "created_at": event.created_at.isoformat() if event.created_at else None
        })
      
      return result
    except Exception as e:
      logger.error("error_fetching_pending_events", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РџРѕРјРµС‡Р°РµРј СЃРѕР±С‹С‚РёРµ РєР°Рє РѕС‚РїСЂР°РІР»РµРЅРЅРѕРµ
  async def mark_event_sent(self, business_id: int, event_id: int):
    try:
      event = await self.repository.mark_event_sent(event_id, business_id)
      if not event:
        logger.warning("event_not_found", event_id=event_id, business_id=business_id)
        raise HTTPException(status_code=404, detail="Event not found")
      await self.session.commit()
      return event
    except HTTPException as http_exc:
      raise http_exc
    except Exception as e:
      logger.error("error_marking_event_sent", event_id=event_id, business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЎРѕР·РґР°РµРј РЅРѕРІСѓСЋ Р·Р°РїРёСЃСЊ
  async def create_appointment(self, business_id: int, appointment_data: AppointmentCreateSchema) -> dict:
    try:
      # РџСЂРѕРІРµСЂРєР° РїСЂРёРЅР°РґР»РµР¶РЅРѕСЃС‚Рё РєР»РёРµРЅС‚Р° Рё СЃРѕС‚СЂСѓРґРЅРёРєР° Рє Р±РёР·РЅРµСЃСѓ
      client_and_staff_exists = await self.repository.client_and_staff_exists(business_id, appointment_data.client_id, appointment_data.staff_id)

      if not client_and_staff_exists:
        logger.warning("client_or_staff_not_belong", business_id=business_id, client_id=appointment_data.client_id, staff_id=appointment_data.staff_id)
        raise HTTPException(status_code=400, detail="Client or staff does not belong to this business")

      # РџСЂРѕРІРµСЂСЏРµРј, РЅРµС‚ Р»Рё РїРµСЂРµСЃРµС‡РµРЅРёР№ СЃ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРјРё Р·Р°РїРёСЃСЏРјРё РґР»СЏ СЌС‚РѕРіРѕ СЃРѕС‚СЂСѓРґРЅРёРєР°
      has_overlap = await self.repository.has_overlapping_appointments(business_id, appointment_data)
      if has_overlap:
        logger.warning(
            "appointment_overlap_detected",
            business_id=business_id,
            staff_id=appointment_data.staff_id,
            start_time=appointment_data.start_time.isoformat(),
            end_time=appointment_data.end_time.isoformat(),
        )
        raise HTTPException(status_code=400, detail="Appointment overlaps with existing booking")
          
      # Р•СЃР»Рё РІСЃРµ РїСЂРѕРІРµСЂРєРё РїСЂРѕР№РґРµРЅС‹, СЃРѕР·РґР°РµРј Р·Р°РїРёСЃСЊ
      new_appointment = AppointmentModel(
        business_id=business_id,
        client_id=appointment_data.client_id,
        client_name=appointment_data.client_name,
        staff_id=appointment_data.staff_id,
        service_id=appointment_data.service_id,
        start_time=appointment_data.start_time,
        end_time=appointment_data.end_time
      )

      await self.repository.add_appointment(new_appointment)
      
      # Flush РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ ID Р±РµР· commit
      await self.session.flush()
      
      # РџРѕР»СѓС‡Р°РµРј РґР°РЅРЅС‹Рµ РґР»СЏ СЃРѕР±С‹С‚РёСЏ
      business = await self.session.get(BusinessModel, business_id)
      client = await self.session.get(ClientModel, appointment_data.client_id)
      staff = await self.session.get(StaffModel, appointment_data.staff_id)
      service = await self.session.get(ServiceModel, appointment_data.service_id)

      # РЎРѕР·РґР°РµРј СЃРѕР±С‹С‚РёРµ РµСЃР»Рё РЅСѓР¶РЅРѕ (С‚РѕР»СЊРєРѕ РµСЃР»Рё РєР»РёРµРЅС‚ РЅРµ РІР»Р°РґРµР»РµС†)
      if business and business.owner_tg_id and client and client.tg_id != business.owner_tg_id:
        event_payload = {
            'owner_tg_id': business.owner_tg_id,
            'client_name': appointment_data.client_name,
            'service_name': service.name if service else 'N/A',
            'staff_name': staff.name if staff else 'N/A',
            'date': appointment_data.start_time.strftime('%d.%m.%Y'),
            'time': f"{appointment_data.start_time.strftime('%H:%M')} - {appointment_data.end_time.strftime('%H:%M')}",
            'appointment_id': new_appointment.id
        }
        
        await self.repository.create_event(
            event_type='new_appointment',
            business_id=business_id,
            appointment_id=new_appointment.id,
            payload=event_payload
        )

      # Сбрасываем кэш
      await cache_delete_pattern(pattern_all_slots(new_appointment.business_id))
      await cache_delete_pattern(pattern_all_free_days(new_appointment.business_id))
      await cache_delete_pattern(key_client_appointments(appointment_data.client_id, business_id))
      await cache_delete_pattern(key_business_appointments(business_id))

      # РћРґРёРЅ commit РґР»СЏ РІСЃРµР№ С‚СЂР°РЅР·Р°РєС†РёРё
      await self.session.commit()
      await self.session.refresh(new_appointment)
          
      logger.info(
          "appointment_created",
          appointment_id=new_appointment.id,
          business_id=business_id,
          client_id=appointment_data.client_id,
          staff_id=appointment_data.staff_id,
          service_id=appointment_data.service_id,
          start_time=new_appointment.start_time.isoformat(),
      )

      # Р’РѕР·РІСЂР°С‰Р°РµРј РґР°РЅРЅС‹Рµ СЃ РІР»РѕР¶РµРЅРЅС‹РјРё РѕР±СЉРµРєС‚Р°РјРё РґР»СЏ Р±РѕС‚Р°
      return {
          'id': new_appointment.id,
          'start_time': new_appointment.start_time.isoformat(),
          'end_time': new_appointment.end_time.isoformat(),
          'service': {
              'name': service.name if service else 'N/A',
              'price': service.price if service else 0
          },
          'staff': {
              'name': staff.name if staff else 'N/A'
          }
      }
    
    except HTTPException as http_exc:
      raise http_exc
    
    except Exception as e:
      logger.error(
          "appointment_creation_failed",
          business_id=business_id,
          error=str(e),
          error_type=type(e).__name__,
          exc_info=True,
      )
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РћС‚РјРµРЅР° Р·Р°РїРёСЃСЊ
  async def cancelled_appointment(self, business_id: int, client_id: int, appointment_id: int, cancelled_by_admin: bool = False) -> dict:
    try:
      # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ Р·Р°РїРёСЃСЊ РїСЂРёРЅР°РґР»РµР¶РёС‚ СЌС‚РѕРјСѓ Р±РёР·РЅРµСЃСѓ Рё РєР»РёРµРЅС‚Сѓ
      appointment = await self.repository.get_appointment_by_id(business_id, client_id, appointment_id)

      if not appointment:
        logger.warning(
            "appointment_cancellation_failed_not_found",
            appointment_id=appointment_id,
            client_id=client_id,
            business_id=business_id,
        )
        raise HTTPException(status_code=404, detail="Appointment not found")

      # РЎРѕС…СЂР°РЅСЏРµРј РґР°РЅРЅС‹Рµ Р”Рћ СѓРґР°Р»РµРЅРёСЏ (СЃРІСЏР·Рё СѓР¶Рµ Р·Р°РіСЂСѓР¶РµРЅС‹ С‡РµСЂРµР· selectinload РІ repository)
      business = await self.session.get(BusinessModel, business_id)
      client = await self.session.get(ClientModel, client_id)
      
      # РР·РІР»РµРєР°РµРј РґР°РЅРЅС‹Рµ РёР· СѓР¶Рµ Р·Р°РіСЂСѓР¶РµРЅРЅС‹С… СЃРІСЏР·РµР№
      staff_name = appointment.staff.name if appointment.staff else 'N/A'
      service_name = appointment.service.name if appointment.service else 'N/A'
      client_name = appointment.client_name
      start_time = appointment.start_time
      end_time = appointment.end_time

      response = await self.repository.cancelled_appointment(appointment)
      
      logger.info(
          "appointment_cancelled",
          appointment_id=appointment_id,
          business_id=business_id,
          client_id=client_id,
          cancelled_by="admin" if cancelled_by_admin else "client",
          start_time=start_time.isoformat(),
      )
      
      # Р›РѕРіРёРєР° СЃРѕР·РґР°РЅРёСЏ СЃРѕР±С‹С‚РёР№ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ С‚РѕРіРѕ, РєС‚Рѕ РѕС‚РјРµРЅСЏРµС‚
      if business and business.owner_tg_id and client:
        # Р•СЃР»Рё РєР»РёРµРЅС‚ = РІР»Р°РґРµР»РµС†, СЃРѕР±С‹С‚РёСЏ РЅРµ СЃРѕР·РґР°РµРј
        if client.tg_id == business.owner_tg_id:
          pass  # Skip event creation
        else:
          # Р•СЃР»Рё РѕС‚РјРµРЅСЏРµС‚ Р°РґРјРёРЅ - СѓРІРµРґРѕРјР»СЏРµРј РєР»РёРµРЅС‚Р°
          if cancelled_by_admin:
            event_payload = {
              'client_tg_id': client.tg_id,
              'client_name': client_name,
              'service_name': service_name,
              'staff_name': staff_name,
              'date': start_time.strftime('%d.%m.%Y'),
              'time': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            }
            
            await self.repository.create_event(
              event_type='cancelled_appointment_by_admin',
              business_id=business_id,
              appointment_id=appointment_id,
              payload=event_payload
            )
          # Р•СЃР»Рё РѕС‚РјРµРЅСЏРµС‚ РєР»РёРµРЅС‚ - СѓРІРµРґРѕРјР»СЏРµРј РІР»Р°РґРµР»СЊС†Р°
          else:
            event_payload = {
              'owner_tg_id': business.owner_tg_id,
              'client_name': client_name,
              'service_name': service_name,
              'staff_name': staff_name,
              'date': start_time.strftime('%d.%m.%Y'),
              'time': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            }
            
            await self.repository.create_event(
              event_type='cancelled_appointment_by_client',
              business_id=business_id,
              appointment_id=appointment_id,
              payload=event_payload
            )
            
            logger.info("event_created", event_type="cancelled_appointment_by_client", appointment_id=appointment_id, business_id=business_id)
      
      await self.session.commit()

      # Сбрасываем кэш
      await cache_delete_pattern(pattern_all_slots(business_id))
      await cache_delete_pattern(pattern_all_free_days(business_id))
      await cache_delete_pattern(key_client_appointments(client_id, business_id))
      await cache_delete_pattern(key_business_appointments(business_id))

      return response

    except HTTPException as http_exc:
      raise http_exc
    
    except Exception as e:
      logger.error(
          "appointment_cancellation_failed",
          appointment_id=appointment_id,
          business_id=business_id,
          client_id=client_id,
          error=str(e),
          error_type=type(e).__name__,
          exc_info=True,
      )
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # РР·РјРµРЅРµРЅРёРµ СЃС‚Р°С‚СѓСЃР° Р·Р°РїРёСЃРё РґР»СЏ Р°РґРјРёРЅРєРё
  async def update_appointment_status(self, business_id: int, client_id: int, appointment_id: int, new_status: str) -> dict:
    try:
      # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ Р·Р°РїРёСЃСЊ РїСЂРёРЅР°РґР»РµР¶РёС‚ СЌС‚РѕРјСѓ Р±РёР·РЅРµСЃСѓ Рё РєР»РёРµРЅС‚Сѓ
        appointment = await self.repository.get_appointment_by_id(business_id, client_id, appointment_id)
        if not appointment:
          logger.warning(
            "appointment_status_update_failed_not_found",
            appointment_id=appointment_id,
            client_id=client_id,
            business_id=business_id,
          )
          raise HTTPException(status_code=404, detail="Appointment not found")

        # Сохраняем старый статус перед изменением
        old_status = appointment.status

        result = await self.repository.update_appointment_status(appointment, new_status)

        # Один commit для всей транзакции
        await self.session.commit()

        logger.info(
          "appointment_status_updated",
          appointment_id=appointment_id,
          business_id=business_id,
          old_status=old_status,
          new_status=new_status,
        )
        await self.session.refresh(appointment)

        # Инвалидация кэша при изменении статуса (слоты и свободные дни)
        try:
          if old_status != new_status:
            await cache_delete_pattern(pattern_all_slots(business_id))
            await cache_delete_pattern(pattern_all_free_days(business_id))
        except Exception:
          pass

        return result

    except HTTPException as http_exc:
      raise http_exc
    except Exception as e:
      logger.error("error_updating_appointment_status", appointment_id=appointment_id, business_id=business_id, new_status=new_status, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")     


  # РџРѕР»СѓС‡РµРЅРёРµ РёР»Рё СЃРѕР·РґР°РЅРёРµ РєР»РёРµРЅС‚Р°
  async def get_or_create_client(self, business_id: int, tg_id: int, client_name: str, phone: str = None) -> dict:
    try:
      result = await self.repository.get_or_create_client(business_id, tg_id, client_name, phone)
      
      # Repository СѓР¶Рµ РІРѕР·РІСЂР°С‰Р°РµС‚ СЃР»РѕРІР°СЂСЊ СЃ client Рё is_owner
      client = result["client"]
      is_owner = result["is_owner"]
      updated = result.get("updated", False)
      
      # Р’РђР–РќРћ: Р’СЃРµРіРґР° РєРѕРјРјРёС‚РёРј, С‡С‚РѕР±С‹ РєР»РёРµРЅС‚ Р±С‹Р» РґРѕСЃС‚СѓРїРµРЅ РґР»СЏ РґСЂСѓРіРёС… Р·Р°РїСЂРѕСЃРѕРІ
      await self.session.commit()
      await self.session.refresh(client)
      
      return {
          "client": {
              "id": client.id,
              "name": client.name,
              "tg_id": client.tg_id,
              "phone": client.phone,
              "business_id": client.business_id,
              "created_at": client.created_at.isoformat() if client.created_at else None
          },
          "is_owner": is_owner
      }
    except HTTPException as http_exc:
      raise http_exc
    except Exception as e:
      logger.error("error_get_or_create_client", business_id=business_id, tg_id=tg_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РџРѕР»СѓС‡Р°РµРј Р±РёР·РЅРµСЃ РїРѕ API Key
  async def get_business_by_api_key(self, api_key: str) -> BusinessModel | None:
    try:
      return await self.repository.get_business_by_api_key(api_key)
    except Exception as e:
      logger.error("error_get_business_by_api_key", error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получение бизнеса по токену бота
  async def get_business_by_bot_token(self, bot_token: str) -> BusinessModel | None:
    try:
      return await self.repository.get_business_by_bot_token(bot_token)
    except Exception as e:
      logger.error("error_get_business_by_bot_token", error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РџРѕР»СѓС‡Р°РµРј РЅРµРѕС‚РјРµС‡РµРЅРЅС‹Рµ Р·Р°РїРёСЃРё
  async def get_unmarked_appointments(self, business_id: int) -> list[dict]:
    try:
      appointments = await self.repository.get_unmarked_appointments(business_id)
      
      if not appointments:
        return []

      # РЎРµСЂРёР°Р»РёР·СѓРµРј Р·Р°РїРёСЃРё (РѕРїС‚РёРјРёР·РёСЂРѕРІР°РЅРѕ С‡РµСЂРµР· list comprehension)
      return [
        {
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        }
        for apt in appointments
      ]
    except Exception as e:
      logger.error("error_fetching_unmarked_appointments", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЎРѕР·РґР°РµРј СЃРѕС‚СЂСѓРґРЅРёРєР° (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def create_staff_admin(self, business_id: int, name: str, role: str) -> dict:
    try:
      new_staff = await self.repository.create_staff(business_id, name, role)
      await self.session.commit()
      await self.session.refresh(new_staff)
      # Инвалидация кэша staff-for-service для бизнеса (на случай, если фронт кешировал список сотрудников)
      try:
        await cache_delete_pattern(f"cache:staffs:business_id:{business_id}:*")
      except Exception:
        pass
      
      return {
        "id": new_staff.id,
        "name": new_staff.name,
        "business_id": new_staff.business_id,
        "role": new_staff.role
      }
    
    except Exception as e:
      logger.error("error_creating_staff", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЈРґР°Р»СЏРµРј СЃРѕС‚СЂСѓРґРЅРёРєР° (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def delete_staff_admin(self, business_id: int, staff_id: int) -> dict:
    try:
      staff = await self.repository.delete_staff(business_id, staff_id)
      if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
      # Сбрасываем кэш: слоты и свободные дни, а также кэш staff-for-service
      try:
        await cache_delete_pattern(pattern_all_slots(business_id))
        await cache_delete_pattern(pattern_all_free_days(business_id))
        await cache_delete_pattern(f"cache:staffs:business_id:{business_id}:*")
      except Exception:
        pass

      await self.session.commit()
      return {"detail": "Staff deleted successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error("error_deleting_staff", business_id=business_id, staff_id=staff_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЎРѕР·РґР°РµРј СѓСЃР»СѓРіСѓ (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def create_service_admin(self, business_id: int, name: str, price: int, description: str, duration_minutes: int) -> dict:
    try:
      new_service = await self.repository.create_service(business_id, name, price, description, duration_minutes)

      # Сбрасываем кэш
      try:
        await delete_cache(key_services(business_id))
        await cache_delete_pattern(pattern_all_slots(business_id))
        await cache_delete_pattern(pattern_all_free_days(business_id))
      except Exception:
        pass

      await self.session.commit()
      await self.session.refresh(new_service)
      
      return {
        "id": new_service.id,
        "name": new_service.name,
        "business_id": new_service.business_id,
        "price": new_service.price,
        "description": new_service.description,
        "duration_minutes": new_service.duration_minutes
      }
    except Exception as e:
      logger.error("error_creating_service", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЈРґР°Р»СЏРµРј СѓСЃР»СѓРіСѓ (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def delete_service_admin(self, business_id: int, service_id: int) -> dict:
    try:
      service = await self.repository.delete_service(business_id, service_id)
      if not service:
        raise HTTPException(status_code=404, detail="Service not found")
      
      # Сбрасываем кэш
      try:
        await delete_cache(key_services(business_id))
        # удаляем кэш staff-for-service для этого сервиса
        await delete_cache(key_staffs_for_service(business_id, service_id))
        await cache_delete_pattern(pattern_all_slots(business_id))
        await cache_delete_pattern(pattern_all_free_days(business_id))
      except Exception:
        pass

      await self.session.commit()
      return {"detail": "Service deleted successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error("error_deleting_service", business_id=business_id, service_id=service_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЎРѕР·РґР°РµРј СЃРІСЏР·СЊ СЃРѕС‚СЂСѓРґРЅРёРє-СѓСЃР»СѓРіР° (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def create_staff_service_admin(self, business_id: int, staff_id: int, service_id: int) -> dict:
    try:
      # РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІРѕРІР°РЅРёРµ СЃРѕС‚СЂСѓРґРЅРёРєР°
      staff = await self.repository.get_staff_by_id(business_id, staff_id)
      if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
      
      # РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІРѕРІР°РЅРёРµ СѓСЃР»СѓРіРё
      service = await self.repository.get_service_by_id(business_id, service_id)
      if not service:
        raise HTTPException(status_code=404, detail="Service not found")
      
      new_staff_service = await self.repository.create_staff_service(business_id, staff_id, service_id)

      # Сбрасываем кэш
      try:
        await delete_cache(key_staffs_for_service(business_id, service_id))
        await cache_delete_pattern(pattern_all_slots(business_id))
        await cache_delete_pattern(pattern_all_free_days(business_id))
      except Exception:
        pass

      await self.session.commit()
      await self.session.refresh(new_staff_service)
      
      return {
        "id": new_staff_service.id,
        "staff_id": new_staff_service.staff_id,
        "service_id": new_staff_service.service_id,
        "business_id": new_staff_service.business_id
      }
    except HTTPException:
      raise
    except Exception as e:
      logger.error("error_creating_staff_service", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РћС‚РјРµРЅСЏРµРј Р·Р°РїРёСЃСЊ С‡РµСЂРµР· Р°РґРјРёРЅРєСѓ
  async def cancel_appointment_admin(self, business_id: int, appointment_id: int) -> dict:
    try:
      appointment = await self.repository.get_appointment_for_cancel(business_id, appointment_id)
      if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
      
      # РСЃРїРѕР»СЊР·СѓРµРј СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёР№ РјРµС‚РѕРґ РѕС‚РјРµРЅС‹ СЃ С„Р»Р°РіРѕРј cancelled_by_admin
      await self.cancelled_appointment(business_id, appointment.client_id, appointment_id, cancelled_by_admin=True)

      # Сбрасываем кэш
      await cache_delete_pattern(pattern_all_slots(business_id))
      await cache_delete_pattern(pattern_all_free_days(business_id))
      await cache_delete_pattern(key_client_appointments(appointment.client_id, business_id))
      await cache_delete_pattern(key_business_appointments(business_id))

      return {"message": "Appointment cancelled by admin successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error("error_cancelling_appointment_admin", business_id=business_id, appointment_id=appointment_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЎРѕР·РґР°РµРј РёСЃРєР»СЋС‡РµРЅРёРµ РІ РіСЂР°С„РёРєРµ (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def create_schedule_exception_admin(self, business_id: int, date: str, is_working: bool, custom_start: str = None, custom_end: str = None) -> dict:
    try:
      exc = await self.repository.create_schedule_exception(business_id, date, is_working, custom_start, custom_end)

      # Сбрасываем кэш
      await cache_delete_pattern(pattern_all_slots(business_id))
      await cache_delete_pattern(pattern_all_free_days(business_id))

      await self.session.commit()
      await self.session.refresh(exc)
      
      return {
        "message": "Exception created",
        "id": exc.id,
        "date": exc.date.strftime("%Y-%m-%d"),
        "is_working": exc.is_working,
        "custom_start_time": exc.custom_start_time.strftime("%H:%M") if exc.custom_start_time else None,
        "custom_end_time": exc.custom_end_time.strftime("%H:%M") if exc.custom_end_time else None
      }
    except Exception as e:
      logger.error("error_creating_schedule_exception", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РџРѕР»СѓС‡Р°РµРј РІСЃРµ РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def get_schedule_exceptions_admin(self, business_id: int) -> list[dict]:
    try:
      exceptions = await self.repository.get_all_schedule_exceptions(business_id)
      
      return [
        {
          "id": exc.id,
          "date": exc.date.strftime("%Y-%m-%d"),
          "is_working": exc.is_working,
          "custom_start_time": exc.custom_start_time.strftime("%H:%M") if exc.custom_start_time else None,
          "custom_end_time": exc.custom_end_time.strftime("%H:%M") if exc.custom_end_time else None
        }
        for exc in exceptions
      ]
    except Exception as e:
      logger.error("error_fetching_schedule_exceptions", business_id=business_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # РЈРґР°Р»СЏРµРј РёСЃРєР»СЋС‡РµРЅРёРµ РІ РіСЂР°С„РёРєРµ (РґР»СЏ Р°РґРјРёРЅРєРё)
  async def delete_schedule_exception_admin(self, business_id: int, exception_id: int) -> dict:
    try:
      exception = await self.repository.delete_schedule_exception(business_id, exception_id)
      if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
      
      await self.session.commit()
      return {"message": "Exception deleted successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error("error_deleting_schedule_exception", business_id=business_id, exception_id=exception_id, error=str(e), error_type=type(e).__name__, exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
