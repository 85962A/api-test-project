"""读 SQLite 生成测试摘要（按类别统计 PASS/FAIL）。

运行：python report.py
"""
import sqlite3
import db


def summary(path=db.DB_PATH):
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT category, status, COUNT(*) FROM results GROUP BY category, status ORDER BY category"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    passed = conn.execute("SELECT COUNT(*) FROM results WHERE status='PASS'").fetchone()[0]
    failed = conn.execute("SELECT COUNT(*) FROM results WHERE status='FAIL'").fetchone()[0]
    conn.close()

    print("=" * 52)
    print("API 自动化测试摘要")
    print("=" * 52)
    print("总用例数：" + str(total) + "   通过：" + str(passed) + "   失败：" + str(failed))
    print("-" * 52)
    for category, status, cnt in rows:
        print("  " + category.ljust(4) + " | " + status.ljust(4) + " | " + str(cnt) + " 条")
    print("=" * 52)
    return {"total": total, "passed": passed, "failed": failed}


if __name__ == "__main__":
    summary()
