#!/usr/bin/env python3
import sys
import logging
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from utils import setup_logging, show_error_message
from windows import MainWindow


def handle_exception(exc_type, exc_value, exc_traceback):
    """Глобальный обработчик необработанных исключений."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    # Форматируем сообщение об ошибке
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # Логируем ошибку
    logger.error(f"Необработанное исключение: {error_message}")

    # Показываем сообщение об ошибке (если есть QApplication)
    if QApplication.instance() is not None:
        show_error_message(
            None,
            "Критическая ошибка",
            f"Произошла критическая ошибка:\n{str(exc_value)}\n\nПодробности в лог-файле."
        )


def main():
    """
    Главная функция приложения.

    Инициализирует и запускает приложение с графическим интерфейсом.
    """
    try:
        # Настраиваем глобальный обработчик исключений
        sys.excepthook = handle_exception

        # Создаем экземпляр QApplication
        app = QApplication(sys.argv)

        # Настраиваем свойства приложения
        app.setApplicationName("A/B Testing Platform")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("Your Team")
        app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        # Устанавливаем стиль Fusion для кроссплатформенного внешнего вида
        app.setStyle("Fusion")

        # Создаем и настраиваем главное окно
        logger.info("Создание главного окна приложения")
        window = MainWindow()

        # Устанавливаем заголовок окна (дублируем для надежности)
        window.setWindowTitle("Платформа для A/B тестирования рекомендательных систем v1.0")

        # Показываем главное окно
        logger.info("Отображение главного окна")
        window.show()

        # Запускаем главный цикл обработки событий
        logger.info("Запуск главного цикла обработки событий")
        return_code = app.exec()

        # Логируем завершение приложения
        logger.info(f"Приложение завершено с кодом возврата: {return_code}")

        return return_code

    except Exception as e:
        # Обрабатываем ошибки инициализации
        error_msg = f"Ошибка при запуске приложения: {str(e)}"
        print(error_msg)
        logging.critical(error_msg)
        return 1


if __name__ == "__main__":
    """
    Точка входа в приложение.

    Этот блок кода выполняется только при прямом запуске файла,
    а не при импорте как модуля.
    """
    # Настраиваем логирование
    logger = setup_logging()

    # Логируем запуск приложения
    logger.info("=" * 60)
    logger.info("Запуск приложения 'Платформа для A/B тестирования'")
    logger.info("=" * 60)

    try:
        # Запускаем главную функцию
        exit_code = main()

        # Логируем завершение работы
        logger.info("Приложение корректно завершило работу")

    except KeyboardInterrupt:
        # Обрабатываем прерывание пользователем (Ctrl+C)
        logger.info("Приложение прервано пользователем")
        exit_code = 0

    except Exception as e:
        # Обрабатываем критические ошибки
        error_msg = f"Критическая ошибка: {str(e)}"
        logger.critical(error_msg)
        print(error_msg)
        exit_code = 1

    finally:
        # Завершаем работу приложения
        logger.info("=" * 60)
        logger.info("Завершение работы приложения")
        logger.info("=" * 60)
        sys.exit(exit_code)

