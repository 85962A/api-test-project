"""读 SQLite 生成测试摘要（按类别统计 PASS/FAIL）。

只统计「最新一次运行批次」，避免历史结果累加（修复 TAPD BUG-001）。

运行：python report.py
"""
import sqlite3

import db


def summary(path=db.DB_PATH):
    conn = sqlite3.connect(str(path))

    row = conn.execute(
        "SELECT run_id FROM results WHERE run_id IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if row is None:  # 兼容没有批次号的旧数据
        batch_label = "（旧数据：无批次号）"
        cond, args = "", ()
    else:
        rid = row[0]
        span = conn.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM results WHERE run_id=?", (rid,)
        ).fetchone()
        batch_label = rid + "  " + str(span[0]) + " ~ " + str(span[1])
        cond, args = " WHERE run_id=?", (rid,)

    total = conn.execute("SELECT COUNT(*) FROM results" + cond, args).fetchone()[0]
    passed = conn.execute(
        "SELECT COUNT(*) FROM results" + (cond + " AND" if cond else " WHERE") + " status='PASS'", args
    ).fetchone()[0]
    failed = conn.execute(
        "SELECT COUNT(*) FROM results" + (cond + " AND" if cond else " WHERE") + " status='FAIL'", args
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT category, status, COUNT(*) FROM results" + cond +
        " GROUP BY category, status ORDER BY category", args
    ).fetchall()
    conn.close()

    print("=" * 52)
    print("API 自动化测试摘要（仅本次运行批次）")
    print("=" * 52)
    print("运行批次：" + batch_label)
    print("总用例数：" + str(total) + "   通过：" + str(passed) + "   失败：" + str(failed))
    print("-" * 52)
    for category, status, cnt in rows:
        print("  " + category.ljust(4) + " | " + status.ljust(4) + " | " + str(cnt) + " 条")
    print("=" * 52)
    return {"total": total, "passed": passed, "failed": failed, "run_id": None if row is None else row[0]}


if __name__ == "__main__":
    summary()
