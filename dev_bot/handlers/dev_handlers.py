"""
Обработчики команд для developer бота
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from dev_bot.keyboards.dev_keyboards import (
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_cancel_keyboard,
    get_business_list_keyboard,
    get_business_actions_keyboard,
    get_confirm_delete_keyboard,
    get_staff_menu_keyboard,
    get_service_menu_keyboard,
    get_schedule_menu_keyboard,
    get_business_selection_keyboard,
    get_yes_no_keyboard
)
from dev_bot.states.dev_states import (
    CreateBusinessStates,
    CreateStaffStates,
    CreateServiceStates,
    AssignServiceStates,
    UpdateScheduleStates,
    CreateExceptionStates
)
from dev_bot.utils.api import dev_api
from app.utils.datetime_utils import now_utc

router = Router()


# ===== Команды =====

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "🔧 <b>Developer Panel</b>\n\n"
        "Добро пожаловать в панель разработчика!\n"
        "Здесь вы можете управлять бизнесами, подключенными к вашему SaaS сервису.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "🔧 <b>Developer Panel</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


# ===== Список бизнесов =====

@router.callback_query(F.data == "list_businesses")
async def list_businesses(callback: CallbackQuery):
    """Показать список всех бизнесов"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "📋 <b>Список бизнесов</b>\n\n"
                "Пока нет подключенных бизнесов.",
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"📋 <b>Список бизнесов</b>\n\n"
                f"Всего бизнесов: {len(businesses)}\n"
                f"Выберите бизнес для просмотра:",
                reply_markup=get_business_list_keyboard(businesses),
                parse_mode="HTML"
            )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при получении списка бизнесов:\n{str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("business_"))
