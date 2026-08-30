"""最小压测脚本：对 JSONPlaceholder 公开 API 做并发负载测试。

不依赖 locust，只用标准库 concurrent.futures + requests：
起 N 个并发 worker 循环请求三类接口（正常 / 边界 / 异常），
按「实际状态码是否命中预期」判定成败（异常场景预期 404，算命中），
统计命中率、响应时间（平均 / 最小 / 最大 / P95）与状态码分布。

用法：
    python stress_test.py [并发数] [总请求数]
    例：python stress_test.py 50 200   # 50 并发、共 200 个请求
"""
import sys
import time
import statistics
import concurrent.futures

import requests

BASE_URL = "https://jsonplaceholder.typicode.com"

# 三类场景（名称, 地址, 预期状态码）
TARGETS = [
    ("GET /posts", BASE_URL + "/posts", 200),              # 正常：全部文章
    ("GET /posts/1", BASE_URL + "/posts/1", 200),          # 边界：最小 ID
    ("GET /posts/99999", BASE_URL + "/posts/99999", 404),  # 异常：不存在资源，预期 404
]


def hit(name, url, expected):
    """单次请求，返回 (名称, 状态码, 是否命中预期, 耗时ms, 异常信息)。"""
    start = time.perf_counter()
    try:
        r = requests.get(url, timeout=10)
        return name, r.status_code, r.status_code == expected, \
            (time.perf_counter() - start) * 1000, None
    except Exception as exc:  # 网络错误 / 超时
        return name, 0, False, (time.perf_counter() - start) * 1000, str(exc)


def p95(values):
    """第 95 百分位响应时间。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(int(len(ordered) * 0.95), len(ordered) - 1)]


def run(concurrency=50, total=200):
    urls = [TARGETS[i % len(TARGETS)] for i in range(total)]
    results = []

    start_all = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(hit, name, url, exp) for name, url, exp in urls]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    wall_seconds = time.perf_counter() - start_all

    hit_ok = [r for r in results if r[2]]           # 命中预期状态
    miss = [r for r in results if not r[2]]          # 未命中（含网络错误）
    net_err = [r for r in results if r[1] == 0]      # 网络错误
    latencies = [r[3] for r in results]

    status_dist = {}
    for r in results:
        status_dist[r[1]] = status_dist.get(r[1], 0) + 1

    print("=" * 62)
    print("API 最小压测结果（并发 %d，总请求 %d）" % (concurrency, total))
    print("=" * 62)
    print("命中预期状态：%d    未命中：%d    命中率：%.1f%%" % (
        len(hit_ok), len(miss), len(hit_ok) / total * 100))
    print("其中网络错误：%d 个" % len(net_err))
    print("总耗时：%.2f 秒    吞吐：%.1f req/s" % (wall_seconds, total / wall_seconds))
    print("-" * 62)
    print("响应时间(ms)：平均 %.1f  最小 %.1f  最大 %.1f  P95 %.1f" % (
        statistics.mean(latencies), min(latencies), max(latencies), p95(latencies)))
    print("状态码分布：" + ", ".join(
        "%s=%d" % (k, v) for k, v in sorted(status_dist.items())))
    if miss:
        print("未命中明细(前 5 条)：" + "; ".join(str(r) for r in miss[:5]))
    print("=" * 62)
    return results


if __name__ == "__main__":
    c = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    run(c, n)
