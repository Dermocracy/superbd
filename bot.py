# bot.py
import telebot
from telebot import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils.markdown import text, hlink
import asyncio
import uuid


import psycopg2
from datetime import datetime
import logging

sent_messages = []

from database import (add_user, get_user_by_tg_id, add_message, list_projects, get_messages_by_parent_id, get_node_by_id,
                      create_project, add_user_to_project_in_db, remove_user_from_project_in_db, get_projects_for_user,
                      update_user_role_in_project_in_db, get_project, update_project, delete_project,
                      create_task, get_root_node, get_project_by_id, is_user_in_project, search_tasks_and_projects,
                      cursor)
import database

API_TOKEN = '6054540829:AAHxxfRyImxaWZQPSWIL5B5zHyD275WbWK4'
bot = telebot.TeleBot(API_TOKEN)
bot_id = bot.get_me().id


class MessageInputState(StatesGroup):
    waiting_for_text = State()


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    user = get_user_by_tg_id(user_id)
    if not user:
        add_user(user_id, username, first_name, last_name)
    bot.send_message(user_id, "Добро пожаловать! Выберите действие:", reply_markup=main_menu())


# 123
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 To-do", "🔍 Поиск")
    markup.row("📁 Проекты", "🗄️ Базы данных")
    return markup


@bot.message_handler(func=lambda message: message.text == "📁 Проекты")
def handle_projects(message):
    display_projects(message)


@bot.message_handler(func=lambda message: message.text == "📋 To-do")
def handle_todo(message):
    pass  # здесь можно добавить обработчик для пункта меню "To-do"


@bot.message_handler(func=lambda message: message.text == "🔍 Поиск")
def handle_search(message):
    search(message)


@bot.message_handler(func=lambda message: message.text == "🗄️ Базы данных")
def handle_databases(message):
    pass  # здесь можно добавить обработчик для пункта меню "Базы данных"


@bot.callback_query_handler(func=lambda call: call.data == "create_project")
def on_create_project_button_pressed(call):
    bot.answer_callback_query(call.id)
    create_project_workflow(call.from_user.id)


def create_project_workflow(user_id):
    msg = bot.send_message(user_id, "Введите название проекта:")
    bot.register_next_step_handler(msg, on_project_name_received, user_id)


def on_project_name_received(message, user_id):
    if message.chat.id == user_id:
        project_name = message.text
        msg = bot.send_message(user_id, "Введите описание проекта:")
        bot.register_next_step_handler(msg, on_project_description_received, user_id, project_name)


def on_project_description_received(message, user_id, project_name):
    if message.chat.id == user_id:
        project_description = message.text
        database.create_project(project_name, project_description, user_id)
        bot.send_message(user_id, "Проект успешно создан.", reply_markup=main_menu())


