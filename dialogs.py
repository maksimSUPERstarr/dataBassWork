"""
Содержит диалоги GUI для второй контрольной работы:
- SchemaEditorDialog — транзакционные операции ALTER TABLE (добавить/удалить столбцы, переименование, типы, ограничения, внешние ключи)
- SelectBuilderDialog — конструктор SELECT с выбором столбцов, WHERE/ORDER BY/GROUP BY/HAVING, JOIN
- SearchDialog — выбор режима поиска (LIKE, ~, ~*, !~, !~*)
- StringFuncsDialog — применение строковых функций (UPPER/LOWER/TRIM/SUBSTRING/LPAD/RPAD/CONCAT)

Визуальный стиль: фон #FAFAFA, текст #000, кнопки белые с серой рамкой (1px solid #C0C0C0), шрифт Helvetica Neue.
Диалоги модальные. Кнопки внизу — уменьшенного размера, белые с серой рамкой.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple, Literal

from psycopg2.extras import Json
from PyQt6.QtCore import QDateTime, QDate
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QTabWidget, QMessageBox,
    QCheckBox, QDoubleSpinBox, QTextEdit, QDateEdit, QDateTimeEdit
)

from database import AlterAction, alter_table, SelectParams, execute_select, apply_string_func

logger = logging.getLogger(__name__)

# ---- design constants (Kanye/Gosha minimal)
APP_BG = "#FAFAFA"
TEXT_COLOR = "#000000"
BORDER_COLOR = "#C0C0C0"
FONT_STACK = "Helvetica Neue, Arial, sans-serif"

BASE_STYLE = f"""
    * {{
        background-color: {APP_BG};
        color: {TEXT_COLOR};
        font-family: {FONT_STACK};
        font-size: 12pt;
    }}
    QLabel {{ color: {TEXT_COLOR}; }}
    QLineEdit, QComboBox {{
        border: 1px solid {BORDER_COLOR};
        padding: 6px;
    }}
    QPushButton {{
        background-color: #FFFFFF;
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        padding: 8px 14px;
    }}
    QPushButton:hover {{
        background-color: #EAEAEA;
    }}
