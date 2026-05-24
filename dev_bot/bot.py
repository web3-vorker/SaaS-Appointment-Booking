"""
Точка входа для developer бота
"""

import asyncio

from dev_bot.init_bot import init_bot
from dev_bot.utils.structured_logger import setup_bot_logging, get_logger
from dev_bot.config.config import dev_bot_config
from dev_bot.utils.error_monitor import ErrorMonitor


# Настройка структурированного логирования
setup_bot_logging(
    log_level=dev_bot_config.log_level,
    log_file_path=dev_bot_config.log_file_path,
    json_format=dev_bot_config.log_json_format,
)

logger = get_logger(__name__)

# Глобальная переменная для error monitor
error_monitor = None


async def main():
    """Главная функция запуска бота"""
    global error_monitor
    
    logger.info("dev_bot_startup", version="1.0.0")
    
    # Инициализируем бота и диспетчер
    bot, dp = init_bot()
    
    # Запускаем error monitor если включен
    if dev_bot_config.error_monitor_enabled:
        if dev_bot_config.developer_tg_id == 0:
            logger.warning("error_monitor_disabled_no_tg_id")
        else:
            try:
                # Получаем текущий event loop
                loop = asyncio.get_event_loop()
                
                error_monitor = ErrorMonitor(
                    log_file_path=dev_bot_config.error_log_path,
                    bot=bot,
                    developer_tg_id=dev_bot_config.developer_tg_id,
                    loop=loop,
                    rate_limit_window=dev_bot_config.alert_rate_limit_window,
                    max_alerts_per_window=dev_bot_config.alert_max_per_window,
                )
                error_monitor.start()
                logger.info(
                    "error_monitor_enabled",
                    log_path=dev_bot_config.error_log_path,
                    developer_tg_id=dev_bot_config.developer_tg_id,
                )
            except Exception as e:
                logger.error(
                    "error_monitor_start_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
    else:
        logger.info("error_monitor_disabled")
    
    try:
        # Запускаем polling
        logger.info("dev_bot_polling_started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error("dev_bot_error", error=str(e), exc_info=True)
        raise
    finally:
        # Останавливаем error monitor
        if error_monitor:
            error_monitor.stop()
        
        await bot.session.close()
        logger.info("dev_bot_stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("dev_bot_stopped_by_user")