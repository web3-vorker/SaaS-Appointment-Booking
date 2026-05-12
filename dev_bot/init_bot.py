"""
Инициализация developer бота
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from dev_bot.config.config import dev_bot_config
from dev_bot.handlers import dev_handlers


def init_bot() -> tuple[Bot, Dispatcher]:
    """Инициализация бота и диспетчера"""
    
    # Создаем бота
    bot = Bot(token=dev_bot_config.telegram_bot_token)
    
    # Создаем диспетчер с хранилищем состояний
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутеры
    dp.include_router(dev_handlers.router)
    
    return bot, dp
