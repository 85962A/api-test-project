"""单元测试（白盒）：只测 db 模块的纯逻辑，不碰网络。

用途：演示「单元测试 + 覆盖率」——面试被问白盒时，这是可运行的实证。

与接口测试的区别：
- 本文件：只测函数、不联网、毫秒级（`tmp_path` 隔离，不污染真实 test_results.db）
- test_api*.py：走真实 HTTP、加重试防抖动

运行：pytest test_unit.py -v --cov=db --cov-report=term-missing
"""
import sqlite3

import db


def test_current_run_id_format():
    """run_id 格式：YYYYMMDD-HHMMSS-xxxxxx（3 段）。"""
    rid = db.current_run_id()
    parts = rid.split("-")
    assert isinstance(rid, str) and len(parts) == 3
    assert len(parts[0]) == 8 and len(parts[1]) == 6 and len(parts[2]) == 6
    assert parts[0].isdigit() and parts[1].isdigit()


def test_init_db_creates_table_and_is_idempotent(tmp_path):
    """建表成功，且重复调用不报错（幂等）。"""
    p = tmp_path / "unit.db"
    conn = db.init_db(path=p)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='results'"
    ).fetchall()
    assert len(rows) == 1                      # 表 results 已建
    conn.close()

    conn2 = db.init_db(path=p)                 # 再 init 一次，不抛异常 = 幂等
    conn2.close()


def test_record_writes_a_row(tmp_path):
    """record 写入后能查回，且字段顺序正确。"""
    p = tmp_path / "unit.db"
    conn = db.init_db(path=p)
    db.record(conn, "用例X", "白盒", "PASS", 200, "ok")
    row = conn.execute(
        "SELECT case_name, category, status, http_status FROM results"
    ).fetchone()
    assert row == ("用例X", "白盒", "PASS", 200)
    conn.close()


def test_init_db_migrates_legacy_table(tmp_path):
    """旧表（无 run_id 列）也能被 init_db 自动补列 —— 专门覆盖 ALTER 分支。

    这一条是「语句覆盖 vs 分支覆盖」的活教材：
    删掉它，db.py 的覆盖率看着仍然很高，但 `if "run_id" not in cols` 的
    ALTER 分支就永远跑不到 —— 语句覆盖满、分支覆盖不满。
    """
    p = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(p))
    conn.execute(
        "CREATE TABLE results (id INTEGER PRIMARY KEY, case_name TEXT, status TEXT)"
    )
    conn.commit()
    conn.close()

    conn2 = db.init_db(path=p)                 # 应自动 ALTER TABLE 加 run_id 列
    cols = [r[1] for r in conn2.execute("PRAGMA table_info(results)")]
    assert "run_id" in cols
    conn2.close()
