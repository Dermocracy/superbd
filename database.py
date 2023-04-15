# database.py

import psycopg2


# Создайте подключение к базе данных PostgreSQL
host = "localhost"
user = "dbuser"
password = "dbpassword"
dbname = "dbsss"

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
    create_nodes_table()


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

def create_nodes_table():
    query = '''
    CREATE TABLE IF NOT EXISTS nodes (
        id SERIAL PRIMARY KEY,
        project_id INT REFERENCES projects (id),
        parent_id INT REFERENCES nodes (id),
        title VARCHAR(255) NOT NULL,
        content TEXT,
        media_type VARCHAR(50), 
        media_url VARCHAR(255)
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
        owner_id INTEGER NOT NULL,
        FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
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

def add_user_to_project_in_db(project_id, user_id, role):
    query = '''
    INSERT INTO user_projects (user_id, project_id, role)
    VALUES (%s, %s, %s);
    '''
    cursor.execute(query, (user_id, project_id, role))
    connection.commit()

def remove_user_from_project_in_db(project_id, user_id):
    query = '''
    DELETE FROM user_projects WHERE user_id = %s AND project_id = %s;
    '''
    cursor.execute(query, (user_id, project_id))
    connection.commit()


def update_user_role_in_project_in_db(project_id, user_id, new_role):
    query = '''
    UPDATE user_projects SET role = %s
    WHERE user_id = %s AND project_id = %s
    '''
    cursor.execute(query, (new_role, user_id, project_id))
    connection.commit()


def get_user_by_tg_id(telegram_id):
    query = '''
    SELECT * FROM users WHERE telegram_id = %s
    '''
    try:
        cursor.execute(query, (telegram_id,))
        result = cursor.fetchone()
    except Exception as e:
        print("Ошибка при выполнении запроса:", e)
        connection.rollback()
    else:
        connection.commit()
        return result


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
    # Получаем внутренний ID пользователя
    query = "SELECT id FROM users WHERE telegram_id = %s"
    cursor.execute(query, (user_id,))
    arUser = cursor.fetchone()
    if arUser is not None:
        internal_user_id = arUser[0]
    else:
        print("Ошибка: пользователь не найден")
        return

    # Создаем проект
    query = '''
    INSERT INTO projects (title, description, owner_id)
    VALUES (%s, %s, %s) RETURNING id;
    '''
    cursor.execute(query, (title, description, internal_user_id))
    project_id = cursor.fetchone()[0]

    # Добавляем связь между пользователем и проектом с ролью "ADMIN"
    role = "ADMIN"
    query = '''
    INSERT INTO user_projects (user_id, project_id, role)
    VALUES (%s, %s, %s);
    '''
    cursor.execute(query, (internal_user_id, project_id, role))

    connection.commit()

def get_projects_by_owner_id(user_id):
    query = '''
    SELECT * FROM user_projects WHERE user_id = %s
    '''
    cursor.execute(query, (user_id,))
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

def is_user_in_project(telegram_id, project_id):
    # Получаем внутренний ID пользователя
    query = "SELECT id FROM users WHERE telegram_id = %s"
    cursor.execute(query, (telegram_id,))
    arUser = cursor.fetchone()
    if arUser is not None:
        internal_user_id = arUser[0]
    else:
        print("Ошибка: пользователь не найден")
        return False

    # Проверяем наличие пользователя в проекте
    query = '''
    SELECT * FROM user_projects WHERE user_id = %s AND project_id = %s
    '''
    cursor.execute(query, (internal_user_id, project_id))
    result = cursor.fetchone()
    return result is not None

def create_node(project_id, parent_id, title, content=None, media_type=None, media_url=None):
    query = '''
    INSERT INTO nodes (project_id, parent_id, title, content, media_type, media_url)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    '''
    cursor.execute(query, (project_id, parent_id, title, content, media_type, media_url))
    conn.commit()
    return cursor.fetchone()[0]


def get_nodes_by_project_id(project_id, parent_id=None):
    query = '''
    SELECT * FROM nodes WHERE project_id = %s AND parent_id = %s
    '''
    cursor.execute(query, (project_id, parent_id))
    result = cursor.fetchall()
    nodes = []

    for row in result:
        nodes.append({
            'id': row[0],
            'project_id': row[1],
            'parent_id': row[2],
            'title': row[3],
            'content': row[4],
            'media_type': row[5],
            'media_url': row[6]
        })

    return nodes



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

def get_root_node(project_id):
    query = "SELECT * FROM nodes WHERE project_id = %s AND parent_id IS NULL"
    cursor.execute(query, (project_id,))
    node = cursor.fetchone()
    if node:
        return {"id": node[0], "title": node[1], "content": node[2], "project_id": node[3], "parent_id": node[4]}
    else:
        return None
