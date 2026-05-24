"""
Мониторинг error.log и отправка алертов в Telegram
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Set
from collections import defaultdict

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from dev_bot.utils.structured_logger import get_logger

logger = get_logger(__name__)


class ErrorAlertManager:
    """Управление алертами с группировкой и rate limiting"""
    
    def __init__(self, rate_limit_window: int = 60, max_alerts_per_window: int = 10):
        self.rate_limit_window = rate_limit_window  # секунды
        self.max_alerts_per_window = max_alerts_per_window
        self.alert_history: dict[str, list[datetime]] = defaultdict(list)
        self.ignored_errors: Set[str] = set()
        
    def should_alert(self, error_signature: str) -> bool:
        """Проверяет, нужно ли отправлять алерт"""
        
        # Проверка игнор-листа
        if error_signature in self.ignored_errors:
            return False
        
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.rate_limit_window)
        
        # Очищаем старые записи
        self.alert_history[error_signature] = [
            ts for ts in self.alert_history[error_signature]
            if ts > cutoff_time
        ]
        
        # Проверяем rate limit
        if len(self.alert_history[error_signature]) >= self.max_alerts_per_window:
            return False
        
        # Добавляем новый алерт
        self.alert_history[error_signature].append(now)
        return True
    
    def ignore_error(self, error_signature: str):
        """Добавить ошибку в игнор-лист"""
        self.ignored_errors.add(error_signature)
        logger.info("error_ignored", signature=error_signature)


class ErrorLogHandler(FileSystemEventHandler):
    """Обработчик изменений в error.log"""
    
    def __init__(self, log_file_path: Path, bot, developer_tg_id: int, alert_manager: ErrorAlertManager, loop):
        self.log_file_path = log_file_path
        self.bot = bot
        self.developer_tg_id = developer_tg_id
        self.alert_manager = alert_manager
        self.last_position = 0
        self.loop = loop  # Сохраняем event loop
        
        # Инициализируем позицию в конце файла (не читаем старые ошибки)
        if self.log_file_path.exists():
            self.last_position = self.log_file_path.stat().st_size
    
    def on_modified(self, event):
        """Вызывается при изменении файла"""
        if not isinstance(event, FileModifiedEvent):
            return
        
        if Path(event.src_path) != self.log_file_path:
            return
        
        # Читаем новые строки в правильном event loop
        asyncio.run_coroutine_threadsafe(self._process_new_lines(), self.loop)
    
    async def _process_new_lines(self):
        """Обрабатывает новые строки в логе"""
        try:
            if not self.log_file_path.exists():
                return
            
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
            
            for line in new_lines:
                await self._process_log_line(line.strip())
                
        except Exception as e:
            logger.error(
                "error_processing_log_lines",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
    
    async def _process_log_line(self, line: str):
        """Обрабатывает одну строку лога"""
        if not line:
            return
        
        try:
            log_entry = json.loads(line)
            
            # Проверяем, что это ошибка
            if log_entry.get('level') not in ['error', 'critical']:
                return
            
            # Создаем сигнатуру ошибки для группировки
            error_signature = f"{log_entry.get('event', 'unknown')}:{log_entry.get('error_type', 'unknown')}"
            
            # Проверяем rate limiting
            if not self.alert_manager.should_alert(error_signature):
                logger.debug("alert_rate_limited", signature=error_signature)
                return
            
            # Отправляем алерт
            await self._send_alert(log_entry)
            
        except json.JSONDecodeError:
            # Не JSON строка, игнорируем
            pass
        except Exception as e:
            logger.error(
                "error_processing_log_entry",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
    
    async def _send_alert(self, log_entry: dict):
        """Отправляет алерт в Telegram"""
        try:
            # Форматируем сообщение
            message = self._format_alert_message(log_entry)
            
            # Отправляем в Telegram
            await self.bot.send_message(
                chat_id=self.developer_tg_id,
                text=message,
                parse_mode="HTML",
            )
            
            logger.info(
                "alert_sent",
                error_event=log_entry.get('event'),
                error_type=log_entry.get('error_type'),
            )
            
        except Exception as e:
            logger.error(
                "error_sending_alert",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
    
    def _format_alert_message(self, log_entry: dict) -> str:
        """Форматирует сообщение алерта"""
        
        # Эмодзи в зависимости от уровня
        emoji = "🚨" if log_entry.get('level') == 'critical' else "⚠️"
        
        # Базовая информация
        event = log_entry.get('event', 'unknown_error')
        timestamp = log_entry.get('timestamp', 'N/A')
        error_msg = log_entry.get('error', 'No error message')
        error_type = log_entry.get('error_type', 'Unknown')
        
        message = f"{emoji} <b>ОШИБКА В BACKEND</b>\n\n"
        message += f"<b>Событие:</b> <code>{event}</code>\n"
        message += f"<b>Время:</b> {timestamp}\n"
        
        # Дополнительный контекст
        if 'business_id' in log_entry:
            message += f"<b>Бизнес ID:</b> #{log_entry['business_id']}\n"
        
        if 'client_id' in log_entry:
            message += f"<b>Клиент ID:</b> #{log_entry['client_id']}\n"
        
        if 'appointment_id' in log_entry:
            message += f"<b>Запись ID:</b> #{log_entry['appointment_id']}\n"
        
        if 'request_id' in log_entry:
            message += f"<b>Request ID:</b> <code>{log_entry['request_id'][:8]}...</code>\n"
        
        if 'path' in log_entry:
            message += f"<b>Endpoint:</b> <code>{log_entry['path']}</code>\n"
        
        message += f"\n<b>Ошибка:</b> {error_msg}\n"
        message += f"<b>Тип:</b> <code>{error_type}</code>\n"
        
        return message


class ErrorMonitor:
    """Главный класс для мониторинга ошибок"""
    
    def __init__(
        self,
        log_file_path: str,
        bot,
        developer_tg_id: int,
        loop,
        rate_limit_window: int = 60,
        max_alerts_per_window: int = 10,
    ):
        self.log_file_path = Path(log_file_path)
        self.bot = bot
        self.developer_tg_id = developer_tg_id
        self.loop = loop
        
        # Создаем менеджер алертов
        self.alert_manager = ErrorAlertManager(
            rate_limit_window=rate_limit_window,
            max_alerts_per_window=max_alerts_per_window,
        )
        
        # Создаем обработчик файлов
        self.event_handler = ErrorLogHandler(
            log_file_path=self.log_file_path,
            bot=self.bot,
            developer_tg_id=self.developer_tg_id,
            alert_manager=self.alert_manager,
            loop=self.loop,
        )
        
        # Создаем observer
        self.observer = Observer()
        
    def start(self):
        """Запускает мониторинг"""
        try:
            # Проверяем, что файл существует
            if not self.log_file_path.exists():
                logger.warning(
                    "error_log_not_found",
                    path=str(self.log_file_path),
                )
                # Создаем файл если его нет
                self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
                self.log_file_path.touch()
            
            # Запускаем наблюдение за директорией
            self.observer.schedule(
                self.event_handler,
                str(self.log_file_path.parent),
                recursive=False,
            )
            self.observer.start()
            
            logger.info(
                "error_monitor_started",
                log_file=str(self.log_file_path),
                developer_tg_id=self.developer_tg_id,
            )
            
        except Exception as e:
            logger.error(
                "error_starting_monitor",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
    
    def stop(self):
        """Останавливает мониторинг"""
        try:
            self.observer.stop()
            self.observer.join()
            logger.info("error_monitor_stopped")
        except Exception as e:
            logger.error(
                "error_stopping_monitor",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
