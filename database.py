import sys
import os
import psycopg2
import logging
from models import Experiment

sys.stdout.reconfigure(encoding='UTF8')
sys.stderr.reconfigure(encoding='UTF8')
os.environ["PYTHONUTF8"] = "1"

def get_connection():
    """Создает и возвращает подключение к БД"""
    conn = psycopg2.connect(
        host="localhost",
        database="ai_experiments",
        user="postgres",
        password="ShubinSQL228"
    )
    conn.set_client_encoding(' UTF8')
    cursor = conn.cursor()
    cursor.execute("SET client_encoding = 'UTF8';")
    cursor.close()
    return conn

def create_tables():
    """Создает таблицы в базе данных если они не существуют"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Явно устанавливаем кодировку
        cursor.execute("SET CLIENT_ENCODING TO 'UTF8';")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                is_active BOOLEAN,
                user_count INTEGER,
                success_rate REAL,
                impressions INTEGER,
                clicks INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("Tables created successfully!")

    except Exception as e:
        if conn:
            conn.rollback()  # Откатываем транзакцию при ошибке
        print(f"Error: {str(e)}")
        raise
    finally:
        # Всегда закрываем соединение
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_experiment(name, is_active, user_count, success_rate, clicks, impressions):
    """Добавляет новый эксперимент в базу данных"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO experiments (name, is_active, user_count, success_rate, clicks, impressions)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, is_active, user_count, success_rate, clicks, impressions))  # Правильный порядок

        new_id = cursor.fetchone()[0]
        conn.commit()
        logging.info(f"Добавлен новый эксперимент: {name} (ID: {new_id})")
        return new_id
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Ошибка при добавлении эксперимента: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_experiments():
    """Получает все эксперименты из базы данных как объекты Experiment"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SET client_encoding TO 'UTF8';")

        cursor.execute("""
            SELECT id, name, is_active, user_count, success_rate, impressions, clicks, created_at
            FROM experiments
            ORDER BY created_at DESC
        """)

        columns = [desc[0] for desc in cursor.description]
        experiments_list = []

        for row in cursor.fetchall():
            # Правильный вызов метода
            experiment = Experiment.from_database_row(row, columns)
            experiments_list.append(experiment)

        cursor.close()
        conn.close()

        logging.info(f"Получено {len(experiments_list)} экспериментов")
        return experiments_list

    except Exception as e:
        logging.error(f"Ошибка при получении экспериментов: {str(e)}")
        raise

def update_experiment(experiment_id, name=None, is_active=None, user_count=None,
                      success_rate=None, impressions=None, clicks=None):
    """Обновляет данные эксперимента"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Безопасное формирование запроса
        update_fields = []
        values = []
        field_mapping = {
            'name': name,
            'is_active': is_active,
            'user_count': user_count,
            'success_rate': success_rate,
            'impressions': impressions,
            'clicks': clicks
        }

        for field, value in field_mapping.items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)

        if not update_fields:
            logging.warning("Не указано ни одного поля для обновления")
            return False

        values.append(experiment_id)

        # Безопасное выполнение запроса
        query = f"UPDATE experiments SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, values)

        conn.commit()
        logging.info(f"Обновлен эксперимент ID: {experiment_id}")
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Ошибка при обновлении эксперимента: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_experiment(experiment_id):
    """Удаляет эксперимент по ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM experiments WHERE id = %s", (experiment_id,))

        conn.commit()
        cursor.close()
        conn.close()

        logging.info(f"Удален эксперимент ID: {experiment_id}")
        return True

    except Exception as e:
        logging.error(f"Ошибка при удалении эксперимента: {str(e)}")
        raise

def get_experiment_by_id(experiment_id):
    """Получает эксперимент по его ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, is_active, user_count, success_rate, impressions, clicks, created_at
            FROM experiments
            WHERE id = %s
        """, (experiment_id,))

        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row:
            experiment = Experiment.from_database_row(row, columns)
            logging.info(f"Получен эксперимент ID: {experiment_id}")
            return experiment
        else:
            logging.warning(f"Эксперимент с ID {experiment_id} не найден")
            return None

    except Exception as e:
        logging.error(f"Ошибка при получении эксперимента: {str(e)}")
        raise

# Проверяем подключение и создаем таблицы
if __name__ == "__main__":
    try:
        create_tables()
        print("Таблицы успешно созданы!")
    except Exception as e:
        print(f"Ошибка: {e}")
