import os
import asyncio
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from app.utils.logger import logger


class NotificationService:
    def __init__(self, token: str | None = None, proxy: str | None = None, retries: int = 3, delay: int = 5):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.proxy = proxy or os.getenv("TELEGRAM_PROXY")
        self.retries = retries
        self.delay = delay

    async def send_new_appointment_notification(self, owner_tg_id: int, appointment_details: dict):
        """Уведомление о новой записи"""
        message = (
            f"🆕 <b>Новая запись!</b>\n\n"
            f"👤 Клиент: {appointment_details.get('client_name', 'N/A')}\n"
            f"✂️ Услуга: {appointment_details.get('service_name', 'N/A')}\n"
            f"👨‍💼 Сотрудник: {appointment_details.get('staff_name', 'N/A')}\n"
            f"📅 Дата: {appointment_details.get('date', 'N/A')}\n"
            f"⏰ Время: {appointment_details.get('time', 'N/A')}\n"
            f"🆔 ID записи: {appointment_details.get('appointment_id', 'N/A')}"
        )
        await self._send(owner_tg_id, message)

    async def send_cancelled_appointment_notification(self, owner_tg_id: int, appointment_details: dict):
        """Уведомление об отмене записи"""
        message = (
            f"❌ <b>Запись отменена!</b>\n\n"
            f"👤 Клиент: {appointment_details.get('client_name', 'N/A')}\n"
            f"✂️ Услуга: {appointment_details.get('service_name', 'N/A')}\n"
            f"📅 Дата: {appointment_details.get('date', 'N/A')}\n"
            f"⏰ Время: {appointment_details.get('time', 'N/A')}"
        )
        await self._send(owner_tg_id, message)

    async def _send(self, chat_id: int, message: str):
        """Внутренний метод отправки с retry"""
        session = AiohttpSession(proxy=self.proxy) if self.proxy else AiohttpSession()
        async with Bot(token=self.token, session=session) as bot:
            last_error = None
            for attempt in range(1, self.retries + 1):
                try:
                    await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
                    logger.info(f"Notification sent to {chat_id}")
                    return
                except Exception as exc:
                    last_error = exc
                    logger.warning(f"Notification attempt {attempt}/{self.retries} failed for {chat_id}: {exc}")
                    if attempt < self.retries:
                        await asyncio.sleep(self.delay)
            logger.error(f"Notification failed after {self.retries} attempts for {chat_id}: {last_error}")
