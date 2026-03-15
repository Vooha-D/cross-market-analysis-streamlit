# db.py
import sqlite3
import pandas as pd
from contextlib import contextmanager

DB_PATH = "cross_market.db"

@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        yield conn
    finally:
        conn.close()

def read_df(sql: str, params: tuple = ()):  # returns DataFrame
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params, parse_dates=["date"]) if "date" in sql.lower() else pd.read_sql_query(sql, conn, params=params)

def read_value(sql: str, params: tuple = ()):  # returns scalar
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return None if row is None else row[0]

def execute(sql: str, params: tuple = ()):  # for non-select
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()

# Helpers for min/max dates

def table_min_max_date(table: str, where: str = "", params: tuple = ()):  # returns (min_date, max_date)
    sql = f"SELECT MIN(date), MAX(date) FROM {table} " + (f"WHERE {where}" if where else "")
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
    return row[0], row[1]

