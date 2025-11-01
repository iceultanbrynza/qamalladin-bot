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
        [KeyboardButton(text="🏪 Магазин"), KeyboardButton(text="💰 Лог действий")],
        [KeyboardButton(text="📌 Правила игры")]
    ])
    return keyboard



def createInlineTaskButton(id):
    keyboard = InlineKeyboardMarkup(inline_keyboard =[
        [InlineKeyboardButton(text="Сделать эту задачу", callback_data=f'report:{id}')]
    ])
    return keyboard

def assessReport(student_id, task_id):
    button = InlineKeyboardButton(text='Оценить', callback_data=f'assess:{student_id}:{task_id}')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard

def nextKeyboard():
    button = InlineKeyboardButton(text='Далее', callback_data=f'next:logs')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard

def exitKeyboard():
    button = InlineKeyboardButton(text='Выход', callback_data='exit:card')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard