from telebot import types
from app import bot
import logging
import requests
from string import Template

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
    headers = {
        'Content-Type': 'application/json'
    }
    url = f"http://127.0.0.1:5000/api/student?chat-id={message.chat.id}"
    payload = {}
    files = {}
    response = requests.request("GET", url, headers=headers, data=payload, files=files).json()
    if response['result'] == 'OK':
        bot.send_message(message.chat.id, f'Привет, {response["name"]}! Чем могу помочь?')
    else:
        msg = bot.reply_to(message, """\
    Привет, я ваш помощник по дежурству!
    Как вас зовут?
    """)
        bot.register_next_step_handler(msg, process_name_step)


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
            msg = bot.reply_to(message, 'Введите число.\nОбратите внимание, что нужно ввести номер комнаты от 300 до 335')
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
        payload = text.substitute(name=user.name, surname=user.surname, room=user.room, chat_id=user.chat_id).encode('utf-8')
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


# Enable saving next step handlers to file "./.handlers-saves/step.save".
# Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
# saving will hapen after delay 2 seconds.
bot.enable_save_next_step_handlers(delay=2)

# Load next_step_handlers from save file (default "./.handlers-saves/step.save")
# WARNING It will work only if enable_save_next_step_handlers was called!
bot.load_next_step_handlers()

if __name__ == '__main__':
    bot.polling()
