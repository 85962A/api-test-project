"""AI 辅助生成的参数化测试用例（初稿，人工校验后合入）。

来源：使用 AI 编程助手（DeepSeek）分析 test_api.py 后生成的重构建议，
人工逐条校验边界条件与预期值后合入，作为「利用 LLM 生成测试用例」的真实实践。

优化点：
1. 用 pytest.mark.parametrize 参数化，消除重复用例代码，覆盖更多边界值；
2. 保留「先入库再断言」的留痕机制（复用 db.record / api_client）。

运行：pytest test_api_parametrized.py -v
"""
import pytest
import requests
import db
from api_client import get, post

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


# ---------- 1. 正常用例（参数化：正常列表 + 单条资源） ----------
@pytest.mark.parametrize("path, expect_len", [
    ("/posts", 100),      # 正常：返回全部 100 条
    ("/comments", 500),   # 正常：comments 资源完整返回
])
def test_list_resources_ok(conn, path, expect_len):
    r = get(path)
    data = r.json()
    check(conn, f"GET {path} 正常返回", "正常",
          r.status_code == 200 and isinstance(data, list) and len(data) == expect_len,
          r.status_code)


# ---------- 2. 边界用例（参数化：最小/最大/越界 ID） ----------
@pytest.mark.parametrize("post_id, expect_status, expect_id", [
    (1, 200, 1),        # 边界：最小 ID
    (100, 200, 100),    # 边界：最大 ID
    (101, 404, None),   # 边界：刚越界（>100 不存在）
    (0, 404, None),     # 边界：非正数 ID
])
def test_post_id_boundaries(conn, post_id, expect_status, expect_id):
    r = get(f"/posts/{post_id}")
    ok = r.status_code == expect_status
    if expect_id is not None:
        ok = ok and r.json().get("id") == expect_id
    check(conn, f"GET /posts/{post_id} 边界", "边界",
          ok, r.status_code, detail=f"期望 {expect_status}")


# ---------- 3. 异常用例（参数化：不存在资源 + 空 body + 非法方法） ----------
@pytest.mark.parametrize("path", ["/posts/99999", "/posts/-1", "/users/0"])
def test_get_nonexistent(conn, path):
    r = get(path)
    check(conn, f"GET {path} 不存在资源", "异常",
          r.status_code == 404, r.status_code)


@pytest.mark.parametrize("payload", [{}, None])
def test_post_empty_payload(conn, payload):
    r = post("/posts", payload)
    check(conn, f"POST /posts 空 body ({payload!r})", "异常",
          r.status_code in (200, 201, 400), r.status_code,
          detail="实际返回 " + str(r.status_code))


# ---------- 4. 鉴权用例（参数化：无凭证 / 错误凭证 / 正确凭证） ----------
@pytest.mark.parametrize("auth, expect_status", [
    (None, 401),                       # 鉴权：无凭证 → 401
    (("user", "wrong"), 401),          # 鉴权：错误凭证 → 401
    (("user", "passwd"), 200),         # 鉴权：正确凭证 → 200
])
def test_basic_auth(conn, auth, expect_status):
    r = requests.get(AUTH_URL, auth=auth, timeout=10)
    check(conn, f"Basic Auth ({'无凭证' if auth is None else auth[1]})", "鉴权",
          r.status_code == expect_status, r.status_code,
          detail=f"期望 {expect_status}")
