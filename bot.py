# bot.py
import telebot
from telebot import types
import psycopg2
from datetime import datetime
import logging
sent_messages = []


from database import (add_user, get_user_by_tg_id, update_user, delete_user,
                      create_project,add_user_to_project_in_db, remove_user_from_project_in_db, update_user_role_in_project_in_db, get_project, update_project, delete_project,
                      create_task, get_root_node, get_task, update_task, delete_task,
                      create_custom_database,get_projects_by_owner_id, get_project_by_id, is_user_in_project, search_tasks_and_projects, cursor)
import database

API_TOKEN = '6054540829:AAHxxfRyImxaWZQPSWIL5B5zHyD275WbWK4'
bot = telebot.TeleBot(API_TOKEN)
bot_id = bot.get_me().id


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
#123
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

def get_projects_for_user(user_id):
    query = '''
    SELECT projects.id, projects.title
    FROM projects
    INNER JOIN user_projects ON projects.id = user_projects.project_id
    INNER JOIN users ON user_projects.user_id = users.id
    WHERE users.telegram_id = %s
    '''
    cursor.execute(query, (user_id,))
    return cursor.fetchall()


def create_default_project(user_id):
    default_project_title = 'Основной проект'
    default_project_description = 'Этот проект содержит все возможные функции бота.'
    create_project(default_project_title, default_project_description, user_id)

def display_projects(message):
    global sent_messages  # добавьте эту строку в начало функции

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

            markup = types.InlineKeyboardMarkup()
            open_project_button = types.InlineKeyboardButton("📂 Открыть проект", callback_data=f"open_project:{project_id}")
            markup.add(open_project_button)

            sent_msg = bot.send_message(user_id, project_title, reply_markup=markup)
            sent_messages.append(sent_msg.message_id)  # исправьте эту строку

    # Добавляем кнопку создания нового проекта после списка существующих проектов
    create_project_markup = types.InlineKeyboardMarkup()
    create_project_button = types.InlineKeyboardButton("➕ Создать проект", callback_data="create_project")
    create_project_markup.add(create_project_button)
    create_project_msg = bot.send_message(user_id, "Создать новый проект:", reply_markup=create_project_markup)
    sent_messages.append(create_project_msg.message_id)  # исправьте эту строку


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
        display_node(call, root_node['id'])

        # Отправляем сообщение с кнопками действий
        actions_markup = types.InlineKeyboardMarkup(row_width=1)
        add_task_button = types.InlineKeyboardButton("➕ Добавить задачу", callback_data=f"add_task:{project_id}")
        add_message_button = types.InlineKeyboardButton("📝 Добавить сообщение", callback_data=f"add_message:{project_id}")
        close_button = types.InlineKeyboardButton("❌ Закрыть", callback_data=f"close_project:{project_id}")

        actions_markup.add(add_task_button, add_message_button, close_button)

        actions_msg = bot.send_message(user_id, "Выберите действие:", reply_markup=actions_markup)
        sent_messages.append(actions_msg.message_id)  # добавьте эту строку

@bot.callback_query_handler(func=lambda call: call.data.startswith("close_project:"))
def close_project_handler(call):
    project_id = int(call.data.split(":")[1])
    close_project(call, project_id)

def close_project(call, project_id):
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_message"))
def add_message_handler(call):
    project_id = int(call.data.split(":")[1])
    # Здесь добавьте код для добавления сообщения и обновления узла


@bot.callback_query_handler(func=lambda call: call.data.startswith('open_project:'))
def open_project_handler(call):
    project_id = int(call.data.split(':')[1])
    open_project(call, project_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    # Разбираем данные callback
    data = call.data.split(':')
    action, value = data[0], data[1]

    user_id = call.message.chat.id

    # Проверяем, является ли получатель сообщения ботом
    if not call.from_user.is_bot:
        # Выполняем действие в зависимости от callback_data
        if action == "manage_project":
            project_id = int(value)
            manage_project(call.message, project_id)
        # ... (обработка остальных инлайн кнопок)





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
    create_message(message_text, project_id, user_id)
    bot.send_message(user_id, "Сообщение успешно создано.", reply_markup=main_menu())

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

def display_node(call, node_id, go_back=False):
    global sent_messages

    user_id = call.from_user.id
    node = get_node_by_id(node_id)

    if go_back:
        parent_node = get_node_by_id(node['parent_id'])
        node_id = parent_node['id']

    # Удаляем предыдущие сообщения
    for message_id in sent_messages:
        try:
            bot.delete_message(user_id, message_id)
        except Exception as e:
            print(f"Error deleting message: {e}")

    sent_messages = []

    if node is not None:
        title = f"📁 {node['title']}"
        if node['content']:
            title += f"\n\n{node['content']}"

        # Отправляем сообщение с информацией о текущем узле
        sent_msg = bot.send_message(user_id, title)
        sent_messages.append(sent_msg.message_id)

        # Отправляем сообщение с кнопками действий
        actions_markup = types.InlineKeyboardMarkup()

        child_nodes = get_nodes_by_project_id(node['project_id'], parent_id=node['id'])

        for child_node in child_nodes:
            button = types.InlineKeyboardButton(child_node['title'], callback_data=f"open_node:{child_node['id']}")
            actions_markup.add(button)

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
            sent_messages.append(sent_msg.message_id)
        else:
            bot.answer_callback_query(call.id, "Проект не найден")

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


# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)

