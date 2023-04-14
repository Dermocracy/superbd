# database.py

import psycopg2


# Создайте подключение к базе данных PostgreSQL
host = "localhost"
user = "dbuser"
password = "dbpassword"
dbname = "dbss"

connection = psycopg2.connect(
    host=host,
    user=user,
    password=password,
    dbname=dbname
)

# Создайте курсор для выполнения операций с базой данных
cursor = connection.cursor()

def init_db():
    # Создайте таблицы базы данных
    create_users_table()
    create_projects_table()
    create_tasks_table()
    create_databases_table()
    create_user_projects_table()


def create_users_table():
    query = '''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        username VARCHAR(255) UNIQUE,
        first_name VARCHAR(255),
        last_name VARCHAR(255)
    )
    '''
    cursor.execute(query)
    connection.commit()


def create_projects_table():
    query = '''
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        FOREIGN KEY (owner_id) REFERENCES users (telegram_id) ON DELETE CASCADE
    )
    '''
    cursor.execute(query)
    connection.commit()


def create_tasks_table():
    query = '''
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        deadline TIMESTAMP,
        project_id INTEGER NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    '''
    cursor.execute(query)
    connection.commit()

def create_databases_table():
    query = '''
    CREATE TABLE IF NOT EXISTS custom_databases (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        owner_id INTEGER NOT NULL,
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    '''
    cursor.execute(query)
    connection.commit()

def create_user_projects_table():
    query = '''
    CREATE TABLE IF NOT EXISTS user_projects (
        user_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        role VARCHAR(50) NOT NULL,
        PRIMARY KEY (user_id, project_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    '''
    cursor.execute(query)
    connection.commit()

# Functions for Users table
def add_user(telegram_id, username, first_name, last_name):
    query = '''
    INSERT INTO users (telegram_id, username, first_name, last_name)
    VALUES (%s, %s, %s, %s)
    '''
    cursor.execute(query, (telegram_id, username, first_name, last_name))
    connection.commit()

def get_user_by_tg_id(telegram_id):
    query = '''
    SELECT * FROM users WHERE telegram_id = %s
    '''
    cursor.execute(query, (telegram_id,))
    return cursor.fetchone()

def update_user(user_id, new_username, new_first_name, new_last_name):
    query = '''
    UPDATE users SET username = %s, first_name = %s, last_name = %s
    WHERE id = %s
    '''
    cursor.execute(query, (new_username, new_first_name, new_last_name, user_id))
    connection.commit()

def delete_user(user_id):
    query = '''
    DELETE FROM users WHERE id = %s
    '''
    cursor.execute(query, (user_id,))
    connection.commit()

# Functions for Projects table
def create_project(title, description, user_id):
    query = "SELECT id FROM projects WHERE title=%s AND description=%s"
    cursor.execute(query, (title, description))
    result = cursor.fetchone()

    if result is not None:
        id = result[0]
    else:
        query = '''
        INSERT INTO projects (title, description)
        VALUES (%s, %s);
        '''
        cursor.execute(query, (title, description))
        id = cursor.fetchone()[0]
    

    query = "SELECT id FROM users WHERE telegram_id = %s"
    cursor.execute(query, (user_id,))
    arUser = cursor.fetchone()
    if arUser is not None:
        userId = arUser[0]
    else:
        print("123")
        # ЗДЕСЬ БУДЕТ ОБРАБОТЧИК ОШИБКИ



    role = "ADMIN"
    query = '''
    INSERT INTO user_projects (user_id, project_id, role)
    VALUES (%s, %s, %s);
    '''
    print(user_id, id, role,)
    cursor.execute(query, (userId, id, role))
   
    connection.commit()

def get_projects_by_owner_id(owner_id):
    query = '''
    SELECT * FROM projects WHERE owner_id = %s
    '''
    cursor.execute(query, (owner_id,))
    return cursor.fetchall()

def get_project(project_id):
    query = '''
    SELECT * FROM projects WHERE id = %s
    '''
    cursor.execute(query, (project_id,))
    return cursor.fetchone()

def get_project_by_id(project_id):
    query = '''
    SELECT * FROM projects WHERE id = %s
    '''
    cursor.execute(query, (project_id,))
    result = cursor.fetchone()
    if result is not None:
        return {
            'id': result[0],
            'title': result[1],
            'description': result[2],
            'owner_id': result[3]
        }
    else:
        return None

def update_project(project_id, new_title, new_description):
    query = '''
    UPDATE projects SET title = %s, description = %s
    WHERE id = %s
    '''
    cursor.execute(query, (new_title, new_description, project_id))
    connection.commit()

def delete_project(project_id):
    query = '''
    DELETE FROM projects WHERE id = %s
    '''
    cursor.execute(query, (project_id,))
    connection.commit()

def is_user_in_project(user_id, project_id):
    query = '''
    SELECT * FROM user_projects WHERE user_id = %s AND project_id = %s
    '''
    cursor.execute(query, (user_id, project_id))
    result = cursor.fetchone()
    return result is not None



# Functions for Tasks table
def create_task(title, description, deadline, project_id):
    query = '''
    INSERT INTO tasks (title, description, deadline, project_id)
    VALUES (%s, %s, %s, %s)
    '''
    cursor.execute(query, (title, description, deadline, project_id))
    connection.commit()

def get_task(task_id):
    query = '''
    SELECT * FROM tasks WHERE id = %s
    '''
    cursor.execute(query, (task_id,))
    return cursor.fetchone()

def update_task(task_id, new_title, new_description, new_deadline):
    query = '''
    UPDATE tasks SET title = %s, description = %s, deadline = %s
    WHERE id = %s
    '''
    cursor.execute(query, (new_title, new_description, new_deadline, task_id))
    connection.commit()

def delete_task(task_id):
    query = '''
    DELETE FROM tasks WHERE id = %s
    '''
    cursor.execute(query, (task_id,))
    connection.commit()

# Functions for Custom Databases table
def create_custom_database(title, description, owner_id):
    query = '''
    INSERT INTO custom_databases (title, description, owner_id)
    VALUES (%s, %s, %s)
    '''
    cursor.execute(query, (title, description, owner_id))
    connection.commit()

def search_tasks_and_projects(user_id, search_query):
    # Реализуйте логику поиска задач и проектов здесь
    return []
