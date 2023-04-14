# bot.py
import telebot
from telebot import types
import psycopg2
from datetime import datetime

from database import (add_user, get_user_by_tg_id, update_user, delete_user,
                      create_project, get_project, update_project, delete_project,
                      create_task, get_task, update_task, delete_task,
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

def create_project_workflow(user_id):  # Изменено название функции
    bot.send_message(user_id, "Введите название проекта:")

    @bot.message_handler(func=lambda m: True)
    def on_project_name_received(m):
        project_name = m.text
        bot.send_message(user_id, "Введите описание проекта:")

        @bot.message_handler(func=lambda m: True)
        def on_project_description_received(m):
            project_description = m.text
            database.create_project(project_name, project_description, user_id)  # Используйте функцию create_project из модуля database
            bot.send_message(user_id, "Проект успешно создан.", reply_markup=main_menu())



def get_projects_for_user(user_id):
    user_projects = get_projects_by_owner_id(user_id)
    return user_projects

def create_default_project(user_id):
    default_project_title = 'Основной проект'
    default_project_description = 'Этот проект содержит все возможные функции бота.'
    create_project(default_project_title, default_project_description, user_id)




def display_projects(message):
    user_id = message.from_user.id
    projects = get_projects_for_user(user_id)

    if not projects:
        create_default_project(user_id)
        projects = get_projects_for_user(user_id)
        bot.send_message(user_id, "Мы создали для вас основной проект, который содержит все возможные функции бота.")

    for project in projects:
        project_id = project[0]
        project_title = project[1]

        markup = types.InlineKeyboardMarkup()
        manage_button = types.InlineKeyboardButton("🔧 Управление", callback_data=f"manage_project:{project_id}")
        markup.add(manage_button)

        bot.send_message(user_id, project_title, reply_markup=markup)


def manage_project(message, project_id):
    user_id = message.chat.id   
    project = get_project_by_id(project_id)

    if not project or not is_user_in_project(user_id, project_id):
        print([project, user_id, project_id, not project, not is_user_in_project(user_id, project_id)])
        bot.send_message(user_id, "У вас нет доступа к управлению этим проектом.")
        return
    bot.send_message(user_id, "все ок.")

    # Здесь можно добавить логику для управления проектом,
    # например, добавление, удаление и изменение ролей участников, создание и удаление задач и т.д.
    pass

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
    update_user_role_in_project(project_id, user_id, new_role)


# Обработчики событий для инлайн кнопок

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






def create_task(message, project_id):
    user_id = message.from_user.id

    if not is_user_in_project(user_id, project_id):
        bot.send_message(user_id, "У вас нет доступа к этому проекту.")
        return

    bot.send_message(user_id, "Введите название задачи:")

    @bot.message_handler(func=lambda m: True)
    def on_task_name_received(m):
        task_name = m.text
        bot.send_message(user_id, "Введите описание задачи:")

        @bot.message_handler(func=lambda m: True)
        def on_task_description_received(m):
            task_description = m.text
            create_task_in_db(user_id, project_id, task_name, task_description)
            bot.send_message(user_id, "Задача успешно создана.", reply_markup=main_menu())

def manage_task(message, task_id):
    user_id = message.from_user.id
    task = get_task_by_id(task_id)

    if not task or not is_user_in_project(user_id, task['project_id']):
        bot.send_message(user_id, "У вас нет доступа к управлению этой задачей.")
        return

    # Здесь можно добавить логику для управления задачей,
    # например, изменение статуса, назначение исполнителя, установка дедлайна и т.д.
    pass

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

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)

