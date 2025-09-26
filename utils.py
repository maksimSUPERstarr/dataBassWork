import logging
import re
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QDate

logger = logging.getLogger(__name__)

def setup_logging():
    """Настраивает систему логирования для этого приложения"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log", encoding='UTF8'),  # Запись в файл
            logging.StreamHandler()  # Вывод в консоль (без параметров!)
        ]
    )
    return logging.getLogger()

def validate_experiment_name(name):
    """Проверяет корректность названия проекта"""
    if not name or not name.strip():
        return False, "Название эксперимента не может быть пустым"
    if len(name.strip()) > 100:
        return False, "Название эксперимента не может содержать больше ста символов"
    if not re.match(r'^[a-zA-Zа-яА-Я0-9_\- ]+$', name):
        return False, "В названии эксперимента содержаться недопустимые символы"
    return True, ""

def validate_metrics(clicks, impressions):
    if clicks < 0:
        return False, "Кол-во кликов должно быть больше нуля"
    if impressions < 0:
        return False, "Кол-во просмотров должно быть больше нуля"
    if clicks > impressions:
        return False, "Кол-во кликов не может превышать кол-во просмотров"
    return True, ""

def validate_success_rate(rate):
    """"проверяет корректность процента CTR"""
    if rate < 0.01 or rate > 1.0:
        return False, "Процент успеха эксперимента должен находится в диапазоне 0.01-1.0"
    return True, ""

def calculate_ctr(clicks, impressions):
    """Вычисляет Click-Through Rate в процентах"""
    if impressions <= 0:
        return 0.0
    return (clicks/ impressions) * 100

def format_date(date_obj, format_str="%Y-%m-%d %H:%M"):
    """Транспортирует объект даты в формат строки"""
    if not date_obj:
        return ""
    return date_obj.strftime(format_str)

def parse_date(date_str, format_str="%Y-%m-%d %H:%M"):
    """Парсит строку с данными о времени в объект datatime"""
    try:
        return datetime.strptime(date_str, format_str)
    except (ValueError, TypeError):
        return None

def qdate_to_datetime(qdate):
    """Преобразует QDate в datetime"""
    if not qdate or not qdate.is_valid():
        return None
    return datetime(qdate.year(), qdate.month(), qdate.day())

def show_error_message(parent, title, message):
    """Показывает сообщение об ошибке"""
    logger.error(f"{title}: {message}")
    QMessageBox.critical(parent, title, message)

def show_info_message(parent, title, message):
    """Показывает информационное сообщение"""
    logger.info(f"{title}: {message}")
    QMessageBox.information(parent, title, message)

def show_warning_message(parent, title, message):
    """Показывает предупреждающее сообщение"""
    logger.warning(f"{title}: {message}")
    QMessageBox.warning(parent, title, message)

def validate_experiment_data(name, clicks, impressions, success_rate):
    """проверяет все данные эксперимента на валидность"""
    is_valid, error_msg = validate_experiment_name(name)
    if not is_valid:
        return False, error_msg
    is_valid, error_msg = validate_metrics(clicks, impressions)
    if not is_valid:
        return False, error_msg
    is_valid, error_msg = validate_success_rate(success_rate)
    if not is_valid:
        return False, error_msg
    return True, ""
