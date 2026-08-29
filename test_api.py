"""API 自动化测试：对 JSONPlaceholder 的 CRUD 接口做四类用例。

四类用例：
1. 正常用例：GET /posts 返回 200 且返回 100 条数据
2. 边界用例：最小 ID / 最大 ID
3. 异常用例：不存在的 ID 返回 404、空 body
4. 鉴权用例：无凭证访问受保护接口返回 401（用 httpbin 演示）

每条用例执行后结果写入 SQLite（test_results.db），运行完可用 report.py 生成摘要。

运行：pytest -v
"""
import pytest
import requests
import db
from api_client import get, post

# httpbin 的 basic-auth 端点：需要 Basic Auth，无凭证返回 401
AUTH_URL = "https://httpbin.org/basic-auth/user/passwd"


def check(conn, name, category, cond, http_status, detail=""):
    """先记录结果到 SQLite，再断言。这样 FAIL 的用例也会入库。"""
    db.record(conn, name, category, "PASS" if cond else "FAIL", http_status, detail)
    assert cond, name + " 失败（HTTP " + str(http_status) + "）"


@pytest.fixture(scope="module")
def conn():
    c = db.init_db()
    yield c
    c.close()


# ---------- 1. 正常用例 ----------
def test_get_posts_ok(conn):
    r = get("/posts")
    data = r.json()
    check(conn, "GET /posts 返回全部文章", "正常",
          r.status_code == 200 and isinstance(data, list) and len(data) == 100,
          r.status_code)


# ---------- 2. 边界用例 ----------
def test_get_first_post(conn):
    r = get("/posts/1")
    check(conn, "GET /posts/1 最小 ID 边界", "边界",
          r.status_code == 200 and r.json().get("id") == 1, r.status_code)


def test_get_last_post(conn):
    r = get("/posts/100")
    check(conn, "GET /posts/100 最大 ID 边界", "边界",
          r.status_code == 200 and r.json().get("id") == 100, r.status_code)


# ---------- 3. 异常用例 ----------
def test_get_nonexistent_post(conn):
    r = get("/posts/99999")
    check(conn, "GET /posts/99999 不存在的 ID", "异常",
          r.status_code == 404, r.status_code)


def test_post_empty_payload(conn):
    r = post("/posts", {})
    check(conn, "POST /posts 空 body", "异常",
          r.status_code in (200, 201, 400), r.status_code,
          detail="实际返回 " + str(r.status_code))


# ---------- 4. 鉴权用例 ----------
def test_auth_required(conn):
    r = requests.get(AUTH_URL, timeout=10)
    check(conn, "无凭证访问受保护接口", "鉴权",
          r.status_code == 401, r.status_code)


def test_auth_success(conn):
    r = requests.get(AUTH_URL, auth=("user", "passwd"), timeout=10)
    check(conn, "正确凭证访问受保护接口", "鉴权",
          r.status_code == 200, r.status_code)
