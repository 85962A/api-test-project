"""SQLite 存储测试结果，供 report.py 生成摘要。

表结构：results(id, run_id, case_name, category, status, http_status, detail, created_at)

两处修复（对应 TAPD 缺陷）：
- BUG-001：新增 run_id 运行批次号，report.py 只统计最新批次，避免历史结果累加（21 条被统计成 42 条）
- BUG-002：DB_PATH 改为绝对路径，无论从哪个目录执行 pytest，结果都写进项目内的库
"""
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

# 绝对路径：修复「跨目录运行会写到另一份 test_results.db」
DB_PATH = Path(__file__).resolve().parent / "test_results.db"

_RUN_ID = None


def current_run_id():
    """本次运行的批次号（同一进程内唯一）。"""
    global _RUN_ID
    if _RUN_ID is None:
        _RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    return _RUN_ID


def init_db(path=DB_PATH):
    """建表并返回连接（库已存在则复用；旧库自动补 run_id 列）。"""
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            case_name TEXT,
            category TEXT,
            status TEXT,
            http_status INTEGER,
            detail TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    # 兼容早期版本建的旧表（没有 run_id 列）
    cols = [row[1] for row in conn.execute("PRAGMA table_info(results)")]
    if "run_id" not in cols:
        conn.execute("ALTER TABLE results ADD COLUMN run_id TEXT")
    conn.commit()
    return conn


def record(conn, case_name, category, status, http_status, detail=""):
    """写入一条测试结果（带本次运行批次号）。"""
    conn.execute(
        "INSERT INTO results (run_id, case_name, category, status, http_status, detail) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (current_run_id(), case_name, category, status, http_status, detail),
    )
    conn.commit()