def create_root_node():
    return {
        'id': str(uuid.uuid4()),
        'user_id': None,
        'project_id': None,
        'parent_id': None,
        'title': 'Корневой узел',
        'content': None,
        'date_created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


nodes = []
adding_message_data = {}
root_node = create_root_node()





def create_default_project(user_id):
    default_project_title = 'Основной проект'
    default_project_description = 'Этот проект содержит все возможные функции бота.'
    create_project(default_project_title, default_project_description, user_id)


def display_projects(message):
    global sent_messages

    user_id = message.from_user.id
    projects = get_projects_for_user(user_id)

    if not projects:
        create_default_project(user_id)
        projects = get_projects_for_user(user_id)
        bot.send_message(user_id, "Мы создали для вас основной проект, который содержит все возможные функции бота.")

    # Отображаем список проектов
    if projects:
        bot.send_message(user_id, "Ваши проекты:")
        sent_messages = []
        for project in projects:
            project_id = project[0]
            project_title = project[1]
            project_description = project[2]

            markup = types.InlineKeyboardMarkup()
            open_project_button = types.InlineKeyboardButton("📂 Открыть проект",
                                                             callback_data=f"open_project:{project_id}")
            markup.add(open_project_button)

            project_text = f"{project_title}\nОписание: {project_description}"
            sent_msg = bot.send_message(user_id, project_text, reply_markup=markup)
            sent_messages.append(sent_msg.message_id)

    # Добавляем кнопку создания нового проекта после списка существующих проектов
    create_project_markup = types.InlineKeyboardMarkup()
    create_project_button = types.InlineKeyboardButton("➕ Создать проект", callback_data="create_project")
    create_project_markup.add(create_project_button)
    create_project_msg = bot.send_message(user_id, "Создать новый проект:", reply_markup=create_project_markup)
    sent_messages.append(create_project_msg.message_id)


def add_user_to_project(message, project_id, user_id, role):
    if not is_user_in_project(message.from_user.id, project_id):
        bot.send_message(message.from_user.id, "У вас нет доступа к управлению этим проектом.")
        return

    # Добавление пользователя к проекту с заданной ролью
    add_user_to_project_in_db(project_id, user_id, role)


def remove_user_from_project(message, project_id, user_id):
    if not is_user_in_project(message.from_user.id, project_id):
        bot.send_message(message.from_user.id, "У вас нет доступа к управлению этим проектом.")
        return

    # Удаление пользователя из проекта
    remove_user_from_project_in_db(project_id, user_id)


def change_role_in_project(message, project_id, user_id, new_role):
    if not is_user_in_project(message.from_user.id, project_id):
        bot.send_message(message.from_user.id, "У вас нет доступа к управлению этим проектом.")
        return

    # Изменение роли пользователя в проекте
    update_user_role_in_project_in_db(project_id, user_id, new_role)


def add_user_to_project_workflow(message, project_id):
    msg = bot.send_message(message.chat.id, "Введите внутренний ID пользователя, которого хотите добавить:")
    bot.register_next_step_handler(msg, on_add_user_id_received, project_id)


def on_add_user_id_received(message, project_id):
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "Выберите роль для пользователя:\n1. MEMBER\n2. ADMIN")
        bot.register_next_step_handler(msg, on_role_selection_received, project_id, user_id)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат ID. Повторите попытку.")


def on_role_selection_received(message, project_id, user_id):
    selected_role = message.text.upper()
    if selected_role in ['1', 'MEMBER', '2', 'ADMIN']:
        if selected_role == '1':
            selected_role = 'MEMBER'
        elif selected_role == '2':
            selected_role = 'ADMIN'
        add_user_to_project_in_db(project_id, user_id, selected_role)
        bot.send_message(message.chat.id, "Пользователь добавлен в проект.")
    else:
        bot.send_message(message.chat.id, "Неверный выбор роли. Повторите попытку.")


def change_user_role_workflow(message, project_id):
    msg = bot.send_message(message.chat.id, "Введите внутренний ID пользователя, для которого хотите изменить роль:")
    bot.register_next_step_handler(msg, on_change_role_user_id_received, project_id)


def on_change_role_user_id_received(message, project_id):
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "Выберите новую роль для пользователя:\n1. MEMBER\n2. ADMIN")
        bot.register_next_step_handler(msg, on_new_role_selection_received, project_id, user_id)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат ID. Повторите попытку.")


def on_new_role_selection_received(message, project_id, user_id):
    new_role = message.text.upper()
    if new_role in ['1', 'MEMBER', '2', 'ADMIN']:
        if new_role == '1':
            new_role = 'MEMBER'
        elif new_role == '2':
            new_role = 'ADMIN'
        change_role_in_project(message, project_id, user_id, new_role)
        bot.send_message(message.chat.id, "Роль пользователя изменена.")
    else:
        bot.send_message(message.chat.id, "Неверный выбор роли. Повторите попытку.")


def remove_user_from_project_workflow(message, project_id):
    msg = bot.send_message(message.chat.id, "Введите внутренний ID пользователя, которого хотите удалить из проекта:")
    bot.register_next_step_handler(msg, on_remove_user_id_received, project_id)


