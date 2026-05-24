# Alembic Migrations

## Управление схемой БД

Проект использует **только Alembic** для управления схемой БД (и в разработке, и в продакшне).

## Команды Alembic

### Применить все миграции
```bash
alembic upgrade head
```

### Создать новую миграцию (автогенерация)
```bash
alembic revision --autogenerate -m "описание изменений"
```

### Откатить последнюю миграцию
```bash
alembic downgrade -1
```

### Посмотреть текущую версию БД
```bash
alembic current
```

### Посмотреть историю миграций
```bash
alembic history
```

### Откатить все миграции
```bash
alembic downgrade base
```

## Workflow

1. Внесите изменения в модели (`app/models/`)
2. Создайте миграцию:
   ```bash
   alembic revision --autogenerate -m "add new field"
   ```
3. Проверьте созданную миграцию в `alembic/versions/`
4. Примените миграцию:
   ```bash
   alembic upgrade head
   ```
5. Закоммитьте миграцию в git

## Важно

- ⚠️ **Всегда проверяйте автогенерированные миграции перед применением**
- ⚠️ **Делайте бэкап БД перед применением миграций в продакшне**
- ⚠️ **Не редактируйте уже примененные миграции**
- ⚠️ **При первом запуске проекта выполните `alembic upgrade head`**

## Текущие миграции

1. `fa10ace46fd1` - Add user name
2. `c8a45261b61e` - Add schedule features and exceptions
3. `c7f77e67b5ae` - Delete bot_token from BusinessModel
4. `b279b40843b1` - Add client_name to appointments
5. `8e268243596e` - Change working_time to time type
6. `6a8ea777362e` - Add staff_services table for many-to-many
7. `28912222cbdc` - Add indexes to events table
