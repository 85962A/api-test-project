"""SQLite 存储测试结果，供 report.py 生成摘要。

表结构：results(id, case_name, category, status, http_status, detail, created_at)
"""
import sqlite3

DB_PATH = "test_results.db"


def init_db(path=DB_PATH):
    """建表并返回连接（若库已存在则复用）。"""
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_name TEXT,
            category TEXT,
            status TEXT,
            http_status INTEGER,
            detail TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.commit()
    return conn


def record(conn, case_name, category, status, http_status, detail=""):
    """写入一条测试结果。"""
    conn.execute(
        "INSERT INTO results (case_name, category, status, http_status, detail) "
        "VALUES (?, ?, ?, ?, ?)",
        (case_name, category, status, http_status, detail),
    )
    conn.commit()
