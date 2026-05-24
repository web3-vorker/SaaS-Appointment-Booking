"""
Скрипт для ручного удаления всех тестовых бизнесов из базы.
Использует прямой доступ к БД через SQLAlchemy.
"""

import asyncio
import sys
sys.path.insert(0, 'C:\\Users\\eziko\\Desktop\\SaaS')

from sqlalchemy import select, delete
from app.db.database import new_session
from app.models.business import BusinessModel
# Импортируем все модели для разрешения связей
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.clients import ClientModel
from app.models.appointments import AppointmentModel
from app.models.events import EventModel
from app.models.schedule_exceptions import ScheduleExceptionModel
from app.models.staff_services import StaffServiceModel


async def cleanup_all_test_businesses():
    """Удаляет все бизнесы с именами 'Test Business%'"""
    print("="*80)
    print("РУЧНАЯ ОЧИСТКА ТЕСТОВЫХ БИЗНЕСОВ")
    print("="*80)
    print()
    
    async with new_session() as session:
        # Находим все тестовые бизнесы
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.name.like('Test Business%'))
        )
        businesses = result.scalars().all()
        
        if not businesses:
            print("[INFO] Тестовые бизнесы не найдены.")
            return
        
        print(f"[*] Найдено {len(businesses)} тестовых бизнесов:")
        for business in businesses:
            print(f"  - ID: {business.id}, Name: {business.name}")
        
        print()
        confirm = input("Удалить все эти бизнесы? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("[INFO] Отменено.")
            return
        
        # Удаляем
        deleted = 0
        for business in businesses:
            await session.delete(business)
            deleted += 1
            print(f"[OK] Удален бизнес #{business.id}: {business.name}")
        
        await session.commit()
        
        print()
        print(f"[OK] Удалено бизнесов: {deleted}")
        print()


if __name__ == "__main__":
    asyncio.run(cleanup_all_test_businesses())
