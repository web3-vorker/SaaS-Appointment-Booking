<img width="1536" height="1024" alt="SaaS System Architecture" src="https://github.com/user-attachments/assets/dd321d68-c289-469a-9bcf-e2540c42e48d" />
# SaaS Appointment Booking System

Сервис для записи клиентов к специалистам через Telegram ботов.

## Архитектура

- **Backend**: FastAPI с SQLAlchemy (async)
- **База данных**: SQLite (для разработки)
- **Бот**: aiogram для Telegram
- **Аутентификация**: API Key для бизнесов

## Установка

1. Клонируйте репозиторий
2. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Настройте переменные окружения (скопируйте `.env.example` в `.env`):
   ```bash
   cp .env.example .env
   ```
   Заполните необходимые значения.

## Запуск

### Backend
```bash
python -m app.main
```

### Бот
```bash
python bot/bot.py
```

## API Endpoints

Все endpoint'ы защищены API Key (заголовок `X-API-Key`).

- `GET /api/v1/staffs/` - список сотрудников
- `GET /api/v1/services/` - список услуг
- `GET /api/v1/staffs/{staff_id}/free-days/` - свободные дни сотрудника
- `GET /api/v1/staffs/{staff_id}/free-slots/` - свободные слоты на день
- `POST /api/v1/appointments/` - создать запись

## Структура проекта

```
app/
├── main.py              # Точка входа FastAPI
├── models/              # SQLAlchemy модели
├── routers/             # API роуты
├── services/            # Бизнес-логика
├── repository/          # Доступ к данным
├── utils/               # Утилиты
└── db/                  # Конфигурация БД

bot/
└── bot.py               # Telegram бот

tests/
└── test_api.py          # Тесты API
```

## Разработка

- Используйте async/await для всех операций с БД
- Все endpoint'ы должны быть защищены аутентификацией
- Логируйте важные операции
- Пишите тесты для новой функциональности
