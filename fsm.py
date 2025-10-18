from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    student_card = State()

    student_choosing_for_accrual = State()
    accrual = State()

    student_choosing_for_fine = State()
    fine = State()

    get_report = State()

    send_report = State()
