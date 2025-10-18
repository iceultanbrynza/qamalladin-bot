from aiogram.types import (InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           KeyboardButton,
                           ReplyKeyboardMarkup)

def createCardKeyboard(dict_of_dicts:dict):
    keyboard = InlineKeyboardMarkup(inline_keyboard =[
                                    [InlineKeyboardButton(text=f"{student['name']} {student['surname']}", callback_data=f'card:{id}')]
                                    for id, student in dict_of_dicts.items() if student['name'] and student['surname']
                                    ])

    exit = InlineKeyboardButton(text='Выход', callback_data='exit:card')

    keyboard.inline_keyboard.append([exit])

    return keyboard

def createAdminPanel():
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👥 Студенты"), KeyboardButton(text="💰 Начислить Qcoins")],
                                    [KeyboardButton(text="🚫 Выдать штраф"), KeyboardButton(text="🏪 Управление магазином")],
                                    [KeyboardButton(text="📈 Отчеты"), KeyboardButton(text="🗒️ Лог действий")]])
    return keyboard

def createStudentPanel():
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Мой прогресс"), KeyboardButton(text="📝 Отправить отчет")],
                                    [KeyboardButton(text="🏪 Магазин"), KeyboardButton(text="💰 Лог действий")],
                                    [KeyboardButton(text="📌 Правила игры")]])
    return keyboard



def createInlineTaskButton(id):
    keyboard = InlineKeyboardMarkup(inline_keyboard =
                                    [[InlineKeyboardButton(text="Сделать эту задачу", callback_data=f'report:{id}')]])
    return keyboard