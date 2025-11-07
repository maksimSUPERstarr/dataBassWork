"""
Содержит:
- Вспомогательные функции для подключения к базе данных
- Средства интроспекции (просмотра структуры) каталога PostgreSQL
- Транзакционный API для ALTER TABLE (структурированные операции изменения таблиц)
- Параметризованный конструктор запросов SELECT с поддержкой JOIN, WHERE, GROUP BY, HAVING и ORDER BY
- Поддержку строковых функций (UPPER, LOWER, TRIM, SUBSTRING, LPAD, RPAD, CONCAT)

Модуль не зависит от графического фреймворка: интерфейс (PyQt/PySide) должен вызывать функции из этого файла.
"""

from __future__ import annotations
import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

# -------- connection

def get_connection() -> PGConnection:
    conn = psycopg2.connect(
        host=os.getenv("PGHOST","localhost"),
        database=os.getenv("PGDATABASE","ai_experiments"),
        user=os.getenv("PGUSER","postgres"),
        password=os.getenv("PGPASSWORD","ShubinSQL228"),
        port=int(os.getenv("PGPORT","5432")),
    )
    conn.set_client_encoding('UTF8')
    return conn

# -------- utilities

class DBError(RuntimeError):
    pass

def _humanize_pg_error(e: Exception) -> str:
    msg = str(e)
    mapping = {
        "unique": "Нарушено ограничение UNIQUE.",
        "not-null": "Нарушено ограничение NOT NULL.",
        "foreign key": "Нарушено ограничение внешнего ключа (FOREIGN KEY).",
        "check constraint": "Нарушено ограничение CHECK.",
        "syntax": "Синтаксическая ошибка SQL.",
        "does not exist": "Объект не найден (таблица/столбец/ограничение).",
        "duplicate object": "Объект уже существует.",
        "invalid input syntax": "Неверный формат данных для указанного типа.",
        "cannot drop column": "Нельзя удалить столбец: существуют зависимости или ограничения.",
    }
    for k,v in mapping.items():
        if k in msg.lower():
            return f"{v} Детали: {msg}"
    return msg

# -------- introspection

def list_tables(conn: PGConnection, schemas: Optional[Sequence[str]]=None) -> List[Dict[str,Any]]:
    q = """
    select n.nspname as schema, c.relname as table, pg_total_relation_size(c.oid) as total_bytes
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where c.relkind = 'r' and n.nspname not in ('pg_catalog','information_schema')
    {schema_filter}
    order by 1,2;
    """
    schema_filter = ""
    args = []
    if schemas:
        schema_filter = "and n.nspname = any(%s)"
        args=[list(schemas)]
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q.format(schema_filter=schema_filter), args)
        return list(cur.fetchall())

def get_columns(conn: PGConnection, table: str, schema: str="public") -> List[Dict[str,Any]]:
    q = """
    select
        c.column_name,
        c.data_type,
        c.is_nullable = 'YES' as nullable,
        c.column_default,
        pgd.description as comment
    from information_schema.columns c
    left join pg_catalog.pg_statio_all_tables st on st.relname = c.table_name
    left join pg_catalog.pg_description pgd on pgd.objoid = st.relid and pgd.objsubid = c.ordinal_position
    where c.table_schema=%s and c.table_name=%s
    order by c.ordinal_position;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q,(schema,table))
        return list(cur.fetchall())

def get_constraints(conn: PGConnection, table: str, schema: str="public") -> List[Dict[str,Any]]:
    q = """
    select con.conname as name,
           con.contype as type,
           pg_get_constraintdef(con.oid) as definition
    from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace nsp on nsp.oid = connamespace
    where nsp.nspname=%s and rel.relname=%s
    order by 1;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q,(schema,table))
        rows = list(cur.fetchall())
        for r in rows:
            tmap = {'p':'PRIMARY KEY','u':'UNIQUE','f':'FOREIGN KEY','c':'CHECK'}
            r['type_verbose'] = tmap.get(r['type'], r['type'])
        return rows

