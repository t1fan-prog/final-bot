from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import bot
import logging
import requests
from string import Template
from datetime import datetime

log = logging.getLogger(__name__)


class User:

    def __init__(self, name, chat_id):
        self.name = name
        self.surname = None
        self.room = None
        self.chat_id = chat_id


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    # Проверяем, есть ли уже такой пользователь в базе данных
    response = get_user(message.chat.id)
    if response['result'] == 'OK':
        bot.send_message(message.chat.id, f'Привет, {response["name"]}! Чем могу помочь?', reply_markup=gen_markup())
    else:
        msg = bot.reply_to(message, "Привет, я ваш помощник по дежурству!\nКак вас зовут?")
        bot.register_next_step_handler(msg, process_name_step)


@bot.message_handler(commands=['delete'])
def delete(message):
    if message.chat.id == 429026017:
        msg = bot.reply_to(message, "Введи chat_id студента:")
        bot.register_next_step_handler(msg, deletion)
    else:
        bot.reply_to(message, "Нет прав доступа")


def deletion(message):
    # Проверяем, есть ли уже такой пользователь в базе данных
    url = "http://127.0.0.1:5000/api/delete"

    data = Template('{"chat_id": $chat_id}')
    payload = data.substitute(chat_id=message.text).encode(
        'utf-8')
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("DELETE", url, headers=headers, data=payload).json()
    if response['status'] == '250 OK':
        bot.send_message(message.chat.id, f'Студент был успешно удалён.')

        # отправляем уведомление студенту, которому была присвоена дата дежурства удалённого студента
        chat_id = response['chat_id']
        if chat_id >= 0:
            bot.send_message(chat_id, 'Произошли изменения в графике, обратите, пожалуйста, внимание.\n'
                                      'Для того, чтобы узнать дату дежурства, нажмите на /help')
    else:
        bot.send_message(message.chat.id, f'Что-то пошло не так')
    pass


def gen_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton('Сообщить о проблеме', callback_data='problem'),
               InlineKeyboardButton('Узнать дату дежурства', callback_data='duty_date'),
               InlineKeyboardButton('Уведомить о выселении', callback_data='ejectment'))
    return markup


@bot.callback_query_handler(func=lambda message: True)
def callback_query(call):
    chat_id = call.message.chat.id
    student = get_user(chat_id)
    if call.data == "problem":
        msg = bot.send_message(chat_id, 'Опишите детальнее проблему, пожалуйста!')
        bot.register_next_step_handler(msg, problem_step, student)
    elif call.data == "duty_date":
        date = datetime.strptime(student['date'], '%a, %d %b %Y %H:%M:%S %Z').date()
        date = date.strftime('%d/%m/%Y')
        bot.send_message(chat_id, f"Дата вашего дежурства: {date}")
    elif call.data == "ejectment":
        # отправка сообщения мне
        bot.send_message(429026017, f'Студент {student["name"]} {student["surname"]}, комната: {student["room"]}, '
                                    f'chat_id: {student["chat_id"]} выселяется.')
        bot.send_message(chat_id, 'Спасибо, уведомление отправлено.')


def problem_step(message, user):
    url = "http://127.0.0.1:5000/api/problem"

    data = Template('{"text": "$text",\n"chat_id": $chat_id}')
    payload = data.substitute(text=message.text, chat_id=message.chat.id).encode(
        'utf-8')
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload).json()
    if response['status'] == '250 OK':
        bot.send_message(message.chat.id, f'Спасибо, {user["name"]}! Мы приняли ваше сообщение.')
    else:
        bot.send_message(message.chat.id, f'Что-то пошло не так')
    pass


def process_name_step(message):
    try:
        name = message.text
        user = User(name=name, chat_id=message.chat.id)
        msg = bot.reply_to(message, 'Ваша фамилия:')
        bot.register_next_step_handler(msg, process_surname_step, user)
    except Exception as e:
        bot.reply_to(message, 'oooops')
        print(e)


def process_surname_step(message, user):
    try:
        user.surname = message.text
        msg = bot.reply_to(message, 'Номер вашей комнаты?')
        bot.register_next_step_handler(msg, process_room_step, user)
    except Exception:
        bot.reply_to(message, 'oooops')
        log.exception(f'[ERROR] Exeption occured process_surname_step', exc_info=True)


def process_room_step(message, user):
    try:
        room = message.text
        if not room.isdigit():
            msg = bot.reply_to(message, 'Введите число.\nОбратите внимание, что нужно ввести номер комнаты от 300 до '
                                        '335')
            bot.register_next_step_handler(msg, process_room_step, user)
            return
        room = int(room)
        if not 300 <= room <= 335:
            msg = bot.reply_to(message, 'Введите число от 300 до 335')
            bot.register_next_step_handler(msg, process_room_step, user)
            return

        user.room = room

        url = "http://127.0.0.1:5000/api/create-student"

        text = Template('{"name": "$name",\n"surname": "$surname",\n"room": $room,\n"chat_id": $chat_id}')
        payload = text.substitute(name=user.name, surname=user.surname, room=user.room, chat_id=user.chat_id).encode(
            'utf-8')
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response['status'] == '250 OK':
            bot.send_message(message.chat.id, f'Добро пожаловать, {user.name}!')
        else:
            bot.send_message(message.chat.id, f'Что-то пошло не так')
    except Exception as e:
        bot.reply_to(message, 'oooops')
        print(e)


def get_user(message_id, filters=None):
    headers = {
        'Content-Type': 'application/json'
    }
    url = f"http://127.0.0.1:5000/api/student?chat-id={message_id}"
    payload = {}
    files = {}
    response = requests.request("GET", url, headers=headers, data=payload, files=files).json()
    return response


# Enable saving next step handlers to file "./.handlers-saves/step.save".
# Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
# saving will happen after delay 2 seconds.
bot.enable_save_next_step_handlers(delay=2)

# Load next_step_handlers from save file (default "./.handlers-saves/step.save")
# WARNING It will work only if enable_save_next_step_handlers was called!
bot.load_next_step_handlers()

if __name__ == '__main__':
    bot.polling()