"""

SMALL_BTNS_STYLE = f"""
    QPushButton {{
        background-color: #FFFFFF;
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        padding: 6px 10px;
        font-size: 11pt;
    }}
    QPushButton:hover {{ background-color: #EAEAEA; }}
"""


class _BaseModalDialog(QDialog):
    """Общий базовый диалог: белый фон, чёрный текст, модальный."""
    def __init__(self, title: str, parent: Optional[QWidget]=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setStyleSheet(BASE_STYLE)


# ---------------- SchemaEditorDialog ----------------

class SchemaEditorDialog(_BaseModalDialog):
    """Мастер транзакционных операций ALTER TABLE."""

    def __init__(self, parent: Optional[QWidget]=None):
        super().__init__("Редактор схемы (ALTER TABLE)", parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("Редактор схемы — ALTER TABLE")
        title.setStyleSheet("font-style: italic; font-size: 14pt;")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        self._build_tab_columns()
        self._build_tab_types()
        self._build_tab_constraints()
        self._build_tab_foreign()

        root.addWidget(self.tabs)

        # Нижние кнопки — уменьшенного размера, белые с серой рамкой
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.apply_btn.clicked.connect(self.apply_changes)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.cancel_btn.clicked.connect(self.reject)

        btns.addWidget(self.apply_btn)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

    # ---- Вкладка «Столбцы»
    def _build_tab_columns(self):
        w = QWidget()
        f = QFormLayout(w)

        self.columns_edit = QLineEdit()
        self.columns_edit.setPlaceholderText("Например: e.id, e.name, m.score или *")
        f.addRow("Столбцы:", self.columns_edit)

        self.tabs.addTab(w, "Столбцы")

        self.table_name_cols = QLineEdit()
        self.table_name_cols.setPlaceholderText("Имя таблицы (например: users)")
        f.addRow("Таблица:", self.table_name_cols)

        # Имя нового столбца
        self.add_col_name = QLineEdit()
        self.add_col_name.setPlaceholderText("Имя столбца")

        # Тип нового столбца — выпадающий список, как у NOT NULL
        self.add_col_type = QComboBox()
        self.add_col_type.addItems([
            "INTEGER",
            "BIGINT",
            "SMALLINT",
            "SERIAL",
            "REAL",
            "DOUBLE PRECISION",
            "NUMERIC(10,2)",
            "BOOLEAN",
            "TEXT",
            "VARCHAR(100)",
            "DATE",
            "TIMESTAMP",
            "JSONB"
        ])

        trow = QHBoxLayout()
        trow.addWidget(self.add_col_name)
        trow.addWidget(self.add_col_type)
        twrap = QWidget()
        twrap.setLayout(trow)
        f.addRow("Добавить столбец (name, type):", twrap)

        # дальше оставляешь как было: удалить столбец, переименовать, NOT NULL и т.д.
        ...
        self.tabs.addTab(w, "Столбцы")

    # ---- Вкладка «Типы»
    # ---- Вкладка «Типы»
    def _build_tab_types(self):
        w = QWidget()
        f = QFormLayout(w)

        # Имя таблицы
        self.table_name_types = QLineEdit()
        self.table_name_types.setPlaceholderText("Имя таблицы (например, users)")
        f.addRow("Таблица:", self.table_name_types)

        # Имя столбца
        self.type_col = QLineEdit()
        self.type_col.setPlaceholderText("Имя столбца (например, age)")

        # Предустановленный список допустимых типов
        self.type_new = QComboBox()
        self.type_new.addItems([
            "INTEGER",
            "BIGINT",
            "SMALLINT",
            "SERIAL",
            "REAL",
            "DOUBLE PRECISION",
            "NUMERIC(10,2)",
            "BOOLEAN",
            "TEXT",
            "VARCHAR(100)",
            "DATE",
            "TIMESTAMP",
            "JSONB"
        ])

        # Компоновка строки «col → type»
        trow = QHBoxLayout()
        trow.addWidget(self.type_col)
        trow.addWidget(self.type_new)
        twrap = QWidget()
        twrap.setLayout(trow)
        f.addRow("Изменить тип (col → type):", twrap)

        self.tabs.addTab(w, "Типы")

    # ---- Вкладка «Ограничения»
    def _build_tab_constraints(self):
        w = QWidget()
        f = QFormLayout(w)

        self.table_name_cons = QLineEdit()
        f.addRow("Таблица:", self.table_name_cons)

        # UNIQUE
        self.uniq_col = QLineEdit()
        self.uniq_name = QLineEdit()
        urow = QHBoxLayout()
        urow.addWidget(self.uniq_col)
        urow.addWidget(self.uniq_name)
        uwrap = QWidget(); uwrap.setLayout(urow)
        f.addRow("UNIQUE (col, constraint_name optional):", uwrap)

        # CHECK
        self.check_expr = QLineEdit()
        self.check_name = QLineEdit()
        crow = QHBoxLayout()
        crow.addWidget(self.check_expr)
        crow.addWidget(self.check_name)
        cwrap = QWidget(); cwrap.setLayout(crow)
        f.addRow("CHECK (expr, constraint_name optional):", cwrap)

        # DROP CONSTRAINT
        self.drop_con_name = QLineEdit()
        f.addRow("Удалить ограничение (name):", self.drop_con_name)

        self.tabs.addTab(w, "Ограничения")

    # ---- Вкладка «Внешние ключи»
    def _build_tab_foreign(self):
        w = QWidget()
        f = QFormLayout(w)

        self.table_name_fk = QLineEdit()
        f.addRow("Таблица:", self.table_name_fk)

        self.fk_col = QLineEdit()
        self.fk_ref_table = QLineEdit()
        self.fk_ref_col = QLineEdit()
        self.fk_name = QLineEdit()
        fkrow = QGridLayout()
        fkrow.addWidget(QLabel("Колонка:"), 0, 0); fkrow.addWidget(self.fk_col, 0, 1)
        fkrow.addWidget(QLabel("Ссылается на таблицу:"), 1, 0); fkrow.addWidget(self.fk_ref_table, 1, 1)
        fkrow.addWidget(QLabel("Колонку:"), 2, 0); fkrow.addWidget(self.fk_ref_col, 2, 1)
        fkrow.addWidget(QLabel("Имя ограничения:"), 3, 0); fkrow.addWidget(self.fk_name, 3, 1)
        f.addRow("Внешний ключ:", QWidget()); f.addRow(fkrow)

        self.drop_fk_name = QLineEdit()
        f.addRow("Удалить ограничение:", self.drop_fk_name)

        self.tabs.addTab(w, "Внешние ключи")

    # ---- Применение изменений (одной транзакцией)
    # ---- Применение изменений (одной транзакцией)
    def apply_changes(self):
        try:
            actions: List[AlterAction] = []

            # ----- Вкладка «Столбцы»
            t = self.table_name_cols.text().strip()
            if t:
                # Добавить столбец
                if self.add_col_name.text().strip():
                    actions.append(
                        AlterAction(
                            kind="add_column",
                            table=t,
                            column=self.add_col_name.text().strip(),
                            data_type=self.add_col_type.currentText().strip(),
                        )
                    )

                # Удалить столбец
                if self.drop_col.text().strip():
                    actions.append(
                        AlterAction(
                            kind="drop_column",
                            table=t,
                            column=self.drop_col.text().strip(),
                            cascade=self.drop_cascade.isChecked(),
                        )
                    )

                # Переименовать столбец
                if self.rename_col_old.text().strip() and self.rename_col_new.text().strip():
                    actions.append(
                        AlterAction(
                            kind="rename_column",
                            table=t,
                            column=self.rename_col_old.text().strip(),
                            new_name=self.rename_col_new.text().strip(),
                        )
                    )

                # NOT NULL / DROP NOT NULL
                if self.notnull_col.text().strip():
                    col = self.notnull_col.text().strip()
                    if self.notnull_mode.currentText().startswith("SET"):
                        actions.append(
                            AlterAction(kind="set_not_null", table=t, column=col)
                        )
                    else:
                        actions.append(
                            AlterAction(kind="drop_not_null", table=t, column=col)
                        )

            # ----- Вкладка «Типы»
            t2 = self.table_name_types.text().strip()
            if t2 and self.type_col.text().strip() and self.type_new.currentText().strip():
                actions.append(
                    AlterAction(
                        kind="alter_type",
                        table=t2,
                        column=self.type_col.text().strip(),
                        data_type=self.type_new.currentText().strip(),
                    )
                )

            # ----- Вкладка «Ограничения»
            t3 = self.table_name_cons.text().strip()
            if t3:
                if self.uniq_col.text().strip():
                    actions.append(
                        AlterAction(
                            kind="add_unique",
                            table=t3,
                            column=self.uniq_col.text().strip(),
                            constraint_name=(self.uniq_name.text().strip() or None),
                        )
                    )
                if self.check_expr.text().strip():
                    actions.append(
                        AlterAction(
                            kind="add_check",
                            table=t3,
                            check_expr=self.check_expr.text().strip(),
                            constraint_name=(self.check_name.text().strip() or None),
                        )
                    )
                if self.drop_con_name.text().strip():
                    actions.append(
                        AlterAction(
                            kind="drop_constraint",
                            table=t3,
                            constraint_name=self.drop_con_name.text().strip(),
                        )
                    )

            # ----- Вкладка «Внешние ключи»
            t4 = self.table_name_fk.text().strip()
            if t4 and self.fk_col.text().strip() and self.fk_ref_table.text().strip() and self.fk_ref_col.text().strip():
                actions.append(
                    AlterAction(
                        kind="add_foreign_key",
                        table=t4,
                        column=self.fk_col.text().strip(),
                        ref_table=self.fk_ref_table.text().strip(),
                        ref_column=self.fk_ref_col.text().strip(),
                        constraint_name=(self.fk_name.text().strip() or None),
                    )
                )
            if t4 and self.drop_fk_name.text().strip():
                actions.append(
                    AlterAction(
                        kind="drop_constraint",
                        table=t4,
                        constraint_name=self.drop_fk_name.text().strip(),
                    )
                )

            if not actions:
                QMessageBox.information(self, "Нет изменений", "Не указано ни одного действия.")
                return

            from database import get_connection
            conn = get_connection()
            try:
                msg = alter_table(conn, actions)
                QMessageBox.information(self, "Успех", msg)
                self.accept()
            finally:
                conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")


class SelectBuilderDialog(_BaseModalDialog):
    """
    Конструктор запросов SELECT без ручного SQL.
    Поддерживает: выбор таблиц, столбцов, JOIN, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT/OFFSET.
    """

    def __init__(self, parent: Optional[QWidget]=None):
        super().__init__("Конструктор SELECT", parent)
        self.result_rows: Optional[List[Dict[str, Any]]] = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("Конструктор SELECT")
        title.setStyleSheet("font-style: italic; font-size: 14pt;")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        self._build_tab_tables_and_joins()
        self._build_tab_columns()
        self._build_tab_where()
        self._build_tab_group_having()
        self._build_tab_order_limit()

        root.addWidget(self.tabs)

        # Нижние кнопки
        btns = QHBoxLayout()
        btns.addStretch(1)

        self.preview_btn = QPushButton("Предпросмотр")
        self.preview_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.preview_btn.clicked.connect(self.on_preview)

        self.ok_btn = QPushButton("Выполнить")
        self.ok_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.ok_btn.clicked.connect(self.on_accept)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.cancel_btn.clicked.connect(self.reject)

        btns.addWidget(self.preview_btn)
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

    # ---- Таблицы и JOIN-ы
    def _build_tab_tables_and_joins(self):
        w = QWidget()
        lay = QFormLayout(w)

        # список таблиц: через запятую (например: public.experiments e, public.ml_models m)
        self.tables_edit = QLineEdit()
        self.tables_edit.setPlaceholderText("Пример: experiments e, ml_models m")
        lay.addRow("Таблицы (с алиасами):", self.tables_edit)

        # мастер JOIN
        grid = QGridLayout()
        self.join_type = QComboBox(); self.join_type.addItems(["INNER", "LEFT", "RIGHT", "FULL"])
        self.join_table = QLineEdit(); self.join_table.setPlaceholderText("Таблица B (с алиасом)")
        self.join_on = QLineEdit(); self.join_on.setPlaceholderText("Условие ON, напр. e.model_id = m.id")
        grid.addWidget(QLabel("Тип:"), 0, 0); grid.addWidget(self.join_type, 0, 1)
        grid.addWidget(QLabel("JOIN таблица:"), 1, 0); grid.addWidget(self.join_table, 1, 1)
        grid.addWidget(QLabel("ON:"), 2, 0); grid.addWidget(self.join_on, 2, 1)

        # возможность добавить несколько JOINов: аккумулируем в списке
        self.joins: List[Dict[str, Any]] = []
        join_btns = QHBoxLayout()
        self.add_join_btn = QPushButton("Добавить JOIN")
        self.add_join_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.add_join_btn.clicked.connect(self._on_add_join)
        self.clear_join_btn = QPushButton("Очистить JOIN-ы")
        self.clear_join_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.clear_join_btn.clicked.connect(self._on_clear_joins)
        join_btns.addWidget(self.add_join_btn)
        join_btns.addWidget(self.clear_join_btn)

        lay.addRow("Мастер JOIN:", QWidget()); lay.addRow(grid)
        lay.addRow(join_btns)

        self.tabs.addTab(w, "Таблицы / JOIN")

    def _on_add_join(self):
        jtype = self.join_type.currentText().strip().upper()
        jtbl = self.join_table.text().strip()
        jon = self.join_on.text().strip()
        if not (jtbl and jon):
            QMessageBox.warning(self, "JOIN", "Укажите таблицу и выражение ON.")
            return
        self.joins.append({"type": jtype, "table": jtbl, "on": jon})
        QMessageBox.information(self, "JOIN", f"Добавлено: {jtype} JOIN {jtbl} ON {jon}")
        self.join_table.clear()
        self.join_on.clear()

    def _on_clear_joins(self):
        self.joins.clear()
        QMessageBox.information(self, "JOIN", "Список JOIN-ов очищен.")

    # ---- Столбцы
    # ---- Вкладка «Столбцы»
    def _build_tab_columns(self):
        w = QWidget()
        f = QFormLayout(w)

        # Таблица
        self.table_name_cols = QLineEdit()
        self.table_name_cols.setPlaceholderText("Имя таблицы (например: users)")
        f.addRow("Таблица:", self.table_name_cols)

        # ---- Добавить столбец (name, type) ----
        self.add_col_name = QLineEdit()
        self.add_col_name.setPlaceholderText("Имя столбца")

        # Тип нового столбца — выпадающий список
        self.add_col_type = QComboBox()
        self.add_col_type.addItems([
            "INTEGER",
            "BIGINT",
            "SMALLINT",
            "SERIAL",
            "REAL",
            "DOUBLE PRECISION",
            "NUMERIC(10,2)",
            "BOOLEAN",
            "TEXT",
            "VARCHAR(100)",
            "DATE",
            "TIMESTAMP",
            "JSONB"
        ])

        add_row = QHBoxLayout()
        add_row.addWidget(self.add_col_name)
        add_row.addWidget(self.add_col_type)
        add_wrap = QWidget()
        add_wrap.setLayout(add_row)
        f.addRow("Добавить столбец (name, type):", add_wrap)

        # ---- Удалить столбец ----
        self.drop_col = QLineEdit()
        self.drop_col.setPlaceholderText("Имя столбца")

        self.drop_cascade = QCheckBox("CASCADE")

        drop_row = QHBoxLayout()
        drop_row.addWidget(self.drop_col)
        drop_row.addWidget(self.drop_cascade)
        drop_wrap = QWidget()
        drop_wrap.setLayout(drop_row)
        f.addRow("Удалить столбец:", drop_wrap)

        # ---- Переименовать столбец (old → new) ----
        self.rename_col_old = QLineEdit()
        self.rename_col_old.setPlaceholderText("старое имя")

        self.rename_col_new = QLineEdit()
        self.rename_col_new.setPlaceholderText("новое имя")

        ren_row = QHBoxLayout()
        ren_row.addWidget(self.rename_col_old)
        ren_row.addWidget(self.rename_col_new)
        ren_wrap = QWidget()
        ren_wrap.setLayout(ren_row)
        f.addRow("Переименовать столбец (old → new):", ren_wrap)

        # ---- NOT NULL для столбца ----
        self.notnull_col = QLineEdit()
        self.notnull_col.setPlaceholderText("Имя столбца")

        self.notnull_mode = QComboBox()
        self.notnull_mode.addItems(["SET NOT NULL", "DROP NOT NULL"])

        nn_row = QHBoxLayout()
        nn_row.addWidget(self.notnull_col)
        nn_row.addWidget(self.notnull_mode)
        nn_wrap = QWidget()
        nn_wrap.setLayout(nn_row)
        f.addRow("NOT NULL для столбца:", nn_wrap)

        self.tabs.addTab(w, "Столбцы")

    # ---- WHERE
    def _build_tab_where(self):
        w = QWidget()
        lay = QFormLayout(w)

        # Одно условие за раз, кнопка "Добавить" накапливает
        grid = QGridLayout()
        self.where_col = QLineEdit(); self.where_col.setPlaceholderText("e.name")
        self.where_op = QComboBox(); self.where_op.addItems(["=", "<>", "<", ">", "<=", ">=", "LIKE", "ILIKE", "~", "~*", "!~", "!~*"])
        self.where_val = QLineEdit(); self.where_val.setPlaceholderText("Значение (подставится как параметр)")
        grid.addWidget(QLabel("Колонка:"), 0, 0); grid.addWidget(self.where_col, 0, 1)
        grid.addWidget(QLabel("Оператор:"), 1, 0); grid.addWidget(self.where_op, 1, 1)
        grid.addWidget(QLabel("Значение:"), 2, 0); grid.addWidget(self.where_val, 2, 1)

        self.where_list: List[Dict[str, Any]] = []
        btns = QHBoxLayout()
        self.add_where_btn = QPushButton("Добавить фильтр")
        self.add_where_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.add_where_btn.clicked.connect(self._on_add_where)
        self.clear_where_btn = QPushButton("Очистить фильтры")
        self.clear_where_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.clear_where_btn.clicked.connect(self._on_clear_where)
        btns.addWidget(self.add_where_btn)
        btns.addWidget(self.clear_where_btn)

        lay.addRow("Условие WHERE:", QWidget()); lay.addRow(grid)
        lay.addRow(btns)

        self.tabs.addTab(w, "WHERE")

    def _on_add_where(self):
        col = self.where_col.text().strip()
        op = self.where_op.currentText().strip()
        val = self.where_val.text()
        if not col:
            QMessageBox.warning(self, "WHERE", "Укажите колонку.")
            return
        self.where_list.append({"col": col, "op": op, "val": val})
        QMessageBox.information(self, "WHERE", f"Добавлено: {col} {op} ?")
        self.where_col.clear(); self.where_val.clear()

    def _on_clear_where(self):
        self.where_list.clear()
        QMessageBox.information(self, "WHERE", "Список фильтров очищен.")

    # ---- GROUP BY / HAVING
    def _build_tab_group_having(self):
        w = QWidget()
        lay = QFormLayout(w)

        self.group_by_edit = QLineEdit()
        self.group_by_edit.setPlaceholderText("Например: e.attack_type, e.model_id")
        lay.addRow("GROUP BY:", self.group_by_edit)

        # HAVING: как WHERE, но по агрегатам
        grid = QGridLayout()
        self.having_col = QLineEdit(); self.having_col.setPlaceholderText("COUNT(m.id)")
        self.having_op = QComboBox(); self.having_op.addItems(["=", "<>", "<", ">", "<=", ">="])
        self.having_val = QLineEdit(); self.having_val.setPlaceholderText("Значение")
        grid.addWidget(QLabel("Выражение:"), 0, 0); grid.addWidget(self.having_col, 0, 1)
        grid.addWidget(QLabel("Оператор:"), 1, 0); grid.addWidget(self.having_op, 1, 1)
        grid.addWidget(QLabel("Значение:"), 2, 0); grid.addWidget(self.having_val, 2, 1)

        self.having_list: List[Dict[str, Any]] = []
        btns = QHBoxLayout()
        self.add_having_btn = QPushButton("Добавить HAVING")
        self.add_having_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.add_having_btn.clicked.connect(self._on_add_having)
        self.clear_having_btn = QPushButton("Очистить HAVING")
        self.clear_having_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.clear_having_btn.clicked.connect(self._on_clear_having)
        btns.addWidget(self.add_having_btn)
        btns.addWidget(self.clear_having_btn)

        lay.addRow("HAVING:", QWidget()); lay.addRow(grid)
        lay.addRow(btns)

        self.tabs.addTab(w, "GROUP/HAVING")

    def _on_add_having(self):
        col = self.having_col.text().strip()
        op = self.having_op.currentText().strip()
        val = self.having_val.text()
        if not col:
            QMessageBox.warning(self, "HAVING", "Укажите выражение.")
            return
        self.having_list.append({"col": col, "op": op, "val": val})
        QMessageBox.information(self, "HAVING", f"Добавлено: {col} {op} ?")
        self.having_col.clear(); self.having_val.clear()

    def _on_clear_having(self):
        self.having_list.clear()
        QMessageBox.information(self, "HAVING", "Список HAVING очищен.")

    # ---- ORDER BY / LIMIT / OFFSET
    def _build_tab_order_limit(self):
        w = QWidget()
        lay = QFormLayout(w)

        # ORDER BY: одно поле за раз, можно добавлять несколько
        grid = QGridLayout()
        self.order_col = QLineEdit(); self.order_col.setPlaceholderText("e.created_at")
        self.order_dir = QComboBox(); self.order_dir.addItems(["ASC", "DESC"])
        grid.addWidget(QLabel("Колонка:"), 0, 0); grid.addWidget(self.order_col, 0, 1)
        grid.addWidget(QLabel("Порядок:"), 1, 0); grid.addWidget(self.order_dir, 1, 1)

        self.order_list: List[Tuple[str, Literal['ASC','DESC']]] = []
        ob_btns = QHBoxLayout()
        self.add_order_btn = QPushButton("Добавить сортировку")
        self.add_order_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.add_order_btn.clicked.connect(self._on_add_order)
        self.clear_order_btn = QPushButton("Очистить сортировки")
        self.clear_order_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.clear_order_btn.clicked.connect(self._on_clear_order)
        ob_btns.addWidget(self.add_order_btn)
        ob_btns.addWidget(self.clear_order_btn)

        # LIMIT/OFFSET
        self.limit_spin = QSpinBox(); self.limit_spin.setRange(0, 100000); self.limit_spin.setValue(100)
        self.offset_spin = QSpinBox(); self.offset_spin.setRange(0, 100000); self.offset_spin.setValue(0)

        lay.addRow("ORDER BY:", QWidget()); lay.addRow(grid); lay.addRow(ob_btns)
        lay.addRow("LIMIT:", self.limit_spin)
        lay.addRow("OFFSET:", self.offset_spin)

        self.tabs.addTab(w, "ORDER/LIMIT")

    def _on_add_order(self):
        col = self.order_col.text().strip()
        direction = self.order_dir.currentText().strip()
        if not col:
            QMessageBox.warning(self, "ORDER BY", "Укажите колонку.")
            return
        self.order_list.append((col, direction))  # type: ignore
        QMessageBox.information(self, "ORDER BY", f"Добавлено: {col} {direction}")
        self.order_col.clear()

    def _on_clear_order(self):
        self.order_list.clear()
        QMessageBox.information(self, "ORDER BY", "Список сортировок очищен.")

    # ---- Построение параметров и выполнение
    def _collect_params(self) -> SelectParams:
        # таблицы
        tables_raw = self.tables_edit.text().strip()
        tables = [t.strip() for t in tables_raw.split(",") if t.strip()] if tables_raw else []
        if not tables:
            raise ValueError("Укажите хотя бы одну таблицу.")

        # столбцы
        cols_raw = self.columns_edit.text().strip()
        columns = [c.strip() for c in cols_raw.split(",")] if cols_raw else []

        # WHERE / HAVING уже собраны списками
        group_by = []
        if self.group_by_edit.text().strip():
            group_by = [g.strip() for g in self.group_by_edit.text().split(",") if g.strip()]

        limit = self.limit_spin.value() if self.limit_spin.value() > 0 else None
        offset = self.offset_spin.value() if self.offset_spin.value() > 0 else None

        return SelectParams(
            tables=tables,
            columns=columns,
            joins=self.joins,
            where=self.where_list,
            group_by=group_by,
            having=self.having_list,
            order_by=self.order_list,   # type: ignore
            limit=limit,
            offset=offset
        )

    def on_preview(self):
        try:
            params = self._collect_params()
            from database import get_connection, build_select_sql
            conn = get_connection()
            try:
                sql_text, args = build_select_sql(params)
                # Предпросмотр: покажем собранный SQL и число строк
                rows = execute_select(conn, params)
                self.result_rows = rows
                QMessageBox.information(
                    self, "Предпросмотр",
                    f"SQL:\n{sql_text}\n\nПараметры: {args}\n\nСтрок: {len(rows)}"
                )
            finally:
                conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")

    def on_accept(self):
        try:
            params = self._collect_params()
            from database import get_connection
            conn = get_connection()
            try:
                rows = execute_select(conn, params)
                self.result_rows = rows
                # Здесь мы просто показываем итог — интеграцию с DataView сделаем из windows.py
                QMessageBox.information(self, "Выполнено", f"Получено строк: {len(rows)}")
                self.accept()
            finally:
                conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")
# ---------------- SearchDialog ----------------

class SearchDialog(_BaseModalDialog):
    """
    Поиск по тексту с выбором режима:
    LIKE, ILIKE, ~, ~*, !~, !~*
    Возвращает число найденных строк (интеграция с DataView — в windows.py).
    """
    def __init__(self, parent: Optional[QWidget]=None):
        super().__init__("Поиск", parent)
        self.result_rows: Optional[List[Dict[str, Any]]] = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("Поиск по таблице")
        title.setStyleSheet("font-style: italic; font-size: 14pt;")
        root.addWidget(title)

        form = QFormLayout()
        self.table_edit = QLineEdit(); self.table_edit.setPlaceholderText("Например: experiments")
        self.column_edit = QLineEdit(); self.column_edit.setPlaceholderText("Например: name")
        self.mode_box = QComboBox(); self.mode_box.addItems(["LIKE", "ILIKE", "~", "~*", "!~", "!~*"])
        self.value_edit = QLineEdit(); self.value_edit.setPlaceholderText("Значение для поиска")

        form.addRow("Таблица:", self.table_edit)
        form.addRow("Колонка:", self.column_edit)
        form.addRow("Режим:", self.mode_box)
        form.addRow("Значение:", self.value_edit)
        root.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.ok_btn = QPushButton("Искать"); self.ok_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.ok_btn.clicked.connect(self.on_search)
        self.cancel_btn = QPushButton("Отмена"); self.cancel_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.ok_btn); btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

    def on_search(self):
        table = self.table_edit.text().strip()
        col = self.column_edit.text().strip()
        mode = self.mode_box.currentText().strip()
        val = self.value_edit.text()

        if not (table and col):
            QMessageBox.warning(self, "Поиск", "Укажите таблицу и колонку.")
            return

        from database import get_connection
        conn = get_connection()
        try:
            # Собираем параметризованный запрос
            if mode in ("LIKE", "ILIKE", "~", "~*", "!~", "!~*"):
                op = mode
            else:
                op = "LIKE"

            # Пример: SELECT * FROM table WHERE col <op> %s LIMIT 200
            q = f"SELECT * FROM {table} WHERE {col} {op} %s LIMIT 200"
            from database import safe_execute
            rows = safe_execute(conn, q, [val])
            self.result_rows = rows
            QMessageBox.information(self, "Результат", f"Найдено строк: {len(rows)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")
        finally:
            conn.close()


# ---------------- StringFuncsDialog ----------------

class StringFuncsDialog(_BaseModalDialog):
    """
    Диалог применения строковых функций:
    UPPER, LOWER, TRIM, SUBSTRING, LPAD, RPAD, CONCAT.
    Возвращает предпросмотр (исходное значение и transformed).
    """
    def __init__(self, parent: Optional[QWidget]=None):
        super().__init__("Строковые функции", parent)
        self.result_rows: Optional[List[Dict[str, Any]]] = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("Строковые функции")
        title.setStyleSheet("font-style: italic; font-size: 14pt;")
        root.addWidget(title)

        form = QFormLayout()
        self.table_edit = QLineEdit(); self.table_edit.setPlaceholderText("Например: experiments")
        self.column_edit = QLineEdit(); self.column_edit.setPlaceholderText("Например: name")
        self.func_box = QComboBox(); self.func_box.addItems(["UPPER", "LOWER", "TRIM", "SUBSTRING", "LPAD", "RPAD", "CONCAT"])

        # Параметры функций:
        # SUBSTRING: start, length
        # LPAD/RPAD: length, fill
        # CONCAT: suffix/prefix (мы добавляем как второй аргумент)
        self.arg1_edit = QLineEdit(); self.arg1_edit.setPlaceholderText("Аргумент 1 (при необходимости)")
        self.arg2_edit = QLineEdit(); self.arg2_edit.setPlaceholderText("Аргумент 2 (при необходимости)")

        form.addRow("Таблица:", self.table_edit)
        form.addRow("Колонка:", self.column_edit)
        form.addRow("Функция:", self.func_box)
        form.addRow("Аргумент 1:", self.arg1_edit)
        form.addRow("Аргумент 2:", self.arg2_edit)
        root.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.preview_btn = QPushButton("Предпросмотр")
        self.preview_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.preview_btn.clicked.connect(self.on_preview)
        self.cancel_btn = QPushButton("Закрыть")
        self.cancel_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.preview_btn); btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

    def on_preview(self):
        table = self.table_edit.text().strip()
        col = self.column_edit.text().strip()
        func = self.func_box.currentText().strip()
        a1 = self.arg1_edit.text().strip()
        a2 = self.arg2_edit.text().strip()

        if not (table and col and func):
            QMessageBox.warning(self, "Строковые функции", "Укажите таблицу, колонку и функцию.")
            return

        # Подготовка аргументов под конкретные функции
        extra_args: List[Any] = []
        if func == "SUBSTRING":
            if not a1 or not a2:
                QMessageBox.warning(self, "SUBSTRING", "Укажите старт и длину.")
                return
            try:
                extra_args = [int(a1), int(a2)]
            except ValueError:
                QMessageBox.warning(self, "SUBSTRING", "Старт и длина должны быть числами.")
                return
        elif func in ("LPAD", "RPAD"):
            if not a1 or not a2:
                QMessageBox.warning(self, func, "Укажите длину и заполнитель.")
                return
            try:
                extra_args = [int(a1), a2]
            except ValueError:
                QMessageBox.warning(self, func, "Длина должна быть числом.")
                return
        elif func == "CONCAT":
            if not a1:
                QMessageBox.warning(self, "CONCAT", "Укажите строку для конкатенации.")
                return
            extra_args = [a1]
        else:
            extra_args = []

        from database import get_connection
        conn = get_connection()
        try:
            rows = apply_string_func(conn, table, col, func, *extra_args)
            self.result_rows = rows
            # Покажем только количество — вывод в таблицу сделаем из windows.py
            QMessageBox.information(self, "Предпросмотр", f"Получено строк: {len(rows)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")
        finally:
            conn.close()

class InsertRowDialog(_BaseModalDialog):
    """
    Добавление одной записи в выбранную таблицу.
    Поля строятся динамически по структуре таблицы (get_columns).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Добавить запись", parent)
        self._cols_meta: List[Dict[str, Any]] = []
        self._editors: Dict[str, QWidget] = {}
        self._null_flags: Dict[str, QCheckBox] = {}
        self.table_name: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("Добавление записи")
        title.setStyleSheet("font-style: italic; font-size: 14pt;")
        root.addWidget(title)

        form = QFormLayout()
        self.table_edit = QLineEdit()
        self.table_edit.setPlaceholderText("Имя таблицы (например: users)")
        form.addRow("Таблица:", self.table_edit)

        # Кнопка «Загрузить поля»
        load_row = QHBoxLayout()
        self.load_btn = QPushButton("Загрузить поля")
        self.load_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.load_btn.clicked.connect(self._on_load_fields)
        load_row.addStretch(1); load_row.addWidget(self.load_btn)
        lw = QWidget(); lw.setLayout(load_row)
        form.addRow("", lw)

        # Контейнер с динамическими редакторами
        self.fields_wrap = QWidget()
        self.fields_layout = QFormLayout(self.fields_wrap)
        form.addRow("Поля:", self.fields_wrap)

        root.addLayout(form)

        # Нижние кнопки
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet(SMALL_BTNS_STYLE)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.save_btn); btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

    # ---- helpers

    @staticmethod
    def _editor_for_type(pg_type: str) -> QWidget:
        t = pg_type.lower()
        # Числа
        if any(x in t for x in ["int", "serial", "smallint", "bigint"]):
            w = QSpinBox(); w.setMinimum(-2_147_483_648); w.setMaximum(2_147_483_647); return w
        if any(x in t for x in ["numeric", "real", "double"]):
            w = QDoubleSpinBox(); w.setDecimals(6); w.setMinimum(-1e12); w.setMaximum(1e12); return w
        # Булево
        if "bool" in t:
            cb = QComboBox(); cb.addItems(["FALSE", "TRUE"]); return cb
        # Дата/время
        if t.startswith("timestamp"):
            dt = QDateTimeEdit()
            dt.setCalendarPopup(True)
            dt.setDateTime(QDateTime.currentDateTime())
            return dt
        if t == "date":
            d = QDateEdit()
            d.setCalendarPopup(True)
            d.setDate(QDate.currentDate())
            return d
        # JSONB и текстовые — multiline
        if "json" in t:
            te = QTextEdit(); te.setPlaceholderText('JSON, напр. {"k": "v"}'); return te
        # Текст
        le = QLineEdit(); return le

    def _on_load_fields(self):
        tbl = self.table_edit.text().strip()
        if not tbl:
            QMessageBox.warning(self, "Таблица", "Укажите имя таблицы.")
            return

        from database import get_connection, get_columns
        conn = get_connection()
        try:
            self._cols_meta = get_columns(conn, tbl, schema="public")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"{e}")
            conn.close()
            return

        self.table_name = tbl
        # Очистим старые редакторы
        while self.fields_layout.rowCount():
            self.fields_layout.removeRow(0)
        self._editors.clear()
        self._null_flags.clear()

        # Строим редакторы по колонкам
        for col in self._cols_meta:
            name = col["column_name"]
            dtype = col["data_type"]
            default = col.get("column_default")
            nullable = bool(col.get("nullable", True))

            # Пропустим явные serial/identity, если есть дефолт
            if default and ("nextval" in str(default) or "identity" in str(default).lower()):
                continue

            editor = self._editor_for_type(dtype)
            null_cb = QCheckBox("NULL/DEFAULT")
            self._editors[name] = editor
            self._null_flags[name] = null_cb

            row = QHBoxLayout()
            row.addWidget(editor, 3)
            row.addWidget(null_cb, 1)
            wrap = QWidget(); wrap.setLayout(row)
            label = f"{name} : {dtype}" + (" (NULL ok)" if nullable else " (NOT NULL)")
            self.fields_layout.addRow(label, wrap)

        if not self._editors:
            QMessageBox.information(self, "Поля", "Нет редактируемых полей (все авто).")
        conn.close()

    def _collect_values(self) -> Tuple[List[str], List[Any]]:
        cols: List[str] = []
        vals: List[Any] = []

        for name, editor in self._editors.items():
            # если пользователь отметил "NULL/DEFAULT"
            if self._null_flags[name].isChecked():
                cols.append(name)
                vals.append(None)
                continue

            # Считываем по типу виджета
            if isinstance(editor, QSpinBox):
                value = int(editor.value())
            elif isinstance(editor, QDoubleSpinBox):
                value = float(editor.value())
            elif isinstance(editor, QComboBox):  # для BOOLEAN
                value = True if editor.currentText().upper() == "TRUE" else False
            elif isinstance(editor, QDateTimeEdit):
                # отдадим как строку в SQL-формате timestamp
                value = editor.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            elif isinstance(editor, QDateEdit):
                value = editor.date().toString("yyyy-MM-dd")
            elif isinstance(editor, QTextEdit):
                value = editor.toPlainText().strip()
            elif isinstance(editor, QLineEdit):
                value = editor.text().strip()
            else:
                value = None

            # Пустая строка → NULL
            if value == "":
                value = None

            # Если поле похоже на JSON — обернём, чтобы адаптер отдал корректно
            # (это безопасно: Json(None) → NULL)
            col_meta = next((c for c in self._cols_meta if c["column_name"] == name), None)
            if col_meta and isinstance(value, str):
                dt = str(col_meta.get("data_type", "")).lower()
                if "json" in dt:
                    try:
                        import json
                        parsed = json.loads(value)  # валидируем JSON
                        value = Json(parsed)
                    except Exception:
                        # если невалидный JSON — оставим как есть, пусть БД вернёт ошибку
                        pass

            cols.append(name)
            vals.append(value)

        return cols, vals

    def _on_save(self):
        if not self.table_name:
            QMessageBox.warning(self, "Таблица", "Сначала загрузите поля таблицы.")
            return

        cols, vals = self._collect_values()
        if not cols:
            QMessageBox.warning(self, "Данные", "Не указано ни одного значения.")
            return

        try:
            from database import get_connection
            conn = get_connection()
            try:
                # Чистый безопасный INSERT без лишней магии обёрток
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join([f'"{c}"' for c in cols])  # экранируем идентификаторы простыми кавычками
                q = f'INSERT INTO "{self.table_name}" ({col_list}) VALUES ({placeholders})'

                cur = conn.cursor()
                cur.execute(q, vals)
                conn.commit()

                QMessageBox.information(self, "Готово", "Запись добавлена.")
                self.accept()
            finally:
                conn.close()
        except Exception as e:
            # Любая ошибка БД/валидации — показываем в диалоге, а не падаем процессом
            QMessageBox.critical(self, "Ошибка вставки", f"{e}")


# ---------------- exports ----------------

__all__ = [
    "SchemaEditorDialog",
    "SelectBuilderDialog",
    "SearchDialog",
    "StringFuncsDialog",
    "InsertRowDialog",
]
