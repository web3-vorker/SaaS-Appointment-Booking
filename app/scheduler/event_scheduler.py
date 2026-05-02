import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import new_session
from app.utils.logger import logger
from app.models.appointments import AppointmentModel
from app.models.events import EventModel


def _event_payload_for_appointment(appointment: AppointmentModel) -> dict:
    return {
        "client_tg_id": appointment.client.tg_id,
        "text": (
            f"⏰ Напоминание: у вас запись на {appointment.start_time.strftime('%d.%m.%Y %H:%M')} "
            f"к {appointment.staff.name if appointment.staff else 'мастеру'}"
        ),
    }


async def create_appointment_reminder_events():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now + timedelta(minutes=59)
    window_end = now + timedelta(minutes=61)

    async with new_session() as session:
        result = await session.execute(
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.client), selectinload(AppointmentModel.staff))
            .where(AppointmentModel.status == "scheduled")
            .where(AppointmentModel.start_time >= window_start)
            .where(AppointmentModel.start_time <= window_end)
        )
        appointments = result.scalars().all()

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
            logger.info(f"Created reminder event for appointment={appointment.id}")

        await session.commit()


async def event_scheduler_loop():
    while True:
        try:
            await create_appointment_reminder_events()
        except Exception as exc:
            logger.error(f"Event scheduler error: {exc}")
        await asyncio.sleep(60)
