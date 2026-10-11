"""接口安全测试用例（8 条）—— 用公开测试接口演示「安全测试思维」。

⚠️ 底线（只允许这三类目标，见 `网络安全转型执行手册` 第八节）：
   ① 公开测试接口（httpbin.org / jsonplaceholder 这类**专供测试**的站点）
   ② 自己搭建的本地环境
   ③ 取得书面授权的资产
   绝不对任何未授权目标做扫描、探测或数据获取。

设计说明：本文件沿用项目既有的「先入库再断言」机制（db.record），
把安全用例的结果和功能用例一起落进同一张表，便于按类别统计。

运行：pytest test_api_security.py -v
"""
import pytest

import db
from api_client import get_url

AUTH_URL = "https://httpbin.org/basic-auth/user/passwd"
OTHER_USER_URL = "https://httpbin.org/basic-auth/admin/secret"
INJECT_URL = "https://httpbin.org/get"
JSON_API = "https://jsonplaceholder.typicode.com"


def check(conn, name, cond, http_status, detail=""):
    """先记录到 SQLite，再断言 —— 失败的用例也会入库（沿用项目既有机制）。"""
    db.record(conn, name, "安全", "PASS" if cond else "FAIL", http_status, detail)
    assert cond, name + " 失败（HTTP " + str(http_status) + "）：" + str(detail)


@pytest.fixture(scope="module")
def conn():
    c = db.init_db()
    yield c
    c.close()


# ---------- 1. 认证：未授权访问 ----------
def test_unauthorized_access_blocked(conn):
    """不带凭证访问受保护接口 → 必须 401，不能放行。"""
    r = get_url(AUTH_URL)
    check(conn, "未授权访问受保护接口应 401", r.status_code == 401, r.status_code,
          "实际 " + str(r.status_code))


# ---------- 2. 认证：错误凭证 ----------
def test_wrong_credentials_rejected(conn):
    """错误凭证 → 401。"""
    r = get_url(AUTH_URL, auth=("user", "wrong-password"))
    check(conn, "错误凭证应 401", r.status_code == 401, r.status_code,
          "实际 " + str(r.status_code))


# ---------- 3. 认证：正确凭证（对照组，证明前两条有效） ----------
def test_valid_credentials_pass(conn):
    """正确凭证 → 200。没有这条对照组，前两条断言可能是假阳性。"""
    r = get_url(AUTH_URL, auth=("user", "passwd"))
    check(conn, "正确凭证应 200（对照组）", r.status_code == 200, r.status_code,
          "实际 " + str(r.status_code))


# ---------- 4. 授权：横向越权（用低权凭证访问他人资源） ----------
def test_horizontal_privilege_escalation(conn):
    """拿「user」的凭证去访问属于「admin」的资源 → 必须被拒（401/403）。

    这是横向越权的最小模型：身份合法，但**资源不属于他**。
    """
    r = get_url(OTHER_USER_URL, auth=("user", "passwd"))
    check(conn, "横向越权：用他人凭证访问他人资源应被拒",
          r.status_code in (401, 403), r.status_code, "实际 " + str(r.status_code))


# ---------- 5. 注入：SQL 注入探针 ----------
def test_sql_injection_probe(conn):
    """参数传入 `' OR 1=1--` → 不得返回 5xx，也不得回显数据库报错。

    注意：这里判的是「没有暴露出注入痕迹」，不是「证明了不存在注入」——
    真正的注入验证需要在自建环境上做更系统的测试。
    """
    payload = "' OR 1=1--"
    r = get_url(INJECT_URL, params={"q": payload})
    body = r.text.lower()
    leaked = [k for k in ("sql syntax", "mysql", "sqlite", "ora-", "syntax error",
                          "unclosed quotation", "odbc") if k in body]
    check(conn, "SQL 注入探针不应触发 5xx 或回显数据库报错",
          r.status_code < 500 and not leaked, r.status_code,
          "状态 " + str(r.status_code) + " 泄漏关键字 " + str(leaked))


# ---------- 6. 健壮性：异常/越界输入 ----------
def test_abnormal_input_robustness(conn):
    """超大/非法 ID → 应 4xx 而不是 5xx（异常输入不能把服务打崩）。"""
    r = get_url(JSON_API + "/posts/99999999999999999999")
    check(conn, "异常输入（超大 ID）应 4xx 而非 5xx",
          400 <= r.status_code < 500, r.status_code, "实际 " + str(r.status_code))


# ---------- 7. 信息泄露：凭证不得回显 ----------
def test_credential_not_echoed(conn):
    """服务端不应把请求携带的凭证明文回显到响应体。"""
    secret = "s3cr3t-passwd-do-not-echo"
    r = get_url(JSON_API + "/posts/1", auth=("user", secret))
    check(conn, "响应体不应回显请求凭证", secret not in r.text, r.status_code,
          "响应长度 " + str(len(r.text)))


# ---------- 8. 安全响应头检查（记录型，缺失不算失败） ----------
def test_security_headers_recorded(conn):
    """检查常见安全响应头是否配置，并把缺失项记录进库。

    这条**故意不判失败** —— 因为公共测试站本来就不会配，
    它的价值是「把缺失项落库」，作为你给业务系统做安全测试时的检查模板。
    """
    r = get_url(JSON_API + "/posts/1")
    have = {k.lower() for k in r.headers}
    want = ["x-frame-options", "x-content-type-options", "content-security-policy",
            "strict-transport-security"]
    missing = [w for w in want if w not in have]
    check(conn, "记录目标站安全响应头缺失情况", True, r.status_code,
          "已配置 " + str(sorted(set(want) & have)) + " ｜ 缺失 " + str(missing))