async def show_business_actions(callback: CallbackQuery):
    """Показать действия для бизнеса"""
    business_id = int(callback.data.split("_")[1])
    
    try:
        # Получаем информацию о бизнесе
        businesses = await dev_api.get_all_businesses()
        business = next((b for b in businesses if b['id'] == business_id), None)
        
        if not business:
            await callback.message.edit_text(
                "❌ Бизнес не найден",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        is_active = business.get('is_active', True)
        status_emoji = "🟢" if is_active else "🔴"
        status_text = "Активен" if is_active else "Неактивен"

        subscription_expires_at = business.get('subscription_expires_at')

        if subscription_expires_at:
            expires_dt = datetime.fromisoformat(subscription_expires_at)  # строку → datetime
            days_left = (expires_dt - now_utc()).days
            subscription_info = f"Осталось дней подписки: {days_left}"
        else:
            subscription_info = "Подписка: бессрочная"
        
        await callback.message.edit_text(
            f"🏢 <b>Бизнес: {business['name']}</b>\n"
            f"ID: {business_id}\n"
            f"Статус: {status_emoji} {status_text}\n"
            f"Тарифный план: {business['subscription_plan']}\n"
            f"{subscription_info}\n\n"
            f"Выберите действие:",
            reply_markup=get_business_actions_keyboard(business_id, is_active),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("delete_business_"))
async def confirm_delete_business(callback: CallbackQuery):
    """Подтверждение удаления бизнеса"""
    business_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        f"⚠️ <b>Удаление бизнеса</b>\n\n"
        f"Вы уверены, что хотите удалить бизнес ID: {business_id}?\n"
        f"Это действие необратимо!",
        reply_markup=get_confirm_delete_keyboard(business_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_active_"))
async def toggle_business_active(callback: CallbackQuery):
    """Переключить статус активности бизнеса"""
    business_id = int(callback.data.split("_")[2])
    
    try:
        result = await dev_api.toggle_business_active(business_id)
        
        # Обновляем отображение с новым статусом
        businesses = await dev_api.get_all_businesses()
        business = next((b for b in businesses if b['id'] == business_id), None)
        
        if business:
            is_active = business.get('is_active', True)
            status_emoji = "🟢" if is_active else "🔴"
            status_text = "Активен" if is_active else "Неактивен"
            
            await callback.message.edit_text(
                f"🏢 <b>Бизнес: {business['name']}</b>\n"
                f"ID: {business_id}\n"
                f"Статус: {status_emoji} {status_text}\n\n"
                f"{result['message']}\n\n"
                f"Выберите действие:",
                reply_markup=get_business_actions_keyboard(business_id, is_active),
                parse_mode="HTML"
            )
        
        await callback.answer(result['message'])
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при изменении статуса:\n{str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_staff_"))
async def delete_staff_handler(callback: CallbackQuery, state: FSMContext):
    """Удалить сотрудника"""
    parts = callback.data.split("_")
    business_id = int(parts[3])
    staff_id = int(parts[4])
    
    try:
        await dev_api.delete_staff(business_id, staff_id)
        await state.clear()
        await callback.message.edit_text(
            f"✅ Сотрудник успешно удален!",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        await state.clear()
        await callback.message.edit_text(
            f"❌ Ошибка при удалении сотрудника:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_service_"))
async def delete_service_handler(callback: CallbackQuery, state: FSMContext):
    """Удалить услугу"""
    parts = callback.data.split("_")
    business_id = int(parts[3])
    service_id = int(parts[4])
    
    try:
        await dev_api.delete_service(business_id, service_id)
        await state.clear()
        await callback.message.edit_text(
            f"✅ Услуга успешно удалена!",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        await state.clear()
        await callback.message.edit_text(
            f"❌ Ошибка при удалении услуги:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_business(callback: CallbackQuery):
    """Удалить бизнес"""
    business_id = int(callback.data.split("_")[2])

    try:
        await dev_api.delete_business(business_id)
        await callback.message.edit_text(
            f"✅ Бизнес ID: {business_id} успешно удален!",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при удалении бизнеса:\n{str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


# ===== Создание бизнеса =====

@router.callback_query(F.data == "create_business")
async def start_create_business(callback: CallbackQuery, state: FSMContext):
    """Начать создание бизнеса"""
    await state.set_state(CreateBusinessStates.entering_name)
    await callback.message.edit_text(
        "➕ <b>Создание бизнеса</b>\n\n"
        "Введите название бизнеса:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CreateBusinessStates.entering_name)
async def process_business_name(message: Message, state: FSMContext):
    """Обработка названия бизнеса"""
    await state.update_data(name=message.text)
    await state.set_state(CreateBusinessStates.entering_working_hours_start)
    await message.answer(
        "⏰ Введите время начала работы (формат HH:MM, например 09:00):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateBusinessStates.entering_working_hours_start)
async def process_working_hours_start(message: Message, state: FSMContext):
    """Обработка времени начала работы"""
    # Простая валидация формата
    if ":" not in message.text or len(message.text) != 5:
        await message.answer("❌ Неверный формат! Используйте HH:MM (например, 09:00)")
        return
    
    await state.update_data(working_hours_start=message.text)
    await state.set_state(CreateBusinessStates.entering_working_hours_end)
    await message.answer(
        "⏰ Введите время окончания работы (формат HH:MM, например 20:00):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateBusinessStates.entering_working_hours_end)
async def process_working_hours_end(message: Message, state: FSMContext):
    """Обработка времени окончания работы"""
    if ":" not in message.text or len(message.text) != 5:
        await message.answer("❌ Неверный формат! Используйте HH:MM (например, 20:00)")
        return
    
    await state.update_data(working_hours_end=message.text)
    await state.set_state(CreateBusinessStates.entering_owner_tg_id)
    await message.answer(
        "👤 Введите Telegram ID владельца бизнеса:",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateBusinessStates.entering_owner_tg_id)
async def process_owner_tg_id(message: Message, state: FSMContext):
    """Обработка Telegram ID владельца"""
    if not message.text.isdigit():
        await message.answer("❌ Telegram ID должен быть числом!")
        return
    
    await state.update_data(owner_tg_id=int(message.text))
    await state.set_state(CreateBusinessStates.entering_subscription_plan)
    await message.answer(
        "💰 Выберите тарифный план (Base или Pro):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateBusinessStates.entering_subscription_plan)
async def process_subscription_plan(message: Message, state: FSMContext):
    """Обработка тарифного плана и создание бизнеса"""
    if message.text not in ("Base", "Pro"):
        await message.answer("❌ Неправильный тарифный план, выберите Base или Pro")
        return

    subscription_plan = message.text
    await state.update_data(subscription_plan=subscription_plan)

    data = await state.get_data()
    if not all(key in data for key in ("name", "working_hours_start", "working_hours_end", "owner_tg_id")):
        await state.clear()
        await message.answer(
            "❌ Ошибка при создании бизнеса: данные сессии оказались неполными. Попробуйте заново.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    subscription_plan = data.get("subscription_plan") or "Base"
    # Создание бизнеса
    try:
        result = await dev_api.create_business(
            name=data['name'],
            working_hours_start=data['working_hours_start'],
            working_hours_end=data['working_hours_end'],
            owner_tg_id=data['owner_tg_id'],
            subscription_plan=subscription_plan
        )
        
        await state.clear()
        await message.answer(
            f"✅ <b>Бизнес успешно создан!</b>\n\n"
            f"ID: {result.get('id')}\n"
            f"Название: {result.get('name')}\n"
            f"Рабочее время: {result.get('working_time_start')} - {result.get('working_time_end')}\n"
            f"Тарифный план: {result.get('subscription_plan', 'Base')}\n"
            f"Длительность подписки: {result.get('subscription_duration')} дней\n"
            f"API Key: <code>{result.get('api_key')}</code>\n\n"
            f"⚠️ Сохраните API ключ! Он понадобится для настройки бота.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка при создании бизнеса:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


# ===== Управление сотрудниками =====

@router.callback_query(F.data == "manage_staff")
async def show_staff_menu(callback: CallbackQuery):
    """Показать меню управления сотрудниками"""
    await callback.message.edit_text(
        "👥 <b>Управление сотрудниками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_staff_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "add_staff")
async def start_add_staff(callback: CallbackQuery, state: FSMContext):
    """Начать добавление сотрудника"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов. Сначала создайте бизнес.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(CreateStaffStates.selecting_business)
        await callback.message.edit_text(
            "👥 <b>Добавление сотрудника</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "staff"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("staff_biz_"), CreateStaffStates.selecting_business)
async def process_staff_business_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бизнеса для сотрудника"""
    business_id = int(callback.data.split("_")[2])
    await state.update_data(business_id=business_id)
    await state.set_state(CreateStaffStates.entering_name)
    
    await callback.message.edit_text(
        "👤 Введите имя сотрудника:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(CreateStaffStates.entering_name)
async def process_staff_name(message: Message, state: FSMContext):
    """Обработка имени сотрудника"""
    await state.update_data(name=message.text)
    await state.set_state(CreateStaffStates.entering_role)
    await message.answer(
        "💼 Введите должность сотрудника (например: Мастер, Барбер):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateStaffStates.entering_role)
async def process_staff_role(message: Message, state: FSMContext):
    """Обработка должности и создание сотрудника"""
    data = await state.get_data()
    
    try:
        result = await dev_api.create_staff(
            business_id=data['business_id'],
            name=data['name'],
            role=message.text
        )
        
        await state.clear()
        await message.answer(
            f"✅ <b>Сотрудник успешно создан!</b>\n\n"
            f"ID: {result['id']}\n"
            f"Имя: {result['name']}\n"
            f"Должность: {result['role']}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка при создании сотрудника:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


# ===== Управление услугами =====

@router.callback_query(F.data == "manage_services")
async def show_service_menu(callback: CallbackQuery):
    """Показать меню управления услугами"""
    await callback.message.edit_text(
        "🛠️ <b>Управление услугами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_service_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "add_service")
async def start_add_service(callback: CallbackQuery, state: FSMContext):
    """Начать добавление услуги"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов. Сначала создайте бизнес.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(CreateServiceStates.selecting_business)
        await callback.message.edit_text(
            "🛠️ <b>Добавление услуги</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "service"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("service_biz_"), CreateServiceStates.selecting_business)
async def process_service_business_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бизнеса для услуги"""
    business_id = int(callback.data.split("_")[2])
    await state.update_data(business_id=business_id)
    await state.set_state(CreateServiceStates.entering_name)
    
    await callback.message.edit_text(
        "✂️ Введите название услуги:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(CreateServiceStates.entering_name)
async def process_service_name(message: Message, state: FSMContext):
    """Обработка названия услуги"""
    await state.update_data(name=message.text)
    await state.set_state(CreateServiceStates.entering_price)
    await message.answer(
        "💰 Введите цену услуги (в рублях, только число):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateServiceStates.entering_price)
async def process_service_price(message: Message, state: FSMContext):
    """Обработка цены услуги"""
    if not message.text.isdigit():
        await message.answer("❌ Цена должна быть числом!")
        return
    
    await state.update_data(price=int(message.text))
    await state.set_state(CreateServiceStates.entering_duration)
    await message.answer(
        "⏱️ Введите длительность услуги (в минутах, только число):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateServiceStates.entering_duration)
async def process_service_duration(message: Message, state: FSMContext):
    """Обработка длительности услуги"""
    if not message.text.isdigit():
        await message.answer("❌ Длительность должна быть числом!")
        return
    
    await state.update_data(duration_minutes=int(message.text))
    await state.set_state(CreateServiceStates.entering_description)
    await message.answer(
        "📝 Введите описание услуги (или отправьте '-' чтобы пропустить):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateServiceStates.entering_description)
async def process_service_description(message: Message, state: FSMContext):
    """Обработка описания и создание услуги"""
    data = await state.get_data()
    description = "" if message.text == "-" else message.text
    
    try:
        result = await dev_api.create_service(
            business_id=data['business_id'],
            name=data['name'],
            price=data['price'],
            duration_minutes=data['duration_minutes'],
            description=description
        )
        
        await state.clear()
        await message.answer(
            f"✅ <b>Услуга успешно создана!</b>\n\n"
            f"ID: {result['id']}\n"
            f"Название: {result['name']}\n"
            f"Цена: {result['price']} ₽\n"
            f"Длительность: {result['duration_minutes']} мин",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка при создании услуги:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "delete_staff")
async def start_delete_staff(callback: CallbackQuery, state: FSMContext):
    """Начать удаление сотрудника"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(CreateStaffStates.selecting_business)
        await state.update_data(action="delete")
        await callback.message.edit_text(
            "🗑️ <b>Удаление сотрудника</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "delete_staff"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("delete_staff_biz_"))
async def show_staff_list_for_delete(callback: CallbackQuery, state: FSMContext):
    """Показать список сотрудников для удаления"""
    business_id = int(callback.data.split("_")[3])
    
    try:
        staffs = await dev_api.get_staffs(business_id)
        
        if not staffs:
            await callback.message.edit_text(
                "❌ У этого бизнеса нет сотрудников.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for staff in staffs:
            buttons.append([InlineKeyboardButton(
                text=f"{staff['name']} - {staff['role']}",
                callback_data=f"confirm_delete_staff_{business_id}_{staff['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "👤 <b>Выберите сотрудника для удаления:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "delete_service")
async def start_delete_service(callback: CallbackQuery, state: FSMContext):
    """Начать удаление услуги"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(CreateServiceStates.selecting_business)
        await state.update_data(action="delete")
        await callback.message.edit_text(
            "🗑️ <b>Удаление услуги</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "delete_service"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("delete_service_biz_"))
async def show_service_list_for_delete(callback: CallbackQuery, state: FSMContext):
    """Показать список услуг для удаления"""
    business_id = int(callback.data.split("_")[3])
    
    try:
        services = await dev_api.get_services(business_id)
        
        if not services:
            await callback.message.edit_text(
                "❌ У этого бизнеса нет услуг.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for service in services:
            buttons.append([InlineKeyboardButton(
                text=f"{service['name']} - {service['price']}₽",
                callback_data=f"confirm_delete_service_{business_id}_{service['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "🛠️ <b>Выберите услугу для удаления:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


# ===== Привязка услуг к сотрудникам =====

@router.callback_query(F.data == "assign_services")
async def start_assign_services(callback: CallbackQuery, state: FSMContext):
    """Начать привязку услуги к сотруднику"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(AssignServiceStates.selecting_business)
        await callback.message.edit_text(
            "🔗 <b>Привязка услуг к сотруднику</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "assign"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_biz_"), AssignServiceStates.selecting_business)
async def process_assign_business_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бизнеса - показать список сотрудников"""
    business_id = int(callback.data.split("_")[2])
    await state.update_data(business_id=business_id)
    
    try:
        # Получаем всех сотрудников бизнеса
        staffs = await dev_api.get_staffs(business_id)
        
        if not staffs:
            await callback.message.edit_text(
                "❌ У этого бизнеса нет сотрудников.\n"
                "Сначала добавьте сотрудников.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        # Создаем кнопки со списком сотрудников
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for staff in staffs:
            buttons.append([InlineKeyboardButton(
                text=f"{staff['name']} - {staff['role']}",
                callback_data=f"assign_staff_{staff['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await state.set_state(AssignServiceStates.selecting_staff)
        await callback.message.edit_text(
            "👤 <b>Выберите сотрудника:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_staff_"), AssignServiceStates.selecting_staff)
async def process_assign_staff_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора сотрудника - показать список услуг с чекбоксами"""
    staff_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    business_id = data['business_id']
    
    try:
        # Получаем все услуги бизнеса
        services = await dev_api.get_services(business_id)
        
        if not services:
            await callback.message.edit_text(
                "❌ У этого бизнеса нет услуг.\n"
                "Сначала добавьте услуги.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        # Получаем уже привязанные услуги
        staff_services = await dev_api.get_staff_services(business_id)
        assigned_service_ids = [
            ss['service_id'] for ss in staff_services 
            if ss['staff_id'] == staff_id
        ]
        
        # Сохраняем данные
        await state.update_data(staff_id=staff_id, selected_services=assigned_service_ids)
        await state.set_state(AssignServiceStates.selecting_service)
        
        # Создаем кнопки с чекбоксами
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for service in services:
            is_selected = service['id'] in assigned_service_ids
            checkbox = "✅" if is_selected else "☐"
            buttons.append([InlineKeyboardButton(
                text=f"{checkbox} {service['name']} - {service['price']}₽",
                callback_data=f"toggle_service_{service['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="💾 Сохранить", callback_data="save_staff_services")])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "🔗 <b>Выберите услуги</b>\n\n"
            "Отметьте услуги, которые может делать этот сотрудник:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_service_"), AssignServiceStates.selecting_service)
async def toggle_service_selection(callback: CallbackQuery, state: FSMContext):
    """Переключение выбора услуги"""
    service_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected_services = data.get("selected_services", [])
    
    # Переключаем выбор
    if service_id in selected_services:
        selected_services.remove(service_id)
    else:
        selected_services.append(service_id)
    
    await state.update_data(selected_services=selected_services)
    
    # Обновляем кнопки
    try:
        business_id = data['business_id']
        services = await dev_api.get_services(business_id)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for service in services:
            is_selected = service['id'] in selected_services
            checkbox = "✅" if is_selected else "☐"
            buttons.append([InlineKeyboardButton(
                text=f"{checkbox} {service['name']} - {service['price']}₽",
                callback_data=f"toggle_service_{service['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="💾 Сохранить", callback_data="save_staff_services")])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "🔗 <b>Выберите услуги</b>\n\n"
            "Отметьте услуги, которые может делать этот сотрудник:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "save_staff_services", AssignServiceStates.selecting_service)
async def save_staff_services(callback: CallbackQuery, state: FSMContext):
    """Сохранение привязок услуг к сотруднику"""
    data = await state.get_data()
    business_id = data['business_id']
    staff_id = data['staff_id']
    selected_services = data.get("selected_services", [])
    
    try:
        # Создаем привязки для выбранных услуг
        for service_id in selected_services:
            try:
                await dev_api.assign_service_to_staff(
                    business_id=business_id,
                    staff_id=staff_id,
                    service_id=service_id
                )
            except Exception:
                # Игнорируем ошибки если привязка уже существует
                pass
        
        await state.clear()
        await callback.message.edit_text(
            f"✅ <b>Услуги успешно привязаны!</b>\n\n"
            f"Привязано услуг: {len(selected_services)}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await state.clear()
        await callback.message.edit_text(
            f"❌ Ошибка при сохранении:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


# ===== Управление графиком =====

@router.callback_query(F.data == "manage_schedule")
async def show_schedule_menu(callback: CallbackQuery):
    """Показать меню управления графиком"""
    await callback.message.edit_text(
        "📅 <b>Управление графиком работы</b>\n\n"
        "Выберите действие:",
        reply_markup=get_schedule_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_break")
async def start_set_break(callback: CallbackQuery, state: FSMContext):
    """Начать установку перерыва"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(UpdateScheduleStates.selecting_business)
        await state.update_data(action="set_break")
        await callback.message.edit_text(
            "⏰ <b>Установка перерыва</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "schedule"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("schedule_biz_"), UpdateScheduleStates.selecting_business)
async def process_schedule_business_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бизнеса для графика"""
    business_id = int(callback.data.split("_")[2])
    await state.update_data(business_id=business_id)
    await state.set_state(UpdateScheduleStates.entering_break_start)
    
    await callback.message.edit_text(
        "⏰ Введите время начала перерыва (формат HH:MM, например 13:00):",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(UpdateScheduleStates.entering_break_start)
async def process_break_start(message: Message, state: FSMContext):
    """Обработка времени начала перерыва"""
    if ":" not in message.text or len(message.text) != 5:
        await message.answer("❌ Неверный формат! Используйте HH:MM (например, 13:00)")
        return
    
    await state.update_data(break_start=message.text)
    await state.set_state(UpdateScheduleStates.entering_break_end)
    await message.answer(
        "⏰ Введите время окончания перерыва (формат HH:MM, например 14:00):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(UpdateScheduleStates.entering_break_end)
async def process_break_end(message: Message, state: FSMContext):
    """Обработка времени окончания перерыва и обновление графика"""
    if ":" not in message.text or len(message.text) != 5:
        await message.answer("❌ Неверный формат! Используйте HH:MM (например, 14:00)")
        return
    
    data = await state.get_data()
    
    try:
        result = await dev_api.update_schedule(
            business_id=data['business_id'],
            break_start=data['break_start'],
            break_end=message.text
        )
        
        await state.clear()
        await message.answer(
            f"✅ <b>Перерыв установлен!</b>\n\n"
            f"Начало: {result['break_start']}\n"
            f"Окончание: {result['break_end']}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка при установке перерыва:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "set_weekends")
async def start_set_weekends(callback: CallbackQuery, state: FSMContext):
    """Начать установку выходных"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(UpdateScheduleStates.selecting_business)
        await state.update_data(action="set_weekends")
        await callback.message.edit_text(
            "📅 <b>Установка выходных дней</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "weekends"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("weekends_biz_"), UpdateScheduleStates.selecting_business)
async def process_weekends_business_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бизнеса для выходных"""
    business_id = int(callback.data.split("_")[2])
    await state.update_data(business_id=business_id)
    await state.set_state(UpdateScheduleStates.entering_weekend_days)
    
    await callback.message.edit_text(
        "📅 Введите номера выходных дней через запятую:\n\n"
        "0 = Понедельник\n"
        "1 = Вторник\n"
        "2 = Среда\n"
        "3 = Четверг\n"
        "4 = Пятница\n"
        "5 = Суббота\n"
        "6 = Воскресенье\n\n"
        "Например: 5,6 (для Сб и Вс)",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(UpdateScheduleStates.entering_weekend_days)
async def process_weekend_days(message: Message, state: FSMContext):
    """Обработка выходных дней и обновление графика"""
    try:
        # Парсим введенные дни
        days_str = message.text.replace(" ", "")
        weekend_days = [int(d) for d in days_str.split(",")]
        
        # Валидация
        if not all(0 <= d <= 6 for d in weekend_days):
            await message.answer("❌ Номера дней должны быть от 0 до 6!")
            return
        
        data = await state.get_data()
        
        result = await dev_api.update_schedule(
            business_id=data['business_id'],
            weekend_days=weekend_days
        )
        
        await state.clear()
        
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        weekend_names = [day_names[d] for d in result['weekend_days']]
        
        await message.answer(
            f"✅ <b>Выходные дни установлены!</b>\n\n"
            f"Выходные: {', '.join(weekend_names)}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Неверный формат! Используйте числа через запятую (например: 5,6)")
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка при установке выходных:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "add_exception")
async def start_add_exception(callback: CallbackQuery, state: FSMContext):
    """Начать добавление исключения в графике"""
    try:
        businesses = await dev_api.get_all_businesses()
        
        if not businesses:
            await callback.message.edit_text(
                "❌ Нет доступных бизнесов.",
                reply_markup=get_back_to_menu_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(CreateExceptionStates.selecting_business)
        await callback.message.edit_text(
            "➕ <b>Добавление исключения в графике</b>\n\n"
            "Выберите бизнес:",
            reply_markup=get_business_selection_keyboard(businesses, "exception"),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("exception_biz_"), CreateExceptionStates.selecting_business)
async def process_exception_business_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бизнеса для исключения"""
    business_id = int(callback.data.split("_")[2])
    await state.update_data(business_id=business_id)
    await state.set_state(CreateExceptionStates.entering_date)
    
    await callback.message.edit_text(
        "📅 Введите дату исключения (формат YYYY-MM-DD, например 2026-05-15):",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(CreateExceptionStates.entering_date)
async def process_exception_date(message: Message, state: FSMContext):
    """Обработка даты исключения"""
    # Простая валидация формата
    if message.text.count("-") != 2 or len(message.text) != 10:
        await message.answer("❌ Неверный формат! Используйте YYYY-MM-DD (например, 2026-05-15)")
        return
    
    await state.update_data(date=message.text)
    await state.set_state(CreateExceptionStates.selecting_is_working)
    await message.answer(
        "❓ Бизнес работает в этот день?",
        reply_markup=get_yes_no_keyboard("exception_working")
    )


@router.callback_query(F.data.startswith("exception_working_"), CreateExceptionStates.selecting_is_working)
async def process_exception_is_working(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора работает ли бизнес"""
    is_working = callback.data.split("_")[2] == "yes"
    await state.update_data(is_working=is_working)
    
    if is_working:
        # Если работает, спросить про особое время
        await state.set_state(CreateExceptionStates.entering_custom_start)
        await callback.message.edit_text(
            "⏰ Введите особое время начала работы (формат HH:MM, или '-' для стандартного):",
            reply_markup=get_cancel_keyboard()
        )
    else:
        # Если не работает, сразу создаем исключение
        data = await state.get_data()
        try:
            result = await dev_api.create_schedule_exception(
                business_id=data['business_id'],
                date=data['date'],
                is_working=False
            )
            
            await state.clear()
            await callback.message.edit_text(
                f"✅ <b>Исключение создано!</b>\n\n"
                f"Дата: {result['date']}\n"
                f"Статус: Выходной день",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            await state.clear()
            await callback.message.edit_text(
                f"❌ Ошибка при создании исключения:\n{str(e)}",
                reply_markup=get_main_menu_keyboard()
            )
    
    await callback.answer()


@router.message(CreateExceptionStates.entering_custom_start)
async def process_exception_custom_start(message: Message, state: FSMContext):
    """Обработка особого времени начала"""
    if message.text != "-":
        if ":" not in message.text or len(message.text) != 5:
            await message.answer("❌ Неверный формат! Используйте HH:MM или '-'")
            return
        await state.update_data(custom_start=message.text)
    else:
        await state.update_data(custom_start=None)
    
    await state.set_state(CreateExceptionStates.entering_custom_end)
    await message.answer(
        "⏰ Введите особое время окончания работы (формат HH:MM, или '-' для стандартного):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateExceptionStates.entering_custom_end)
async def process_exception_custom_end(message: Message, state: FSMContext):
    """Обработка особого времени окончания и создание исключения"""
    custom_end = None if message.text == "-" else message.text
    
    if custom_end and (":" not in custom_end or len(custom_end) != 5):
        await message.answer("❌ Неверный формат! Используйте HH:MM или '-'")
        return
    
    data = await state.get_data()
    
    try:
        result = await dev_api.create_schedule_exception(
            business_id=data['business_id'],
            date=data['date'],
            is_working=data['is_working'],
            custom_start=data.get('custom_start'),
            custom_end=custom_end
        )
        
        await state.clear()
        
        time_info = ""
        if result['custom_start_time'] and result['custom_end_time']:
            time_info = f"\nВремя работы: {result['custom_start_time']} - {result['custom_end_time']}"
        
        await message.answer(
            f"✅ <b>Исключение создано!</b>\n\n"
            f"Дата: {result['date']}\n"
            f"Статус: Рабочий день{time_info}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Ошибка при создании исключения:\n{str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "list_exceptions")
async def list_exceptions(callback: CallbackQuery):
    """Показать список исключений"""
    await callback.message.edit_text(
        "📋 <b>Список исключений</b>\n\n"
        "Для просмотра исключений используйте developer endpoints напрямую:\n"
        "GET /dev/business/{business_id}/schedule-exceptions/",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "health_check")
async def health_check_handler(callback: CallbackQuery):
    """Проверка работы системы"""
    await callback.answer()
    
    try:
        result = await dev_api.health_check()
        
        status_emoji = "✅" if result.get("status") == "ok" else "❌"
        db_emoji = "✅" if result.get("database") == "ok" else "❌"
        redis_emoji = "✅" if result.get("redis") == "ok" else "❌"
        
        text = (
            f"🏥 <b>Проверка системы</b>\n\n"
            f"{status_emoji} <b>Статус:</b> {result.get('status', 'unknown')}\n"
            f"{db_emoji} <b>PostgreSQL:</b> {result.get('database', 'unknown')}\n"
            f"{redis_emoji} <b>Redis:</b> {result.get('redis', 'unknown')}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка проверки системы</b>\n\n{str(e)}",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()