def on_remove_user_id_received(message, project_id):
    try:
        user_id = int(message.text)
        remove_user_from_project(message, project_id, user_id)
        bot.send_message(message.chat.id, "Пользователь удален из проекта.")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат ID. Повторите попытку.")


def manage_project(message, project_id):
    user_id = message.chat.id
    project = get_project_by_id(project_id)

    if not project or not is_user_in_project(user_id, project_id):
        bot.send_message(user_id, "У вас нет доступа к управлению этим проектом.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить пользователя", "🔄 Изменить роль пользователя")
    markup.row("➖ Удалить пользователя", "🔙 Назад")
    msg = bot.send_message(user_id, "Выберите действие для управления проектом:", reply_markup=markup)

    bot.register_next_step_handler(msg, on_management_option_selected, project_id)


def on_management_option_selected(message, project_id):
    option = message.text

    if option == "➕ Добавить пользователя":
        add_user_to_project_workflow(message, project_id)
    elif option == "🔄 Изменить роль пользователя":
        change_user_role_workflow(message, project_id)
    elif option == "➖ Удалить пользователя":
        remove_user_from_project_workflow(message, project_id)
    elif option == "🔙 Назад":
        bot.send_message(message.chat.id, "Возвращаемся к главному меню.", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "Неверный выбор опции. Повторите попытку.")


def open_project(call, project_id):
    global sent_messages

    user_id = call.from_user.id
    project = get_project_by_id(project_id)

    # Удаляем предыдущие сообщения
    for message_id in sent_messages:
        try:
            bot.delete_message(user_id, message_id)
        except Exception as e:
            print(f"Error deleting message: {e}")

    sent_messages = []

    if project is not None:
        root_node = get_root_node(project_id)

        if root_node is not None:
            fake_callback_query = types.CallbackQuery(id=0, from_user=call.from_user, message=call.message,
                                                      data=call.data, chat_instance='', json_string='')

            open_node_handler(fake_callback_query)
        else:
            bot.send_message(user_id, "Не удалось найти корневой узел проекта.")

        # Отправляем сообщение с кнопками действий
        actions_markup = types.InlineKeyboardMarkup(row_width=1)
        add_task_button = types.InlineKeyboardButton("➕ Добавить задачу", callback_data=f"add_task:{project_id}")
        add_message_button = types.InlineKeyboardButton("📝 Добавить сообщение",
                                                        callback_data=f"add_message:{project_id}")
        close_button = types.InlineKeyboardButton("❌ Закрыть", callback_data=f"close_project:{project_id}")

        manage_project_button = types.InlineKeyboardButton("⚙️ Управление проектом",
                                                           callback_data=f"manage_project:{project_id}")
        actions_markup.add(add_task_button, add_message_button, manage_project_button, close_button)

        actions_msg = bot.send_message(user_id, "Выберите действие:", reply_markup=actions_markup)
        sent_messages.append(actions_msg.message_id)  # добавьте эту строку


@bot.callback_query_handler(func=lambda call: call.data.startswith("close_project:"))
def close_project_handler(call):
    project_id = int(call.data.split(":")[1])
    close_project(call)


def close_project(call):
    user_id = call.from_user.id
    bot.delete_message(user_id, call.message.message_id)  # удалите сообщение с открытым проектом


# Обработчики событий для инлайн кнопок
def on_inline_button_click(call):
    user_id = call.from_user.id
    data = call.data

    if data.startswith("manage_project:"):
        project_id = int(data.split(":")[1])
        manage_project(call.message, project_id)
    elif data.startswith("open_tasks:"):
        project_id = int(data.split(":")[1])
        display_tasks(call.message, project_id)
    elif data.startswith("open_messages:"):
        project_id = int(data.split(":")[1])
        display_messages(call.message, project_id)
    elif data.startswith("open_project:"):
        logging.basicConfig(level=logging.INFO)
        logging.info(f"Open project: {project_id}")
        project_id = int(data.split(":")[1])
        open_project(call.message, project_id)
    # ... другие обработчики callback_data


