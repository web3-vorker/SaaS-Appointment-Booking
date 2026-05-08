# main.py - точка входа в приложение, где создается экземпляр FastAPI и подключаются роуты

from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers.route import main_router
from app.dev.dev_router import dev_router
from app.admin.admin_router import admin_router
from app.utils.logger import logger
from app.redis.limiter import close_redis
from app.db.database import engine
from app.models.base import Base
import app.models.events
from app.scheduler.event_scheduler import event_scheduler_loop
from app.config.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Создаем все таблицы в БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.event_scheduler_task = asyncio.create_task(event_scheduler_loop())
    yield

    # Shutdown: отменяем задачу планировщика
    scheduler_task = getattr(app.state, "event_scheduler_task", None)
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    
    # Закрываем Redis соединение
    await close_redis()
    logger.info("Redis connection closed")


app = FastAPI(title="SaaS Appointment Booking API", version="1.0.0", lifespan=lifespan)
app.include_router(main_router)
app.include_router(dev_router)
app.include_router(admin_router)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger.info(f"{request.method} {request.url.path}")
        try:
            response = await call_next(request)
            logger.info(f"Response: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Middleware error: {str(e)}")
            raise

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=config.cors_methods,
    allow_headers=config.cors_headers,
    allow_credentials=config.cors_credentials,
)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
  uvicorn.run("app.main:app", reload=True)