def get_foreign_keys(conn: PGConnection, table: str, schema: str="public") -> List[Dict[str,Any]]:
    q = """
    select con.conname as name,
           pg_get_constraintdef(con.oid) as definition
    from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace nsp on nsp.oid = connamespace
    where con.contype='f' and nsp.nspname=%s and rel.relname=%s
    order by 1;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q,(schema,table))
        return list(cur.fetchall())
# -------- ALTER TABLE transactional API --------

@dataclass
class AlterAction:
    kind: Literal[
        "add_column", "drop_column", "rename_column", "rename_table",
        "alter_type", "set_not_null", "drop_not_null",
        "add_unique", "drop_constraint", "add_check",
        "add_foreign_key"
    ]
    table: str
    column: Optional[str] = None
    new_name: Optional[str] = None
    data_type: Optional[str] = None
    check_expr: Optional[str] = None
    ref_table: Optional[str] = None
    ref_column: Optional[str] = None
    constraint_name: Optional[str] = None
    cascade: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


def alter_table(conn: PGConnection, actions: Sequence[AlterAction]) -> str:
    """
    Выполняет несколько операций ALTER TABLE в одной транзакции.
    При ошибке все изменения откатываются.
    """
    commands = []
    for a in actions:
        t = sql.Identifier(a.table)
        if a.kind == "add_column":
            cmd = sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                t, sql.Identifier(a.column), sql.SQL(a.data_type))
        elif a.kind == "drop_column":
            cmd = sql.SQL("ALTER TABLE {} DROP COLUMN {} {}").format(
                t, sql.Identifier(a.column),
                sql.SQL("CASCADE") if a.cascade else sql.SQL(""))
        elif a.kind == "rename_column":
            cmd = sql.SQL("ALTER TABLE {} RENAME COLUMN {} TO {}").format(
                t, sql.Identifier(a.column), sql.Identifier(a.new_name))
        elif a.kind == "rename_table":
            cmd = sql.SQL("ALTER TABLE {} RENAME TO {}").format(
                t, sql.Identifier(a.new_name))
        elif a.kind == "alter_type":
            cmd = sql.SQL("ALTER TABLE {} ALTER COLUMN {} TYPE {}").format(
                t, sql.Identifier(a.column), sql.SQL(a.data_type))
        elif a.kind == "set_not_null":
            cmd = sql.SQL("ALTER TABLE {} ALTER COLUMN {} SET NOT NULL").format(
                t, sql.Identifier(a.column))
        elif a.kind == "drop_not_null":
            cmd = sql.SQL("ALTER TABLE {} ALTER COLUMN {} DROP NOT NULL").format(
                t, sql.Identifier(a.column))
        elif a.kind == "add_unique":
            cname = a.constraint_name or f"{a.table}_{a.column}_uniq"
            cmd = sql.SQL("ALTER TABLE {} ADD CONSTRAINT {} UNIQUE ({})").format(
                t, sql.Identifier(cname), sql.Identifier(a.column))
        elif a.kind == "add_check":
            cname = a.constraint_name or f"{a.table}_check_{abs(hash(a.check_expr))%9999}"
            cmd = sql.SQL("ALTER TABLE {} ADD CONSTRAINT {} CHECK ({})").format(
                t, sql.Identifier(cname), sql.SQL(a.check_expr))
        elif a.kind == "add_foreign_key":
            cname = a.constraint_name or f"{a.table}_{a.column}_fk"
            cmd = sql.SQL(
                "ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) REFERENCES {}({})"
            ).format(
                t, sql.Identifier(cname),
                sql.Identifier(a.column),
                sql.Identifier(a.ref_table),
                sql.Identifier(a.ref_column),
            )
        elif a.kind == "drop_constraint":
            cmd = sql.SQL("ALTER TABLE {} DROP CONSTRAINT {}").format(
                t, sql.Identifier(a.constraint_name))
        else:
            raise DBError(f"Неизвестный тип действия: {a.kind}")
        commands.append(cmd)

    cur = conn.cursor()
    try:
        for cmd in commands:
            cur.execute(cmd)
        conn.commit()
        return f"Успешно выполнено {len(commands)} изменений."
    except Exception as e:
        conn.rollback()
        msg = _humanize_pg_error(e)
        logging.exception("Ошибка ALTER TABLE: %s", msg)
        raise DBError(msg)
    finally:
        cur.close()
# -------- SELECT Query Builder --------

@dataclass
class SelectParams:
    tables: List[str]
    columns: List[str] = field(default_factory=list)
    joins: List[Dict[str, Any]] = field(default_factory=list)  # [{'type':'LEFT','table':'b','on':'a.id=b.a_id'}]
    where: List[Dict[str, Any]] = field(default_factory=list)  # [{'col':'x','op':'=','val':1}]
    group_by: List[str] = field(default_factory=list)
    having: List[Dict[str, Any]] = field(default_factory=list)
    order_by: List[Tuple[str, Literal['ASC','DESC']]] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None


def build_select_sql(p: SelectParams) -> Tuple[str, List[Any]]:
    """
    Собирает SQL-запрос SELECT с поддержкой JOIN, WHERE, GROUP BY, HAVING и ORDER BY.
    Возвращает текст запроса и список аргументов.
    """
    parts = ["SELECT"]
    if p.columns:
        parts.append(", ".join(p.columns))
    else:
        parts.append("*")

    parts.append("FROM " + ", ".join(p.tables))

    # JOIN
    for j in p.joins:
        jtype = j.get("type","INNER").upper()
        parts.append(f"{jtype} JOIN {j['table']} ON {j['on']}")

    # WHERE
    args: List[Any] = []
    if p.where:
        wh = []
        for cond in p.where:
            op = cond.get("op","=").strip().upper()
            val = cond.get("val")
            if op in ["LIKE","ILIKE","~","~*","!~","!~*"]:
                wh.append(f"{cond['col']} {op} %s")
            else:
                wh.append(f"{cond['col']} {op} %s")
            args.append(val)
        parts.append("WHERE " + " AND ".join(wh))

    # GROUP BY
    if p.group_by:
        parts.append("GROUP BY " + ", ".join(p.group_by))

    # HAVING
    if p.having:
        hv = []
        for cond in p.having:
            hv.append(f"{cond['col']} {cond['op']} %s")
            args.append(cond['val'])
        parts.append("HAVING " + " AND ".join(hv))

    # ORDER BY
    if p.order_by:
        ob = [f"{col} {dir}" for col, dir in p.order_by]
        parts.append("ORDER BY " + ", ".join(ob))

    # LIMIT / OFFSET
    if p.limit is not None:
        parts.append("LIMIT %s")
        args.append(p.limit)
    if p.offset is not None:
        parts.append("OFFSET %s")
        args.append(p.offset)

    query = " ".join(parts)
    return query, args


def execute_select(conn: PGConnection, params: SelectParams) -> List[Dict[str, Any]]:
    """Выполняет запрос, собранный build_select_sql."""
    sql_text, args = build_select_sql(params)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql_text, args)
            return list(cur.fetchall())
    except Exception as e:
        msg = _humanize_pg_error(e)
        raise DBError(msg)
# -------- String functions utilities --------

VALID_STRING_FUNCS = {
    "UPPER": "UPPER({col})",
    "LOWER": "LOWER({col})",
    "TRIM": "TRIM({col})",
    "SUBSTRING": "SUBSTRING({col} FROM %s FOR %s)",  # extra args: start, length
    "LPAD": "LPAD({col}, %s, %s)",                   # extra args: length, fill
    "RPAD": "RPAD({col}, %s, %s)",
    "CONCAT": "CONCAT({col}, %s)",                   # extra arg: suffix/prefix
}


def apply_string_func(
    conn: PGConnection,
    table: str,
    column: str,
    func: str,
    *extra_args: Any
) -> List[Dict[str, Any]]:
    """
    Применяет строковую функцию (UPPER, LOWER, TRIM, SUBSTRING, LPAD, RPAD, CONCAT)
    к указанному столбцу таблицы и возвращает результат в виде списка словарей.
    """
    func = func.upper().strip()
    if func not in VALID_STRING_FUNCS:
        raise DBError(f"Неизвестная строковая функция: {func}")

    expr_template = VALID_STRING_FUNCS[func]
    expr = expr_template.format(col=sql.Identifier(column).as_string(conn))

    q = sql.SQL("SELECT {}, {} FROM {}").format(
        sql.Identifier(column),
        sql.SQL(expr + " AS transformed"),
        sql.Identifier(table)
    )

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(q, extra_args)
            return list(cur.fetchall())
    except Exception as e:
        msg = _humanize_pg_error(e)
        raise DBError(msg)


# -------- Combined API for GUI calls --------

def preview_table(conn: PGConnection, table: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Возвращает первые N строк указанной таблицы (для предпросмотра)."""
    q = sql.SQL("SELECT * FROM {} LIMIT %s").format(sql.Identifier(table))
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, (limit,))
        return list(cur.fetchall())


