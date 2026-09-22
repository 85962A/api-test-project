"""封装 HTTP 请求：统一 base_url 与超时，并对外部接口做有限次重试。

为什么要重试：本项目用例依赖 jsonplaceholder / httpbin 等外部实时接口，
网络抖动（超时、连接重置）会制造「假失败」，让 CI 红绿随机（见 TAPD BUG-006）。

用法：
    from api_client import get, post, get_url
    r = get("/posts")
"""
import time

import requests

BASE_URL = "https://jsonplaceholder.typicode.com"

RETRIES = 3          # 最多尝试次数
BACKOFF = 1.0        # 退避基数（秒）


def request_with_retry(method, url, **kwargs):
    """带重试的请求：仅在连接类异常（ConnectionError / Timeout）时重试，返回最后一次响应。"""
    kwargs.setdefault("timeout", 10)
    last_exc = None
    for attempt in range(1, RETRIES + 1):
        try:
            return requests.request(method, url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < RETRIES:
                time.sleep(BACKOFF * attempt)
    raise last_exc


def get(path):
    """发送 GET 请求（相对 BASE_URL）。"""
    return request_with_retry("GET", BASE_URL + path)


def post(path, data):
    """发送 POST 请求（JSON body，相对 BASE_URL）。"""
    return request_with_retry("POST", BASE_URL + path, json=data)


def get_url(url, **kwargs):
    """发送绝对 URL 的 GET 请求（用于 httpbin 等第三方端点，同样带重试）。"""
    return request_with_retry("GET", url, **kwargs)
