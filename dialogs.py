import logging
from PyQt6.QtWidgets import (QDialog, QLineEdit, QCheckBox, QSpinBox,
                             QDoubleSpinBox, QPushButton, QFormLayout,
                             QHBoxLayout, QVBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt
from database import insert_experiment
from models import create_experiment_from_form_data

logger = logging.getLogger(__name__)


class AddDataDialog(QDialog):
    def __init__(self, parent=None):
        super(AddDataDialog, self).__init__(parent)
        # диалоговое окно
        self.setWindowTitle("Добавить эксперимент")
        self.setModal(True)
        self.setFixedSize(400, 350)

        # виджеты для ввода данных
        self.name_edit = QLineEdit()
        self.is_active_check = QCheckBox("Активный эксперимент")
        self.user_count_spin = QSpinBox()
        self.user_count_spin.setRange(0, 1000000)
        self.success_rate_spin = QDoubleSpinBox()
        self.success_rate_spin.setRange(0.0, 1.0)
        self.success_rate_spin.setSingleStep(0.01)
        self.success_rate_spin.setDecimals(3)
        self.impressions_spin = QSpinBox()
        self.impressions_spin.setRange(0, 1000000)
        self.clicks_spin = QSpinBox()
        self.clicks_spin.setRange(0, 1000000)

        # кнопки
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Отмена")

        # компоновка виджетов
        form_layout = QFormLayout()
        form_layout.addRow("Название:", self.name_edit)
        form_layout.addRow("", self.is_active_check)
        form_layout.addRow("Количество пользователей:", self.user_count_spin)
        form_layout.addRow("Процент успеха (0.0-1.0):", self.success_rate_spin)
        form_layout.addRow("Количество показов:", self.impressions_spin)
        form_layout.addRow("Количество кликов:", self.clicks_spin)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)

        # компоновка для диалогового окна
        self.setLayout(main_layout)

        # сигналы и слоты
        self.ok_btn.clicked.connect(self.add_experiment)
        self.cancel_btn.clicked.connect(self.reject)

        logger.info("Диалоговое окно открыто")

    def add_experiment(self):
        """Добавляет эксперимент в базу данных используя модель"""
        try:
            # Получаем данные из полей ввода
            form_data = {
                'name': self.name_edit.text().strip(),
                'is_active': self.is_active_check.isChecked(),
                'user_count': self.user_count_spin.value(),
                'success_rate': self.success_rate_spin.value(),
                'impressions': self.impressions_spin.value(),
                'clicks': self.clicks_spin.value()
            }

            experiment = create_experiment_from_form_data(form_data)
            # Проверяем валидность данных
            is_valid, error_msg = experiment.validate()
            if not is_valid:
                QMessageBox.warning(self, "Ошибка", error_msg)
                return

            # Вставляем данные в базу (ПРАВИЛЬНЫЙ ВЫЗОВ)
            experiment_id = insert_experiment(
                experiment.name,
                experiment.is_active,
                experiment.user_count,
                experiment.success_rate,
                experiment.clicks,
                experiment.impressions
            )

            logger.info(f"Добавлен эксперимент: {experiment.name} (ID: {experiment_id})")
            QMessageBox.information(self, "Успех",
                                    f"Эксперимент '{experiment.name}' успешно добавлен с ID: {experiment_id}")
            self.accept()
        except Exception as e:
            error_msg = f"Ошибка при добавлении эксперимента: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)
