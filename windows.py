"""
Главное окно приложения:
- Две кнопки в строке (минималистичный стиль: фон #FAFAFA, текст #000, белые кнопки с серой рамкой)
- Кнопки: Создать таблицу, Редактор схемы, Конструктор SELECT, Мастер JOIN (встроен в конструктор),
  Строковые функции, Поиск, Применить изменения, Отменить, Лог..., Выход
- DataView: табличный просмотр результатов/предпросмотра
- Интеграция с dialogs.py и database.py
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QStatusBar,  QSizePolicy
)

from database import (
    get_connection, preview_table, execute_select, SelectParams, safe_execute
)
from dialogs import (
    SchemaEditorDialog, SelectBuilderDialog, SearchDialog, StringFuncsDialog
)
"константы для удобства"
APP_BG = "#FAFAFA"
TEXT_COLOR = "#000000"
BORDER_COLOR = "#C0C0C0"
FONT_STACK = "Helvetica Neue, Arial, sans-serif"

BASE_STYLE = f"""
    QWidget {{
        background-color: #FAFAFA;
        color: #000000;
        font-family: "Helvetica Neue", Arial, sans-serif;
        font-size: 12pt;
    }}
    QPushButton {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #FFFFFF, stop:1 #EAEAEA);
        border: 1px solid #BEBEBE;
        border-radius: 4px;
        padding: 12px;
        min-height: 48px;
    }}
    QPushButton:hover {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #F2F2F2, stop:1 #E0E0E0);
    }}
    QTableWidget {{
        gridline-color: #D0D0D0;
        alternate-background-color: #F5F5F5;
        selection-background-color: #E0E0E0;
        selection-color: #000000;
        border: 1px solid #C0C0C0;
    }}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DB Designer — KR-2")
        self.resize(1100, 720)
        self._setup_ui()
        self._last_rows: List[Dict[str, Any]] = []

    def _setup_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        cw.setStyleSheet(BASE_STYLE)

        root = QVBoxLayout(cw)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(14)

        # ─── Верхняя строка: название справа ───────────────────────
        topbar = QHBoxLayout()
        topbar.addStretch(1)  # уводим контент вправо

        title_wrap = QWidget()
        title_lay = QVBoxLayout(title_wrap)
        title_lay.setContentsMargins(0, 0, 0, 0)

        title = QLabel("The Second Test")
        title.setStyleSheet("font-weight: 600; font-size: 16pt;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title_lay.addWidget(title)

        topbar.addWidget(title_wrap, 0)
        root.addLayout(topbar)

        # ─── Таблица (занимает максимум пространства; со скроллами) ─
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        root.addWidget(self.table, 1)  # растягивается

        # ─── Кнопки: три строки по две, под таблицей, растягиваем ───
        self.btn_create = QPushButton("Создать таблицу")
        self.btn_schema = QPushButton("Редактор схемы")
        self.btn_select = QPushButton("Конструктор SELECT")
        self.btn_strings = QPushButton("Строковые функции")
        self.btn_search = QPushButton("Поиск")
        self.btn_exit = QPushButton("Выход")

        # делаем кнопки тянущимися по ширине
        for b in (self.btn_create, self.btn_schema, self.btn_select,
                  self.btn_strings, self.btn_search, self.btn_exit):
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        buttons = [
            self.btn_create, self.btn_schema,
            self.btn_select, self.btn_strings,
            self.btn_search, self.btn_exit,
        ]
        row = col = 0
        for b in buttons:
            grid.addWidget(b, row, col)
            col = (col + 1) % 2
            if col == 0:
                row += 1

        root.addLayout(grid)

        # ─── Статус-бар и сигналы ───────────────────────────────────
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.status = sb

        self.btn_create.clicked.connect(self.on_create_table)
        self.btn_schema.clicked.connect(self.on_schema_editor)
        self.btn_select.clicked.connect(self.on_select_builder)
        self.btn_strings.clicked.connect(self.on_string_funcs)
        self.btn_search.clicked.connect(self.on_search)
        self.btn_exit.clicked.connect(self.close)

    def _show_rows(self, rows: List[Dict[str, Any]]):
        self._last_rows = rows
        if not rows:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.status.showMessage("Пустой результат", 5000)
            return
        headers = list(rows[0].keys())
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, key in enumerate(headers):
                val = row.get(key, "")
                item = QTableWidgetItem(str(val))
                self.table.setItem(r_idx, c_idx, item)
        self.status.showMessage(f"Строк: {len(rows)}; Колонок: {len(headers)}", 5000)

    # ---- actions

    def on_create_table(self):
        # simple dialog-less flow: ask for name and create minimal table
        name, ok = QFileDialog.getSaveFileName(self, "Имя новой таблицы (впишите без расширения и нажмите 'Сохранить')", "", "Имя без расширения (*)")
        if not ok or not name:
            return
        # sanitize name from path
        import os
        base = os.path.basename(name)
        table = base.replace(".", "_").replace("-", "_")
        try:
            conn = get_connection()
            try:
                q = f'CREATE TABLE IF NOT EXISTS "{table}" (id SERIAL PRIMARY KEY, name TEXT)'
                safe_execute(conn, q)
                # preview new table
                rows = preview_table(conn, table, limit=0)
                self._show_rows(rows)
                QMessageBox.information(self, "Создано", f'Таблица "{table}" создана.')
            finally:
                conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def on_schema_editor(self):
        dlg = SchemaEditorDialog(self)
        if dlg.exec():
            # after schema changes we can refresh structure or show success message already handled
            pass

    def on_select_builder(self):
        dlg = SelectBuilderDialog(self)
        if dlg.exec() and getattr(dlg, "result_rows", None) is not None:
            self._show_rows(dlg.result_rows)
            self.status.showMessage(f"Показано строк: {len(dlg.result_rows)}", 5000)
        else:
            self.status.showMessage("Запрос отменён или результата нет.", 3000)

    def on_string_funcs(self):
        dlg = StringFuncsDialog(self)
        if dlg.exec():
            self._show_rows(dlg.result_rows)
            pass

    def on_search(self):
        dlg = SearchDialog(self)
        if dlg.exec():
            self._show_rows(dlg.result_rows)
            pass

    def on_apply_commit(self):
        QMessageBox.information(self, "Транзакция", "Изменения применяются автоматически после операций.")

    def on_apply_rollback(self):
        QMessageBox.information(self, "Транзакция", "Откат возможен для явных транзакций. В текущем режиме операции атомарны.")

    def on_show_log(self):
        import os
        logfile = "app.log"
        if os.path.exists(logfile):
            try:
                with open(logfile, "r", encoding="utf-8") as f:
                    data = f.read()[-5000:]
                QMessageBox.information(self, "Лог (хвост)", data if data else "Лог пуст.")
            except Exception as e:
                QMessageBox.warning(self, "Лог", f"Не удалось прочитать лог: {e}")
        else:
            QMessageBox.information(self, "Лог", "Файл лога не найден.")
def main():
    import sys
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
