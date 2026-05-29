# main.py - точка входа в приложение, где создается экземпляр FastAPI и подключаются роуты

from contextlib import asynccontextmanager
import asyncio
import uuid
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.routers.route import main_router
from app.dev.dev_router import dev_router
from app.admin.admin_router import admin_router
from app.utils.structured_logger import setup_logging, get_logger
from app.redis.limiter import close_redis
from app.scheduler.event_scheduler import event_scheduler_loop
from app.config.config import config

# Инициализация структурированного логирования
setup_logging(
    log_level=config.log_level,
    log_file_path=config.log_file_path,
    json_format=config.log_json_format,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="1.0.0", environment=config.log_level)
    app.state.event_scheduler_task = asyncio.create_task(event_scheduler_loop())
    yield

    # Shutdown: отменяем задачу планировщика
    logger.info("application_shutdown")
    scheduler_task = getattr(app.state, "event_scheduler_task", None)
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    
    # Закрываем Redis соединение
    await close_redis()
    logger.info("redis_connection_closed")


app = FastAPI(title="SaaS Appointment Booking API", version="1.0.0", lifespan=lifespan)


# Middleware для добавления request_id и логирования запросов
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Генерируем уникальный request_id
    request_id = str(uuid.uuid4())
    
    # Добавляем request_id в контекст structlog
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )
    
    # Логируем начало запроса
    start_time = time.time()
    logger.info("request_started")
    
    # Обрабатываем запрос
    try:
        response = await call_next(request)
        
        # Логируем успешный запрос
        duration = time.time() - start_time
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        
        # Добавляем request_id в заголовки ответа
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as exc:
        # Логируем ошибку
        duration = time.time() - start_time
        logger.error(
            "request_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=round(duration * 1000, 2),
            exc_info=True,
        )
        raise


app.include_router(main_router)
app.include_router(dev_router)
app.include_router(admin_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=config.cors_methods,
    allow_headers=config.cors_headers,
    allow_credentials=config.cors_credentials,
)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
  uvicorn.run("app.main:app", reload=True)
