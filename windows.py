import logging
from PyQt6.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QWidget,
                             QMessageBox, QLabel, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTextEdit, QDialog)
from PyQt6.QtCore import Qt
from database import create_tables, get_all_experiments
from dialogs import AddDataDialog
from DataView import DataViewWindow

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

class LogsWindows(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр логов")
        self.setGeometry(200, 200, 800, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.refresh_btn = QPushButton("Обновить логи")
        self.refresh_btn.clicked.connect(self.load_logs)
        layout.addWidget(self.refresh_btn)

        self.load_logs()
        logger.info("Окно просмотра логов инициализировано")

    def load_logs(self):
        """Загружает и отображает логи из файла"""
        try:
            with open("app.log", "r", encoding="utf-8") as log_file:
                logs = "".join(log_file.readlines())
            self.log_text.setPlainText(logs)
            logger.info("Логи загружены в окно просмотра")
        except Exception as e:
            error_msg = f"Ошибка при чтении логов: {str(e)}"
            logger.error(error_msg)
            self.log_text.setPlainText(error_msg)

    def open_logs_windows(self):
        """Открывает окно просмотра логов"""
        self.logs_window = LogsWindows(self)
        print(f"Атрибуты объекта: {dir(self.logs_window)}")  # ← отладка
        self.logs_window.show()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Платформа для A/B тестирования рекомендательных систем")
        self.setGeometry(100, 100, 600, 400)
        # создаем центральный виджет и компоновку
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # добавляем заголовок
        title_label = QLabel("Платформа для A/B тестирования рекомендательных систем")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px")

        # создаем кнопочки
        self.create_tables_btn = QPushButton("Создать схему и таблицу")
        self.add_data_btn = QPushButton("Внести данные")
        self.show_data_btn = QPushButton("Показать данные")
        self.view_logs_btn = QPushButton("Изучить логи")

        # подключаем обработчик событий
        self.create_tables_btn.clicked.connect(self.create_tables)
        self.add_data_btn.clicked.connect(self.open_add_data_dialog)
        self.show_data_btn.clicked.connect(self.open_show_data_window)
        self.view_logs_btn.clicked.connect(self.open_logs_windows)

        # добавляем кнопки в компоновку
        layout.addWidget(self.create_tables_btn)
        layout.addWidget(self.add_data_btn)
        layout.addWidget(self.show_data_btn)
        layout.addWidget(self.view_logs_btn)

        # заполним пустое пространство между виджетами
        layout.addStretch()
        # настройка статусной строки
        self.statusBar().showMessage("Готово к работе")
        # логируем создание окна
        logger.info("Главное окно приложения инициализировано")

    def create_tables(self):
        """Создает таблицы в базе данных"""
        try:
            create_tables()
            self.statusBar().showMessage("Таблицы успешно созданы")
            logger.info("Таблицы базы данных успешно созданы")
            QMessageBox.information(self,"Успех", "Таблицы успешно созданы!")
        except Exception as e:
            error_msg = f"Ошибка при создании таблиц: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Ощибка", error_msg)

    def open_add_data_dialog(self):
        """Открывает диалоговое окно для добавления данных"""
        dialog = AddDataDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Данные успешно добавлены!")
            logger.info("Новые данные были добавлены через диалоговое окно")

    def open_show_data_window(self):
        """Открывает окно для просмотра данных"""
        self.data_window = DataViewWindow(self)
        self.data_window.show()
        logger.info("Окно просмотра данных было открыто")

    def open_logs_windows(self):
        """Открывает окно просмотра логов"""
        self.logs_window = LogsWindows(self)
        self.logs_window.show()
        logger.info("Окно просмотра логов было открыто")