def safe_execute(conn: PGConnection, query: str, args: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """
    Универсальное выполнение SQL-запроса с возвратом данных (используется GUI для произвольных запросов).
    """
    args = args or []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, args)
            if cur.description:
                return list(cur.fetchall())
            conn.commit()
            return []
    except Exception as e:
        conn.rollback()
        msg = _humanize_pg_error(e)
        raise DBError(msg)
# -------- Logging / diagnostics --------

def configure_logging(level: int = logging.INFO) -> None:
    """Базовая настройка логирования модуля."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt)


def ping(conn: PGConnection) -> bool:
    """Проверка соединения с БД."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False


def explain_select(conn: PGConnection, params: SelectParams) -> List[str]:
    """
    Возвращает план выполнения запроса (EXPLAIN) для визуальной отладки в GUI.
    """
    q, args = build_select_sql(params)
    try:
        with conn.cursor() as cur:
            cur.execute("EXPLAIN " + q, args)
            return [r[0] for r in cur.fetchall()]
    except Exception as e:
        raise DBError(_humanize_pg_error(e))


# -------- Convenience helpers for GUI --------

def list_all_schema_objects(conn: PGConnection, schema: str = "public") -> Dict[str, Any]:
    """Сводная информация по схеме: таблицы, столбцы, ограничения."""
    result: Dict[str, Any] = {"tables": []}
    for t in [r["table"] for r in list_tables(conn, [schema])]:
        result["tables"].append({
            "name": t,
            "columns": get_columns(conn, t, schema),
            "constraints": get_constraints(conn, t, schema),
            "foreign_keys": get_foreign_keys(conn, t, schema),
        })
    return result


def begin(conn: PGConnection):
    """Явный старт транзакции (для цепочек операций из GUI)."""
    with conn.cursor() as cur:
        cur.execute("BEGIN")


def commit(conn: PGConnection):
    """Фиксация транзакции (для цепочек операций из GUI)."""
    conn.commit()


def rollback(conn: PGConnection):
    """Откат транзакции (для цепочек операций из GUI)."""
    conn.rollback()


# -------- Public API --------

__all__ = [
    # подключение
    "get_connection", "DBError", "configure_logging", "ping",
    # интроспекция
    "list_tables", "get_columns", "get_constraints", "get_foreign_keys",
    "list_all_schema_objects",
    # ALTER TABLE
    "AlterAction", "alter_table",
    # SELECT builder
    "SelectParams", "build_select_sql", "execute_select", "explain_select",
    # строки
    "VALID_STRING_FUNCS", "apply_string_func",
    # util транзакций
    "begin", "commit", "rollback",
    # произвольный запрос
    "safe_execute",
]

