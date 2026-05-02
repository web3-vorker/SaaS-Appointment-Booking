import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.db.database import new_session
from app.utils.logger import logger
from app.models.appointments import AppointmentModel
from app.models.business import BusinessModel
from app.models.clients import ClientModel
from app.models.service import ServiceModel
from app.models.staffs import StaffModel


async def _send_with_retry(bot, chat_id: int, text: str, parse_mode: str = "HTML", retries: int = 3, delay: int = 5):
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return
        except Exception as exc:
            last_exception = exc
            logger.warning(f"Telegram send attempt {attempt}/{retries} failed for {chat_id}: {exc}")
            if attempt < retries:
                await asyncio.sleep(delay)
    logger.error(f"Telegram send failed after {retries} attempts for {chat_id}: {last_exception}")
    raise last_exception


async def send_remind_for_business(bot):
    """Отправляет напоминания владельцу бизнеса за час до записи."""
    while True:
        async with new_session() as session:
            now = datetime.now(timezone.utc)
            now_naive = now.replace(tzinfo=None)
            hour_later = (now + timedelta(hours=1)).replace(tzinfo=None)

            result = await session.execute(
                select(AppointmentModel)
                .where(AppointmentModel.start_time <= hour_later)
                .where(AppointmentModel.start_time > now_naive)
                .where(AppointmentModel.status == "scheduled")
            )
            appointments = result.scalars().all()

            for apt in appointments:
                business = await session.get(BusinessModel, apt.business_id)
                client = await session.get(ClientModel, apt.client_id)
                staff = await session.get(StaffModel, apt.staff_id)

                if business and business.owner_tg_id:
                    text = (
                        f"⏰ Напоминание: через час запись к {staff.name if staff else 'мастеру'} "
                        f"у клиента {client.name if client else apt.client_id}"
                    )
                    try:
                        await _send_with_retry(bot, business.owner_tg_id, text)
                    except Exception:
                        logger.error(f"Failed to send business reminder for appointment {apt.id}")

        await asyncio.sleep(60)


async def send_remind_for_client(bot):
    """Отправляет напоминания клиентам за час до записи."""
    while True:
        async with new_session() as session:
            now = datetime.now(timezone.utc)
            now_naive = now.replace(tzinfo=None)
            hour_later = (now + timedelta(hours=1)).replace(tzinfo=None)

            result = await session.execute(
                select(AppointmentModel)
                .where(AppointmentModel.start_time <= hour_later)
                .where(AppointmentModel.start_time > now_naive)
                .where(AppointmentModel.status == "scheduled")
            )
            appointments = result.scalars().all()

            for apt in appointments:
                client = await session.get(ClientModel, apt.client_id)
                staff = await session.get(StaffModel, apt.staff_id)
                service = await session.get(ServiceModel, apt.service_id)

                if client and client.tg_id:
                    message = (
                        f"⏰ <b>Напоминание о записи!</b>\n\n"
                        f"✂️ Услуга: {service.name if service else 'Не указана'}\n"
                        f"👨‍💼 Мастер: {staff.name if staff else 'Не указан'}\n"
                        f"📅 Дата: {apt.start_time.strftime('%d.%m.%Y')}\n"
                        f"⏰ Время: {apt.start_time.strftime('%H:%M')} - {apt.end_time.strftime('%H:%M')}\n\n"
                        f"📍 Не опоздайте! Если нужно отменить или перенести запись, используйте команду /my_appointments"
                    )
                    try:
                        await _send_with_retry(bot, client.tg_id, message)
                    except Exception:
                        logger.error(f"Failed to send client reminder for appointment {apt.id}")

        await asyncio.sleep(60)


async def start_scheduler(bot):
    await asyncio.gather(
        send_remind_for_business(bot),
        send_remind_for_client(bot),
    )
