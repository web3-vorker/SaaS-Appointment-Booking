# API Documentation

## Overview

This document describes the public REST API for the SaaS Appointment Booking service.
All API requests are served under the `/api/v1` prefix.

## Authentication

All endpoints require an API key header:

- Header: `X-API-Key`
- Value: business API key

Example:

```http
X-API-Key: test-api-key-12345
```

## Base URL

For local development:

```http
http://localhost:8000/api/v1
```

For production, replace with the deployed URL.

---

## Endpoints

### 1. Get business staff list

`GET /staffs/`

Response:

```json
[
  {
    "id": 1,
    "name": "Ivan",
    "role": "Stylist",
    "business_id": 1
  }
]
```

---

### 2. Get business services

`GET /services/`

Response:

```json
[
  {
    "id": 1,
    "name": "Haircut",
    "price": 1200,
    "duration_minutes": 60,
    "business_id": 1
  }
]
```

---

### 3. Get available free days for a staff member

`GET /staffs/{staff_id}/free-days/?service_id={service_id}`

Query parameters:

- `service_id` — required

Response:

```json
[
  { "date": "2026-05-03", "slots_count": 4 },
  { "date": "2026-05-04", "slots_count": 2 }
]
```

---

### 4. Get available free slots for a staff member on a date

`GET /staffs/{staff_id}/free-slots/?date={YYYY-MM-DD}&service_id={service_id}`

Query parameters:

- `date` — required, format `YYYY-MM-DD`
- `service_id` — required

Response:

```json
[
  "2026-05-03T09:00:00+00:00",
  "2026-05-03T10:00:00+00:00"
]
```

Slots are returned in ISO 8601 format.

---

### 5. Get client appointments

`GET /clients/{client_id}/appointments/`

Response:

```json
[
  {
    "id": 10,
    "business_id": 1,
    "client_id": 5,
    "staff_id": 2,
    "service_id": 3,
    "start_time": "2026-05-10T14:00:00+00:00",
    "end_time": "2026-05-10T15:00:00+00:00",
    "status": "scheduled",
    "service": {
      "id": 3,
      "name": "Massage",
      "price": 2000,
      "duration_minutes": 60,
      "business_id": 1
    },
    "staff": {
      "id": 2,
      "name": "Anna",
      "role": "Therapist",
      "business_id": 1
    }
  }
]
```

---

### 6. Create or get client by Telegram ID

`POST /clients/get-or-create/?tg_id={tg_id}&client_name={client_name}`

Query parameters:

- `tg_id` — Telegram user ID
- `client_name` — client name

Response:

```json
{
  "id": 5,
  "name": "Anton",
  "tg_id": 123456789,
  "business_id": 1
}
```

This endpoint is useful for bot integrations to ensure the user exists in the business database.

---

### 7. Create appointment

`POST /appointments/`

Request body:

```json
{
  "client_id": 5,
  "staff_id": 2,
  "service_id": 3,
  "start_time": "2026-05-10T14:00:00+00:00",
  "end_time": "2026-05-10T15:00:00+00:00"
}
```

Response:

```json
{
  "id": 10,
  "business_id": 1,
  "client_id": 5,
  "staff_id": 2,
  "service_id": 3,
  "start_time": "2026-05-10T14:00:00+00:00",
  "end_time": "2026-05-10T15:00:00+00:00",
  "status": "scheduled"
}
```

Errors:

- `400` when appointment overlaps or client/staff does not belong to the business
- `404` when service is not found

---

### 8. Cancel appointment

`POST /clients/{client_id}/appointments/{appointment_id}/`

Response:

```json
{ "message": "Запись успешно отменена" }
```

---

### 9. Get pending events

`GET /events/`

Response:

```json
[
  {
    "id": 1,
    "type": "appointment_reminder",
    "business_id": 1,
    "appointment_id": 10,
    "payload": {
      "client_tg_id": 123456789,
      "text": "⏰ Напоминание: у вас запись на 10.05.2026 14:00 к Anna"
    },
    "is_sent": false,
    "created_at": "2026-05-10T13:00:00"
  }
]
```

This endpoint is intended for the Telegram bot or an external delivery worker.

---

### 10. Mark event as sent

`POST /events/{event_id}/mark-sent/`

Response:

```json
{ "message": "Event marked as sent", "event_id": 1 }
```

Use this after a reminder has been successfully delivered to prevent duplicate sending.

---

## Error Handling

Standard error response format:

```json
{
  "detail": "Error message"
}
```

Common status codes:

- `200` — success
- `400` — bad request / validation error
- `401` — invalid API key
- `404` — not found
- `500` — internal server error

---

## Integration Notes

- Use `POST /clients/get-or-create/` before creating appointments to ensure the Telegram user exists.
- Use `GET /staffs/{staff_id}/free-days/` and `GET /staffs/{staff_id}/free-slots/` to offer available booking options.
- For reminder delivery, poll `GET /events/` regularly and call `POST /events/{event_id}/mark-sent/` after successful notification.
- All date/time values are returned in ISO 8601 format.

---

## Example flow for a Telegram bot integration

1. `POST /clients/get-or-create/?tg_id=12345&client_name=Ivan`
2. `GET /staffs/`
3. `GET /services/`
4. `GET /staffs/{staff_id}/free-days/?service_id={service_id}`
5. `GET /staffs/{staff_id}/free-slots/?date=2026-05-10&service_id={service_id}`
6. `POST /appointments/` with chosen slot
7. Periodically poll `GET /events/`
8. After sending reminder, `POST /events/{event_id}/mark-sent/`

---

## Developer and environment settings

Required environment variables:

- `DATABASE_URL`
- `API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `API_URL` (for bot or external services)

Optional:

- `TELEGRAM_PROXY` — proxy URL for Telegram bot traffic
- `EVENT_POLL_INTERVAL` — polling interval in seconds for Telegram bot event delivery
