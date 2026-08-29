"""封装 HTTP 请求：统一 base_url 与超时，便于维护和复用。

用法：
    from api_client import get, post
    r = get("/posts")
"""
import requests

BASE_URL = "https://jsonplaceholder.typicode.com"


def get(path):
    """发送 GET 请求。"""
    return requests.get(BASE_URL + path, timeout=10)


def post(path, data):
    """发送 POST 请求（JSON body）。"""
    return requests.post(BASE_URL + path, json=data, timeout=10)
