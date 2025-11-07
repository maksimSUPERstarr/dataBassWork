#!/usr/bin/env python3
import sys
import logging
from PyQt6.QtWidgets import QApplication

from utils import setup_logging


def main():
    """Главная функция приложения"""
    # Настраиваем логирование
    logger = setup_logging()

    try:
        logger.info("=" * 60)
        logger.info("Запуск приложения 'Платформа для A/B тестирования'")
        logger.info("=" * 60)

        # Создаем приложение
        app = QApplication(sys.argv)
        app.setApplicationName("A/B Testing Platform")
        app.setApplicationVersion("1.0")

        # Импортируем и создаем главное окно
        from windows import MainWindow
        window = MainWindow()
        window.show()

        # Запускаем приложение
        return_code = app.exec()

        logger.info("Приложение завершено корректно")
        return return_code

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())