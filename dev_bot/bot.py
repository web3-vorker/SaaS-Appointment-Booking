"""
Точка входа для developer бота
"""

import asyncio
import logging

from dev_bot.init_bot import init_bot


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    logger.info("Starting Developer Bot...")
    
    # Инициализируем бота и диспетчер
    bot, dp = init_bot()
    
    try:
        # Запускаем polling
        logger.info("Developer Bot is running!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Developer Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Developer Bot stopped by user.")


# Придумай название для этого бота в тг, в конце должно быть Bot или _bot, и оно должно быть уникальным, не должно быть уже существующим в тг. Название должно отражать его предназначение - бот для разработчика, через который он подключает бизнесы к SaaS платформе.
# Предложение: DevConnectBot