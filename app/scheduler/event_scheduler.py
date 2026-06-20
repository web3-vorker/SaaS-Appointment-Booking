import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db.database import new_session
from app.models.business import BusinessModel
from app.redis.cache import delete_cache
from app.redis.cache_keys import key_business_by_api_key
from app.utils.logger import logger
from app.utils.datetime_utils import now_utc
from app.models.appointments import AppointmentModel
from app.models.events import EventModel
from app.config.config import config


def _event_payload_for_appointment(appointment: AppointmentModel) -> dict:
    return {
        "client_tg_id": appointment.client.tg_id,
        "text": (
            f"⏰ Напоминание: у вас запись на {appointment.start_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"Мастер: {appointment.staff.name if appointment.staff else 'не указан'}\n"
            f"Услуга: {appointment.service.name if appointment.service else 'не указана'}"
        ),
    }


async def create_appointment_reminder_events():
    """Создает события-напоминания для записей"""
    now = now_utc()
    # Используем конфиг для определения окна напоминаний
    reminder_minutes = config.reminder_minutes_before
    window_start = now + timedelta(minutes=reminder_minutes - 1)
    window_end = now + timedelta(minutes=reminder_minutes + 1)

    logger.debug(
        "scheduler_checking_reminders",
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
    )

    async with new_session() as session:
        result = await session.execute(
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.client), selectinload(AppointmentModel.staff))
            .where(AppointmentModel.status == "scheduled")
            .where(AppointmentModel.start_time >= window_start)
            .where(AppointmentModel.start_time <= window_end)
        )
        appointments = result.scalars().all()

        created_count = 0
        for appointment in appointments:
            existing = await session.execute(
                select(EventModel)
                .where(EventModel.type == "appointment_reminder")
                .where(EventModel.appointment_id == appointment.id)
            )
            if existing.scalars().first():
                continue

            payload = _event_payload_for_appointment(appointment)
            event = EventModel(
                type="appointment_reminder",
                business_id=appointment.business_id,
                appointment_id=appointment.id,
                payload=payload,
            )
            session.add(event)
            created_count += 1
            logger.info(
                "reminder_event_created",
                appointment_id=appointment.id,
                business_id=appointment.business_id,
                client_tg_id=appointment.client.tg_id,
                start_time=appointment.start_time.isoformat(),
            )

        await session.commit()
        
        if created_count > 0:
            logger.info(
                "reminders_batch_created",
                count=created_count,
                window_start=window_start.isoformat(),
            )


async def cleanup_old_events():
    """Удаляет старые отправленные события"""
    now = now_utc()
    # Используем конфиг для определения срока хранения событий
    cutoff_date = now - timedelta(days=config.event_cleanup_days)

    async with new_session() as session:
        result = await session.execute(
            delete(EventModel)
            .where(EventModel.created_at < cutoff_date)
            .where(EventModel.is_sent == True)
        )
        deleted_count = result.rowcount
        await session.commit()
        
        if deleted_count > 0:
            logger.info(
                "old_events_cleaned",
                count=deleted_count,
                cutoff_date=cutoff_date.isoformat(),
                retention_days=config.event_cleanup_days,
            )


async def deactivate_expired_subscriptions():
    """Деактивирует бизнесы с истёкшей подпиской"""
    now = now_utc()
    
    async with new_session() as session:
        result = await session.execute(
            select(BusinessModel)
            .where(BusinessModel.is_active == True)
            .where(BusinessModel.subscription_expires_at != None)
            .where(BusinessModel.subscription_expires_at <= now)
        )
        businesses = result.scalars().all()
        
        for business in businesses:
            business.is_active = False
            
            existing = await session.execute(
                select(EventModel)
                .where(EventModel.type == "subscription_expired")
                .where(EventModel.business_id == business.id)
                .where(EventModel.appointment_id == None)
            )
            if existing.scalars().first():
                continue
            
            # Создаём событие — бот владельца его получит и уведомит
            event = EventModel(
                type="subscription_expired",
                business_id=business.id,
                appointment_id=None,
                payload={
                    "owner_tg_id": business.owner_tg_id,
                    "business_name": business.name,
                    "expired_at": business.subscription_expires_at.isoformat(),
                    "subscription_plan": business.subscription_plan,
                }
            )
            session.add(event)
            
            # Инвалидируем кэш бизнеса
            try:
                await delete_cache(key_business_by_api_key(business.api_key))
            except Exception:
                pass
            
            logger.info(
                "subscription_expired_deactivated",
                business_id=business.id,
                business_name=business.name,
                expired_at=business.subscription_expires_at.isoformat()
            )
        
        await session.commit()


async def notify_expiring_subscriptions():
    """Уведомляет владельцев за N дней до истечения подписки"""
    now = now_utc()
    notify_before_days = config.notify_before_days 
    notify_window = now + timedelta(days=notify_before_days)
    
    async with new_session() as session:
        result = await session.execute(
            select(BusinessModel)
            .where(BusinessModel.is_active == True)
            .where(BusinessModel.subscription_expires_at != None)
            .where(BusinessModel.subscription_expires_at <= notify_window)
            .where(BusinessModel.subscription_expires_at > now)
            # Не уведомляли вообще ИЛИ уведомляли давно (> 24ч назад)
            .where(
                (BusinessModel.subscription_notified_at == None) |
                (BusinessModel.subscription_notified_at <= now - timedelta(hours=24))
            )
        )
        businesses = result.scalars().all()
        
        for business in businesses:
            days_left = (business.subscription_expires_at - now).days
            
            existing = await session.execute(
                select(EventModel)
                .where(EventModel.type == "subscription_expiring_soon")
                .where(EventModel.business_id == business.id)
                .where(EventModel.appointment_id == None)
                .where(EventModel.is_sent == False)
            )
            if existing.scalars().first():
                continue

            event = EventModel(
                type="subscription_expiring_soon",
                business_id=business.id,
                appointment_id=None,
                payload={
                    "owner_tg_id": business.owner_tg_id,
                    "business_name": business.name,
                    "expires_at": business.subscription_expires_at.isoformat(),
                    "subscription_plan": business.subscription_plan,
                    "days_left": days_left
                }
            )
            session.add(event)
            business.subscription_notified_at = now
            
            logger.info(
                "subscription_expiring_soon_notified",
                business_id=business.id,
                days_left=days_left
            )
        
        await session.commit()


async def event_scheduler_loop():
    logger.info("event_scheduler_started", interval_seconds=60)
    
    while True:
        try:
            await create_appointment_reminder_events()
            await cleanup_old_events()
            await deactivate_expired_subscriptions()
            await notify_expiring_subscriptions()
        except Exception as exc:
            logger.error(
                "event_scheduler_error",
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
        await asyncio.sleep(60)
