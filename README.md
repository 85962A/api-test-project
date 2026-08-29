# API 自动化测试与数据校验工具

一个用 Python 对公开 REST API 做四类用例测试、并把结果落库生成摘要的小项目。

## 技术选型

- **Python 3**：脚本与断言逻辑
- **pytest**：测试框架
- **requests**：HTTP 请求
- **sqlite3**（标准库）：结果落库

## 目录结构

    api-test-project/
    ├── api_client.py     # 封装 HTTP 请求（统一 base_url、超时）
    ├── test_api.py       # pytest 测试用例（四类）
    ├── db.py             # SQLite 存储测试结果
    ├── report.py         # 生成测试摘要
    ├── requirements.txt  # 依赖
    └── README.md         # 本文档

## 运行方法

    # 1. 安装依赖
    pip install -r requirements.txt

    # 2. 运行测试（每条结果自动写入 test_results.db）
    pytest -v

    # 3. 生成测试摘要
    python report.py

## 四类测试用例设计

| 类别 | 用例 | 预期 |
|---|---|---|
| 正常 | GET /posts 返回全部文章 | 200，返回 100 条 |
| 边界 | GET /posts/1、/posts/100（最小/最大 ID） | 200，id 正确 |
| 异常 | GET /posts/99999（不存在 ID） | 404 |
| 异常 | POST /posts 空 body | 记录实际返回 |
| 鉴权 | 无凭证访问受保护接口 | 401 |
| 鉴权 | 正确凭证访问 | 200 |

## 测试对象

- 主对象：JSONPlaceholder（https://jsonplaceholder.typicode.com ，免费假 REST API）
- 鉴权演示：httpbin.org（https://httpbin.org/basic-auth/user/passwd ）

## 设计说明

- **api_client.py** 把 base_url 和超时集中管理，接口地址变更时只改一处。
- **check()** 先写库再断言，保证失败的用例也会被记录，便于复盘。
- 结果落 SQLite，便于后续按类别统计、生成趋势。