@bot.callback_query_handler(func=lambda call: call.data.startswith("open_node"))
def open_node_handler(call):
    node_id = int(call.data.split(":")[1])
    display_node(call, node_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("close_node"))
def close_node_handler(call):
    node_id = int(call.data.split(":")[1])
    display_node(call, node_id, go_back=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_task"))
def add_task_handler(call):
    project_id = int(call.data.split(":")[1])
    # Здесь добавьте код для добавления задачи и обновления узла


@bot.callback_query_handler(func=lambda call: call.data.startswith('open_project:'))
def open_project_handler(call):
    project_id = int(call.data.split(':')[1])
    open_project(call, project_id)


def add_task_workflow(message, project_id):
    user_id = message.chat.id
    msg = bot.send_message(user_id, "Введите название задачи:")
    bot.register_next_step_handler(msg, on_task_name_received, project_id)


def on_task_name_received(message, project_id):
    user_id = message.chat.id
    task_name = message.text
    create_task(task_name, project_id, user_id)
    bot.send_message(user_id, "Задача успешно создана.", reply_markup=main_menu())


def display_tasks(message, project_id):
    user_id = message.chat.id
    tasks = get_tasks(project_id)

    if tasks:
        bot.send_message(user_id, "Задачи в проекте:")
        for task in tasks:
            task_id = task[0]
            task_title = task[1]

            markup = types.InlineKeyboardMarkup()
            manage_button = types.InlineKeyboardButton("🔧 Управление", callback_data=f"manage_task:{task_id}")
            markup.add(manage_button)

            bot.send_message(user_id, task_title, reply_markup=markup)
    else:
        bot.send_message(user_id, "В проекте нет задач.")


def add_message_workflow(message, project_id):
    user_id = message.chat.id
    msg = bot.send_message(user_id, "Введите текст сообщения:")
    bot.register_next_step_handler(msg, on_message_text_received, project_id)


def on_message_text_received(message, project_id):
    user_id = message.chat.id
    message_text = message.text
    add_message(bot, user_id, project_id, None, message_text, None)  # Добавьте параметр user_id здесь
    bot.send_message(user_id, "Сообщение успешно создано.")


def display_messages(message, project_id):
    user_id = message.chat.id
    messages = get_messages(project_id)

    if messages:
        bot.send_message(user_id, "Сообщения в проекте:")
        for msg in messages:
            message_id = msg[0]
            message_text = msg[1]

            markup = types.InlineKeyboardMarkup()
            manage_button = types.InlineKeyboardButton("🔧 Управление", callback_data=f"manage_message:{message_id}")
            markup.add(manage_button)

            bot.send_message(user_id, message_text, reply_markup=markup)
    else:
        bot.send_message(user_id, "В проекте нет сообщений.")


def create_microproject(message, task_id):
    user_id = message.from_user.id
    task = get_task_by_id(task_id)

    if not task or not is_user_in_project(user_id, task['project_id']):
        bot.send_message(user_id, "У вас нет доступа к этой задаче.")
        return

    # Здесь можно добавить логику для создания микропроекта на основе задачи,
    # например, назначение ответственных, добавление подзадач и т.д.
    pass


def manage_microproject(message, task_id):
    user_id = message.from_user.id
    task = get_task_by_id(task_id)

    if not task or not is_user_in_project(user_id, task['project_id']):
        bot.send_message(user_id, "У вас нет доступа к этому микропроекту.")
        return

    # Здесь можно добавить логику для управления микропроектом,
    # например, изменение статуса подзадач, назначение исполнителей, установка дедлайнов и т.д.
    pass


def set_deadline(message, task_id):
    user_id = message.from_user.id
    task = get_task_by_id(task_id)

    if not task or not is_user_in_project(user_id, task['project_id']):
        bot.send_message(user_id, "У вас нет доступа к этой задаче.")
        return

    bot.send_message(user_id, "Введите дедлайн для задачи (формат: YYYY-MM-DD):")

    @bot.message_handler(func=lambda m: True)
    def on_deadline_received(m):
        deadline = m.text
        try:
            set_task_deadline(task_id, deadline)
            bot.send_message(user_id, "Дедлайн успешно установлен.", reply_markup=main_menu())
        except ValueError:
            bot.send_message(user_id, "Ошибка: неверный формат даты. Попробуйте еще раз.")


def search(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Введите текст для поиска:")

    @bot.message_handler(func=lambda m: True)
    def on_search_query_received(m):
        search_query = m.text
        results = search_tasks_and_projects(user_id, search_query)

        if not results:
            bot.send_message(user_id, "По вашему запросу ничего не найдено.")
            return

        # Вывод результатов поиска
        for result in results:
            item_type = result['type']
            item_title = result['title']
            item_description = result['description']

            if item_type == 'task':
                task_id = result['id']
                # Здесь можно добавить инлайн кнопки для управления задачей, если это необходимо
                bot.send_message(user_id, f"Задача: {item_title}\n\n{item_description}")
            elif item_type == 'project':
                project_id = result['id']
                markup = types.InlineKeyboardMarkup()
                manage_button = types.InlineKeyboardButton("🔧 Управление", callback_data=f"manage_project:{project_id}")
                markup.add(manage_button)
                bot.send_message(user_id, f"Проект: {item_title}\n\n{item_description}", reply_markup=markup)


# ... (реализация остальных функций)

def process_media(message, project_id):
    if message.content_type == 'photo':
        media_type = 'photo'
        media_url = message.photo[-1].file_id
    elif message.content_type == 'video':
        media_type = 'video'
        media_url = message.video.file_id
    elif message.text == 'Пропустить':
        bot.send_message(message.chat.id, "Медиафайл не добавлен.")
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Шаг пропущен.", reply_markup=markup)
        return
    else:
        bot.send_message(message.chat.id, "Неверный формат медиафайла. Попробуйте еще раз.")
        return

    add_message(project_id, None, "Медиафайл", None, media_type, media_url)
    bot.send_message(message.chat.id, "Медиафайл добавлен.")


def display_node(call, node_id):
    user_id = call.message.chat.id
    node = get_node_by_id(node_id)
    message_text = node['title']
    if node['content']:
        message_text += "\n\n" + node['content']

    # Выводим сообщение и добавляем кнопку "Добавить сообщение"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Добавить сообщение", callback_data=f"add_message:{node_id}"))
    bot.send_message(user_id, message_text, parse_mode='HTML', reply_markup=markup)

    # Сохраняем информацию о добавлении сообщения для user_id
    adding_message_data[user_id] = (node['project_id'], node_id)

    # Отображаем дочерние сообщения
    child_nodes = get_nodes_by_project_id(node['project_id'], node['parent_id'])
    for child_node in child_nodes:
        title = child_node['title']
        if child_node['content']:
            title += "\n\n" + child_node['content']
        markup_child = types.InlineKeyboardMarkup()
        markup_child.add(types.InlineKeyboardButton(text=title, callback_data=f"open_node:{child_node['id']}"))
        bot.send_message(user_id, "", reply_markup=markup_child)


def display_node(call, node_id):
    user_id = call.message.chat.id
    node = get_node_by_id(node_id)

    if node is None:
        bot.send_message(user_id, "Узел не найден")
        return

    message_text = node['title']
    if node['content']:
        message_text += "\n\n" + node['content']

    # Выводим сообщение и добавляем кнопку "Добавить сообщение"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Добавить сообщение", callback_data=f"add_message:{node_id}"))
    bot.send_message(user_id, message_text, parse_mode='HTML', reply_markup=markup)

    # Отображаем дочерние сообщения
    child_nodes = get_nodes_by_project_id(node['project_id'], node['parent_id'])
    for child_node in child_nodes:
        title = child_node['title']
        if child_node['content']:
            title += "\n\n" + child_node['content']
        markup_child = types.InlineKeyboardMarkup()
        markup_child.add(types.InlineKeyboardButton(text=title, callback_data=f"open_node:{child_node['id']}"))
        bot.send_message(user_id, "", reply_markup=markup_child)

    # Отправляем сообщение с кнопками действий
    actions_markup = types.InlineKeyboardMarkup()

    if node['parent_id'] is not None:
        back_button = types.InlineKeyboardButton("🔙 Назад", callback_data=f"back_node:{node['id']}")
        actions_markup.add(back_button)

    close_button = types.InlineKeyboardButton("❌ Закрыть", callback_data="close_project")
    actions_markup.add(close_button)

    add_file_button = types.InlineKeyboardButton("📎 Добавить фото/видео",
                                                 callback_data=f"add_file:{node['id']}")
    actions_markup.add(add_file_button)

    main_menu_button = types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    actions_markup.add(main_menu_button)

    sent_msg = bot.send_message(user_id, "Выберите действие:", reply_markup=actions_markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("open_node:"))
def open_node_handler(call):
    node_id = int(call.data.split(":")[1])
    display_node(call, node_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("back_node:"))
def back_node_handler(call):
    node_id = int(call.data.split(":")[1])
    display_node(call, node_id, go_back=True)


@bot.callback_query_handler(func=lambda call: call.data == "add_file")
def add_file_handler(call):
    bot.answer_callback_query(call.id, "Функция добавления файла пока не реализована")


def process_message_text(message, project_id):
    # Здесь добавьте логику для обработки текстовых сообщений и вызова функции add_message
    # с соответствующими параметрами.
    # В данном примере, мы добавляем сообщение без родительского узла (parent_id=None).
    add_message(project_id, None, message.text, None)
    bot.send_message(message.chat.id, "Сообщение добавлено.")


@bot.message_handler(content_types=['photo', 'video'])
def handle_media_message(message):
    # Здесь добавьте логику для обработки медиафайлов и вызова функции add_message
    # с соответствующими параметрами.
    pass


adding_message_data = {}


def filter_add_message(call):
    return call.data.startswith("add_message:")


@bot.callback_query_handler(func=filter_add_message)
@bot.callback_query_handler(func=filter_add_message)
@bot.callback_query_handler(func=filter_add_message)
def add_message_handler(call):
    user_id = call.message.chat.id
    _, parent_id = call.data.split(":")
    adding_message_data[user_id] = (parent_id,)

    bot.send_message(user_id, "Введите текст нового сообщения:")


@bot.callback_query_handler(func=lambda call: call.data.startswith("manage_project:"))
def manage_project_handler(call):
    project_id = int(call.data.split(":")[1])
    manage_project(call.message, project_id)


@bot.message_handler(content_types=['text'])
def text_message_handler(message):
    user_id = message.chat.id
    content = message.text

    if user_id in adding_message_data:
        parent_id = adding_message_data[user_id][0]

        if parent_id != root_node['id']:
            node = get_node_by_id(parent_id)

            if node is not None:
                project_id = node['project_id']
                add_message(bot, user_id, project_id, parent_id, content)
                adding_message_data[user_id] = None
                bot.send_message(user_id, "Сообщение успешно создано.")
            else:
                bot.send_message(user_id, "Ошибка: родительский узел не найден. Пожалуйста, попробуйте еще раз.")
        else:
            bot.send_message(user_id,
                             "Ошибка: нельзя добавить сообщение к корневому узлу. Пожалуйста, выберите другой узел.")
    else:
        bot.send_message(user_id, "Я не понимаю эту команду. Воспользуйтесь кнопками для управления.")


# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
