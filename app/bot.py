from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import bot
import requests
from string import Template
from datetime import datetime
from config import admis_list
from logger import create_logger
import traceback

logger = create_logger(__name__)


class User:

    def __init__(self, name, chat_id):
        self.name = name
        self.surname = None
        self.room = None
        self.chat_id = chat_id


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    try:
        # Проверяем, есть ли уже такой пользователь в базе данных
        response = get_user(message.chat.id)
        if response['result'] == 'OK':
            bot.send_message(message.chat.id, f'Привет, {response["name"]}! Для просмотра меню нажмите на /help',
                             reply_markup=gen_markup())
        else:
            msg = bot.reply_to(message, "Привет, я ваш помощник по дежурству!\nКак вас зовут?")
            logger.info(f'Новый пользователь. Chat_id: {message.chat.id} Функция: {traceback.extract_stack()[-1][2]}')
            bot.register_next_step_handler(msg, process_name_step)
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


@bot.message_handler(commands=['update'])
def update(message):
    try:
        if message.chat.id in admis_list:
            url = "http://127.0.0.1:5000/api/update"

            payload = {}
            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.request("PATCH", url, headers=headers, data=payload).json()
            if response['status'] == '250 OK':
                bot.send_message(message.chat.id, f'Список обновлён')
                logger.info(f'Список дежурств обновлён. Функция: {traceback.extract_stack()[-1][2]}')
            else:
                logger.error(f'Ошибка при работе с базой данных, Функция: {traceback.extract_stack()[-1][2]}')
                bot.send_message(message.chat.id, f'Что-то пошло не так')
        else:
            bot.send_message(message.chat.id, f'Нет прав доступа')
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


@bot.message_handler(commands=['delete'])
def delete(message):
    try:
        if message.chat.id in admis_list:
            msg = bot.reply_to(message, "Введи chat_id студента:")
            bot.register_next_step_handler(msg, deletion)
        else:
            bot.reply_to(message, "Нет прав доступа")
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def deletion(message):
    # Проверяем, есть ли уже такой пользователь в базе данных
    try:
        if message.text.isdigit():
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
                logger.info(f'Удалён студент с chat_id {message.text}. Функция: {traceback.extract_stack()[-1][2]}')
                # отправляем уведомление студенту, которому была присвоена дата дежурства удалённого студента
                chat_id = response['chat_id']
                if chat_id >= 0:
                    logger.info(f'Попытка отправки сообщения об изменениях в графике студенту с chat_id {chat_id}. '
                                f'Функция: {traceback.extract_stack()[-1][2]}')
                    bot.send_message(chat_id, 'Произошли изменения в графике, обратите, пожалуйста, внимание.\n'
                                              'Для того, чтобы узнать дату дежурства, нажмите на /help')
            elif response['status'] == '255 OK':
                bot.send_message(message.chat.id, f'Нет студента с таким chat_id')
            else:
                logger.error(f'Ошибка при работе с базой данных, Функция: {traceback.extract_stack()[-1][2]}')
                bot.send_message(message.chat.id, f'Что-то пошло не так')
        else:
            message = bot.reply_to(message, "Можно вводить только цифры. Для продолжения напиши любое слово")
            bot.register_next_step_handler(message, delete)
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def gen_markup():
    try:
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(InlineKeyboardButton('Сообщить о проблеме', callback_data='problem'),
                   InlineKeyboardButton('Узнать дату дежурства', callback_data='duty_date'),
                   InlineKeyboardButton('Уведомить о выселении', callback_data='ejectment'))
        return markup
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


