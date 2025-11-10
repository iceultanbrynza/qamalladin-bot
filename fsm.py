from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    student_card = State()

    student_choosing_for_accrual = State()
    accrual = State()
    comment = State() # Curator is about to write comment

    student_choosing_for_fine = State()
    fine = State()

    get_report = State() #Curator is about to choose student whose report he wants to see
    assess_report = State() #Curator is about to assess the report

    get_log = State() #Curator is about to choose to see next n logs

    add_students = State() #Curator is about to send list of new students to add

    update_levels = State() #Curator is about to send list of new levels in place of already existed

    add_tasks = State() #Curator is about to add new tasks

    add_goods = State()

    find_student = State()


    send_report = State() # Student is about to send report
    get_student_log = State() #Student is about to get logs
    shopping = State() #Student is about to purchase
