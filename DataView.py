import logging
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from database import get_all_experiments

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

class DataViewWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр экспериментов")
        self.setGeometry(200, 200, 800, 600)

        # создаем центральный виджет и компоновку
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Создаем таблицу для отображения
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(self.refresh_btn)

        self.load_data()

        logger.info("Окно просмотра данных создано")

    def load_data(self):
        try:
            experiments = get_all_experiments()

            # Настраиваем таблицу
            self.table.setRowCount(len(experiments))
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "ID", "Название", "Активный", "Пользователи",
                "Успех", "Показы", "Клики", "Создан"
            ])

            # заполняем таблицу данным
            for row, experiment in enumerate(experiments):
                self.table.setItem(row, 0, QTableWidgetItem(str(experiment.id)))
                self.table.setItem(row, 1, QTableWidgetItem(str(experiment.name)))
                self.table.setItem(row, 2, QTableWidgetItem("Да" if experiment.is_active else "Нет"))
                self.table.setItem(row, 3, QTableWidgetItem(str(experiment.user_count)))
                self.table.setItem(row, 4, QTableWidgetItem(str(experiment.success_rate)))
                self.table.setItem(row, 5, QTableWidgetItem(str(experiment.impressions)))
                self.table.setItem(row, 6, QTableWidgetItem(str(experiment.clicks)))
                self.table.setItem(row, 7, QTableWidgetItem(experiment.created_at.strftime("%Y-%m-%d %H:%M")))

            # Настройка растягивание столбцов
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # исправлено

            logger.info(f"Загружено {len(experiments)} экспериментов")

        except Exception as e:
            error_msg = f"Ошибки при загрузке данных: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)
    def closeEvent(self, event):
        logger.info("Окно просмотра данных закрыто")
        event.accept()
