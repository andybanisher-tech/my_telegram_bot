import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = "news_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            is_verified BOOLEAN DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            category_id INTEGER,
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, category_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS managers (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_companies (
            user_id INTEGER,
            company_code TEXT,
            company_name TEXT,
            selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, company_code),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_code TEXT,
            clicks INTEGER DEFAULT 0,
            unique_users INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(partner_code)
        )
    ''')

    # Добавляем категории по умолчанию только если таблица пуста
    cur.execute("SELECT COUNT(*) FROM categories")
    count = cur.fetchone()[0]
    if count == 0:
        default_categories = ['Спорт', 'Политика', 'IT', 'Культура']
        for cat in default_categories:
            try:
                cur.execute('INSERT INTO categories (name) VALUES (?)', (cat,))
            except Exception as e:
                logger.error(f"Ошибка добавления категории {cat}: {e}")
        logger.info("Добавлены категории по умолчанию")
    else:
        logger.info("Категории уже существуют, пропускаем добавление по умолчанию")

    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

# ---------- Функции для статистики ----------
def increment_user_counter():
    """Увеличивает счётчик уникальных пользователей (при каждом новом пользователе)."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO stats (partner_code, unique_users) VALUES ('total', 0)")
    cur.execute("UPDATE stats SET unique_users = unique_users + 1 WHERE partner_code = 'total'")
    conn.commit()
    conn.close()

def increment_click_counter(partner_code: str):
    """Увеличивает счётчик кликов по ссылкам акций для конкретного партнёра."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO stats (partner_code, clicks) VALUES (?, 0)", (partner_code,))
    cur.execute("UPDATE stats SET clicks = clicks + 1 WHERE partner_code = ?", (partner_code,))
    conn.commit()
    conn.close()

def get_stats():
    """Возвращает количество уникальных пользователей и кликов по каждому партнёру."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT partner_code, clicks, unique_users FROM stats ORDER BY partner_code")
    rows = cur.fetchall()
    conn.close()
    result = {}
    total_users = 0
    for row in rows:
        if row[0] == 'total':
            total_users = row[2] if row[2] else 0
        else:
            result[row[0]] = {'clicks': row[1] or 0, 'users': row[2] or 0}
    return {'total_users': total_users, 'partners': result}

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                (user_id, username, first_name))
    if cur.rowcount > 0:
        increment_user_counter()  # новый пользователь
    conn.commit()
    conn.close()

# ---------- Остальные функции (без изменений) ----------
def get_categories():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    cats = cur.fetchall()
    conn.close()
    return cats

def get_category_by_name(name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories WHERE name = ?", (name,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res else None

def get_category_by_id(cat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res else None

def add_category(name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Категория {name} уже существует")
        new_id = None
    finally:
        conn.close()
    return new_id

def rename_category(old_name, new_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE categories SET name = ? WHERE name = ?", (new_name, old_name))
        conn.commit()
        success = cur.rowcount > 0
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def delete_category(name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM categories WHERE name = ?", (name,))
        conn.commit()
        success = cur.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка удаления категории {name}: {e}")
        success = False
    finally:
        conn.close()
    return success

# Функции для users и телефонов
def get_user_phone(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT phone FROM users WHERE user_id = ?', (user_id,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res else None

def update_user_phone(user_id, phone):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET phone = ? WHERE user_id = ?', (phone, user_id))
    conn.commit()
    conn.close()

def get_user_verification_status(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT is_verified FROM users WHERE user_id = ?', (user_id,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res else 0

def mark_user_verified(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET is_verified = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Подписки
def get_user_subscriptions(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT category_id FROM subscriptions WHERE user_id = ?', (user_id,))
    subs = [row[0] for row in cur.fetchall()]
    conn.close()
    return subs

def subscribe(user_id, category_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR IGNORE INTO subscriptions (user_id, category_id) VALUES (?, ?)',
                    (user_id, category_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка подписки: {e}")
    finally:
        conn.close()

def unsubscribe(user_id, category_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM subscriptions WHERE user_id = ? AND category_id = ?',
                    (user_id, category_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка отписки: {e}")
    finally:
        conn.close()

def unsubscribe_all(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_users_by_category(category_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM subscriptions WHERE category_id = ?', (category_id,))
    users = [row[0] for row in cur.fetchall()]
    conn.close()
    return users

def get_users_by_categories(category_ids):
    if not category_ids:
        return []
    placeholders = ','.join(['?'] * len(category_ids))
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    query = f"""
        SELECT DISTINCT user_id FROM subscriptions
        WHERE category_id IN ({placeholders})
    """
    cur.execute(query, category_ids)
    users = [row[0] for row in cur.fetchall()]
    conn.close()
    return users

def get_category_subscribers_count():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, COUNT(s.user_id)
        FROM categories c
        LEFT JOIN subscriptions s ON c.id = s.category_id
        GROUP BY c.id
        ORDER BY c.name
    """)
    result = dict(cur.fetchall())
    conn.close()
    return result

# Администраторы и менеджеры
def add_admin(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR REPLACE INTO admins (user_id, name) VALUES (?, ?)', (user_id, name))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка добавления админа: {e}")
    finally:
        conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_db_admins():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id, name FROM admins')
    rows = cur.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1]} for row in rows]

def add_manager(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR REPLACE INTO managers (user_id, name) VALUES (?, ?)', (user_id, name))
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка добавления менеджера: {e}")
    finally:
        conn.close()

def remove_manager(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM managers WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_db_managers():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id, name FROM managers')
    rows = cur.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1]} for row in rows]

# Компании пользователя
def save_user_companies(user_id, companies):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM user_companies WHERE user_id = ?', (user_id,))
    for comp in companies:
        cur.execute('''
            INSERT INTO user_companies (user_id, company_code, company_name)
            VALUES (?, ?, ?)
        ''', (user_id, comp['code'], comp['name']))
    conn.commit()
    conn.close()

def get_user_companies(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT company_code, company_name FROM user_companies WHERE user_id = ?', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"code": row[0], "name": row[1]} for row in rows]