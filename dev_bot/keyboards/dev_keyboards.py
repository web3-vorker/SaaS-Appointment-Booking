"""
Клавиатуры для developer бота
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню developer панели"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Список бизнесов", callback_data="list_businesses")],
        [InlineKeyboardButton(text="➕ Создать бизнес", callback_data="create_business")],
        [InlineKeyboardButton(text="👥 Управление сотрудниками", callback_data="manage_staff")],
        [InlineKeyboardButton(text="🛠️ Управление услугами", callback_data="manage_services")],
        [InlineKeyboardButton(text="🔗 Привязка услуг", callback_data="assign_services")],
        [InlineKeyboardButton(text="📅 Управление графиком", callback_data="manage_schedule")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    keyboard = [[InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    keyboard = [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_business_list_keyboard(businesses: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком бизнесов"""
    keyboard = []
    
    for business in businesses:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{business['name']} (ID: {business['id']})",
                callback_data=f"business_{business['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_business_actions_keyboard(business_id: int) -> InlineKeyboardMarkup:
    """Действия с конкретным бизнесом"""
    keyboard = [
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data=f"business_info_{business_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить бизнес", callback_data=f"delete_business_{business_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="list_businesses")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_delete_keyboard(business_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления бизнеса"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{business_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"business_{business_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_staff_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления сотрудниками"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить сотрудника", callback_data="add_staff")],
        [InlineKeyboardButton(text="🗑️ Удалить сотрудника", callback_data="delete_staff")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_service_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления услугами"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить услугу", callback_data="add_service")],
        [InlineKeyboardButton(text="🗑️ Удалить услугу", callback_data="delete_service")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления графиком"""
    keyboard = [
        [InlineKeyboardButton(text="⏰ Установить перерыв", callback_data="set_break")],
        [InlineKeyboardButton(text="📅 Установить выходные", callback_data="set_weekends")],
        [InlineKeyboardButton(text="➕ Добавить исключение", callback_data="add_exception")],
        [InlineKeyboardButton(text="📋 Список исключений", callback_data="list_exceptions")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_business_selection_keyboard(businesses: list, action: str) -> InlineKeyboardMarkup:
    """Выбор бизнеса для действия"""
    keyboard = []
    
    for business in businesses:
        keyboard.append([
            InlineKeyboardButton(
                text=business['name'],
                callback_data=f"{action}_biz_{business['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_yes_no_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Да", callback_data=f"{action}_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data=f"{action}_no")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
