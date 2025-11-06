from aiogram.types import (InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           KeyboardButton,
                           ReplyKeyboardMarkup)

def createCardKeyboard(dict_of_dicts:list):
    keyboard = InlineKeyboardMarkup(inline_keyboard =[
                                    [InlineKeyboardButton(text=f"{student['surname']} {student['name']}", callback_data=f'card:{id}')]
                                    for id, student in dict_of_dicts if student['name'] and student['surname']
                                    ])

    next = InlineKeyboardButton(text='Далее', callback_data='next:card')

    back = InlineKeyboardButton(text='Назад', callback_data='back:card')

    exit = InlineKeyboardButton(text='Выход', callback_data='exit:card')

    keyboard.inline_keyboard.append([next])
    keyboard.inline_keyboard.append([back])
    keyboard.inline_keyboard.append([exit])

    return keyboard

def createAdminPanel():
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👥 Студенты"), KeyboardButton(text="💰 Начислить Qcoins")],
        [KeyboardButton(text="🚫 Выдать штраф"), KeyboardButton(text="🏪 Управление магазином")],
        [KeyboardButton(text="📈 Отчеты"), KeyboardButton(text="🗒️ Лог действий")],
        [KeyboardButton(text="👨‍🎓 Добавить студентов"), KeyboardButton(text="📥 Добавить задачу")]
    ])
    return keyboard

def createStudentPanel():
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Мой прогресс"), KeyboardButton(text="📝 Отправить отчет")],
        [KeyboardButton(text="🏪 Магазин"), KeyboardButton(text="💰 Лог действий")]
    ])
    return keyboard



def createInlineTaskButton(task_id: str):
    keyboard = [
        [InlineKeyboardButton(text="Сделать эту задачу", callback_data=f"report:{task_id}")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def levelsKeyboard(level):
    keyboard = []
    for i in range(1, level + 1):
        keyboard.append([
            InlineKeyboardButton(text=f"Уровень {i}", callback_data=f"level:{i}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def assessReport(student_id, task_id):
    button1 = InlineKeyboardButton(text='Оценить', callback_data=f'assess:{student_id}:{task_id}')
    button2 = InlineKeyboardButton(text='Вернуть', callback_data=f'fail:{student_id}:{task_id}')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button1], [button2]])
    return keyboard

def nextKeyboard():
    button = InlineKeyboardButton(text='Далее', callback_data=f'next:logs')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard

def exitKeyboard():
    button = InlineKeyboardButton(text='Выход', callback_data='exit:card')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard

# Магазин
# Сторона куратора
def addGoodKeyboard():
    keyboard = [
        [InlineKeyboardButton(text="Далее", callback_data=f"next:shop")],
        [InlineKeyboardButton(text="Назад", callback_data=f"back:shop")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"add:shop")],
        [InlineKeyboardButton(text='Выход', callback_data='exit:card')]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def addGoodButton():
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"add:shop")],
        [InlineKeyboardButton(text='Выход', callback_data='exit:card')]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Сторона студента
def buyGoodKeyboard(good_id):
    keyboard = [
        [InlineKeyboardButton(text="Купить", callback_data=f"buy:{good_id}")],
        [InlineKeyboardButton(text="Далее", callback_data=f"next:shop")],
        [InlineKeyboardButton(text="Назад", callback_data=f"back:shop")],
        [InlineKeyboardButton(text='Выход', callback_data='exit:card')]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)