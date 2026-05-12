"""
FSM состояния для developer бота
"""

from aiogram.fsm.state import State, StatesGroup


class CreateBusinessStates(StatesGroup):
    """Состояния для создания бизнеса"""
    entering_name = State()
    entering_working_hours_start = State()
    entering_working_hours_end = State()
    entering_owner_tg_id = State()


class CreateStaffStates(StatesGroup):
    """Состояния для создания сотрудника"""
    selecting_business = State()
    entering_name = State()
    entering_role = State()


class CreateServiceStates(StatesGroup):
    """Состояния для создания услуги"""
    selecting_business = State()
    entering_name = State()
    entering_price = State()
    entering_duration = State()
    entering_description = State()


class AssignServiceStates(StatesGroup):
    """Состояния для привязки услуги к сотруднику"""
    selecting_business = State()
    selecting_staff = State()
    selecting_service = State()


class UpdateScheduleStates(StatesGroup):
    """Состояния для обновления графика работы"""
    selecting_business = State()
    entering_break_start = State()
    entering_break_end = State()
    entering_weekend_days = State()


class CreateExceptionStates(StatesGroup):
    """Состояния для создания исключения в графике"""
    selecting_business = State()
    entering_date = State()
    selecting_is_working = State()
    entering_custom_start = State()
    entering_custom_end = State()