@bot.callback_query_handler(func=lambda message: True)
def callback_query(call):
    try:
        chat_id = call.message.chat.id
        student = get_user(chat_id)
        if call.data == "problem":
            msg = bot.send_message(chat_id, 'Опишите детальнее проблему, пожалуйста!')
            bot.register_next_step_handler(msg, problem_step, student)
        elif call.data == "duty_date":
            date = datetime.strptime(student['date'], '%a, %d %b %Y %H:%M:%S %Z').date()
            date = date.strftime('%d-%m-%Y')
            bot.send_message(chat_id, f"Дата вашего дежурства: {date}")
        elif call.data == "ejectment":
            # отправка сообщения мне
            bot.send_message(429026017, f'Студент {student["name"]} {student["surname"]}, комната: {student["room"]}, '
                                        f'chat_id: {student["chat_id"]} выселяется.')
            bot.send_message(chat_id, 'Спасибо, уведомление отправлено.')
            logger.info(f'Студент {student["name"]} {student["surname"]} chat_id: {student["chat_id"]} сообщил о выселении.')
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def problem_step(message, student):
    try:
        url = "http://127.0.0.1:5000/api/problem"

        data = Template('{"text": "$text",\n"chat_id": $chat_id}')
        payload = data.substitute(text=message.text, chat_id=message.chat.id).encode(
            'utf-8')
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response['status'] == '250 OK':
            bot.send_message(message.chat.id, f'Спасибо, {student["name"]}! Мы приняли ваше сообщение.')
            logger.info(f'Студент {student["name"]} {student["surname"]} chat_id: {student["chat_id"]} сообщил о проблеме')
        else:
            bot.send_message(message.chat.id, f'Что-то пошло не так')
            logger.error(f'Ошибка при работе с базой данных, Функция: {traceback.extract_stack()[-1][2]}')
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def process_name_step(message):
    try:
        name = message.text
        user = User(name=name, chat_id=message.chat.id)
        msg = bot.reply_to(message, 'Ваша фамилия:')
        bot.register_next_step_handler(msg, process_surname_step, user)
    except Exception as e:
        bot.reply_to(message, 'oooops')
        # В {} указано имя функции
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def process_surname_step(message, user):
    try:
        user.surname = message.text
        msg = bot.reply_to(message, 'Номер вашей комнаты?')
        bot.register_next_step_handler(msg, process_room_step, user)
    except Exception:
        bot.reply_to(message, 'oooops')
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


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
            logger.info(f'Студент {user.name} {user.surname} chat_id: {user.chat_id} добавлен в БД.')
        else:
            bot.send_message(message.chat.id, f'Что-то пошло не так')
    except Exception:
        bot.reply_to(message, 'oooops')
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


@bot.message_handler(commands=['get'])
def get_command(message):
    try:
        if message.chat.id in admis_list:
            msg = bot.reply_to(message, "Введи chat_id студента:")
            bot.register_next_step_handler(msg, get_student)
        else:
            bot.reply_to(message, "Нет прав доступа")
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def get_student(message):
    try:
        if message.text.isdigit():
            response = get_user(message.text)
            if response['result'] == 'OK':
                date = datetime.strptime(response['date'], '%a, %d %b %Y %H:%M:%S %Z').date()
                date = date.strftime('%d-%m-%Y')
                bot.send_message(message.chat.id, f'{response["name"]} {response["surname"]}, комната: {response["room"]},'
                                                  f' дата дежурства: {date}')
            else:
                bot.send_message('Нет студента с таким chat_id')
        else:
            message = bot.reply_to(message, "Можно вводить только цифры. Для продолжения напиши любое слово")
            bot.register_next_step_handler(message, get_command)
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


def get_user(chat_id):
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        url = f"http://127.0.0.1:5000/api/student?chat-id={chat_id}"
        payload = {}
        files = {}
        response = requests.request("GET", url, headers=headers, data=payload, files=files).json()
        return response
    except Exception:
        logger.exception(f'Exeption occured {traceback.extract_stack()[-1][2]}', exc_info=True)


# Enable saving next step handlers to file "./.handlers-saves/step.save".
# Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
# saving will happen after delay 2 seconds.
# bot.enable_save_next_step_handlers(delay=2)
#
# # Load next_step_handlers from save file (default "./.handlers-saves/step.save")
# # WARNING It will work only if enable_save_next_step_handlers was called!
# bot.load_next_step_handlers()

if __name__ == '__main__':
    bot.polling()
