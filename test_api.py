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

import db
from api_client import get, get_url, post

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
    # BUG-003 修复：原来断言 in (200, 201, 400) 等于三种结果都放行、失去检出能力
    # 现收紧为唯一预期 201，并校验响应体含 id（实测：{} 与 null 均返回 201 + {"id": 101}）
    r = post("/posts", {})
    body = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
    check(conn, "POST /posts 空 body", "异常",
          r.status_code == 201 and isinstance(body, dict) and body.get("id") is not None,
          r.status_code,
          detail="期望 201 且响应体含 id，实际 " + str(r.status_code))


# ---------- 4. 鉴权用例 ----------
def test_auth_required(conn):
    r = get_url(AUTH_URL)  # 走 api_client 的重试封装（BUG-006）
    check(conn, "无凭证访问受保护接口", "鉴权",
          r.status_code == 401, r.status_code)


def test_auth_success(conn):
    r = get_url(AUTH_URL, auth=("user", "passwd"))  # 走重试封装（BUG-006）
    check(conn, "正确凭证访问受保护接口", "鉴权",
          r.status_code == 200, r.status_code)
