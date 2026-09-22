# API 自动化测试与数据校验工具

[![API 自动化测试](https://github.com/85962A/api-test-project/actions/workflows/tests.yml/badge.svg)](https://github.com/85962A/api-test-project/actions/workflows/tests.yml)

一个用 Python 对公开 REST API 做四类用例测试、把结果落库生成摘要，并接入 **CI/CD** 与 **缺陷管理** 流程的小项目。

- **21 条接口自动化用例**（7 组场景 + 14 条参数化变体）→ **每次 push 自动执行**（GitHub Actions）
- **测试结果落 SQLite**，按运行批次（`run_id`）隔离，支持按类别统计与复盘
- 迁移到 AI 测试：`ai_eval.py` 用「事实性 + 来源可验证性」两个指标给 LLM 回答打分

## 技术选型

- **Python 3.12**：脚本与断言逻辑
- **pytest**：测试框架（含 `parametrize` 参数化）
- **requests**：HTTP 请求（封装了超时与有限次重试）
- **sqlite3**（标准库）：结果落库
- **GitHub Actions**：持续集成（提交即验证 + 报告归档）

## 目录结构

    api-test-project/
    ├── .github/workflows/tests.yml   # CI：push/PR 触发 pytest，归档 JUnit 报告与摘要
    ├── api_client.py                 # 封装 HTTP 请求（统一 base_url、超时、重试）
    ├── test_api.py                   # 7 组手工设计的用例（正常/边界/异常/鉴权）
    ├── test_api_parametrized.py      # 14 条参数化变体（pytest.mark.parametrize）
    ├── db.py                         # SQLite 存储测试结果（按 run_id 批次隔离）
    ├── report.py                     # 生成测试摘要（只统计最新批次）
    ├── ai_eval.py                    # AI 评测模块（LLM 回答质量打分）
    ├── stress_test.py                # 最小并发压测脚本
    ├── requirements.txt              # 依赖
    ├── .env.example                  # AI 评测所需环境变量示例（复制为 .env 后填 Key）
    └── README.md                     # 本文档

## 运行方法

    # 1. 安装依赖
    pip install -r requirements.txt

    # 2. 运行测试（21 条；每条结果自动写入 test_results.db）
    pytest -v

    # 3. 生成测试摘要（只统计最新一次运行批次，避免历史累加）
    python report.py

    # 4. AI 评测（需配置 API Key，见下文「AI 评测模块」）
    copy .env.example .env       # 然后填入 DEEPSEEK_API_KEY
    python ai_eval.py

    # 5. 最小并发压测（50 并发、200 请求）
    python stress_test.py 50 200

## 测试用例设计（共 21 条）

| 类别 | 用例 | 预期 |
|---|---|---|
| 正常 | `GET /posts` 返回全部文章 | 200，返回 100 条 |
| 正常 | `GET /comments` 返回全部评论（参数化） | 200，返回 500 条 |
| 边界 | `GET /posts/1`、`/posts/100`（最小/最大 ID） | 200，id 正确 |
| 边界 | `GET /posts/101`、`/posts/0`（越界/非正数，参数化） | 404 |
| 异常 | `GET /posts/99999`、`/posts/-1`、`/users/0`（参数化） | 404 |
| 异常 | `POST /posts` 空 body（`{}` / `null`） | **201，且响应体含 id** |
| 鉴权 | 无凭证 / 错误凭证访问受保护接口（参数化） | 401 |
| 鉴权 | 正确凭证访问 | 200 |

> 「空 body」这条最初断言写成 `status_code in (200, 201, 400)`，三种结果都放行、等于没校验；
> 后收紧为唯一预期 201 并校验响应体（见「缺陷管理」BUG-003）。

## 测试对象

- 主对象：JSONPlaceholder（https://jsonplaceholder.typicode.com ，免费假 REST API）
- 鉴权演示：httpbin.org（https://httpbin.org/basic-auth/user/passwd ）

## 设计说明

- **api_client.py** 集中管理 base_url、超时与**有限次重试**（3 次 + 退避）：用例依赖外部实时接口，
  网络抖动会造成假失败（见「缺陷管理」BUG-006）。
- **check()** 先写库再断言，保证失败用例也会被记录，便于复盘。
- **结果按 `run_id` 批次隔离**：`report.py` 只统计最新批次，避免多次运行后摘要把 21 条累加成 42 条
  （见「缺陷管理」BUG-001）。
- **DB_PATH 用绝对路径**（`Path(__file__).parent`）：无论从哪个目录执行 pytest，结果都写进项目内的库
  （见「缺陷管理」BUG-002）。

## 持续集成（GitHub Actions）

[`.github/workflows/tests.yml`](.github/workflows/tests.yml)

- **触发**：`push` / `pull_request` 到 `main`，也可在 Actions 页手动 `Run workflow`
- **环境**：`ubuntu-24.04` + Python 3.12，超时上限 10 分钟
- **步骤**：安装依赖 → `pytest -v --junitxml=reports/junit.xml` → 生成摘要 → **校验用例数量**
  （少于 21 条直接让 CI 失败，防止"0 用例也算通过"）→ 上传工件
- **归档**：`junit.xml`（JUnit 报告）、`summary.txt`（按类别 PASS/FAIL 摘要）、`test_results.db`，保留 14 天；
  摘要同时写入 Actions 页面的 Step Summary

## AI 评测模块（ai_eval.py）

把「传统测试的断言」迁移到「AI 测试的评测」：用 **4 个评测问题**（事实类 / 过程类 / 对比类 / 概念类，
如 HTTP 404 含义、TCP 三次握手、list 与 tuple 区别、大模型「幻觉」）提问，用
**事实性** + **来源可验证性** 两个指标给 LLM 回答打分（0-5 分）。

- 传统接口测试：写断言 → PASS/FAIL（`test_api.py`）
- AI 产品测试：建评测集 → 定指标 → 打分（`ai_eval.py`）

运行前配置 OpenAI 兼容 API Key（DeepSeek / Kimi 均可），见 `.env.example`。

## 最小并发压测（stress_test.py）

用标准库 `ThreadPoolExecutor` + `requests` 起 N 个并发 worker，循环请求正常/边界/异常
三类接口，按「实际状态码是否命中预期」判定成败，统计命中率、响应时间与状态码分布。

    python stress_test.py 50 200
    # 50 并发、200 请求 → 输出命中率 / 平均·最小·最大·P95 响应时间 / 状态码分布

## 缺陷管理（TAPD）

项目自己的缺陷也按流程管：在 **TAPD** 登记 6 条真实缺陷，走 `提交 → 指派 → 修复 → 回归 → 关闭`。
其中 4 条已修复并通过回归（提交 `66d1f38`，21 条用例全过），2 条低优先级按计划保留：

| 编号 | 缺陷 | 结论 |
|---|---|---|
| BUG-001 | 结果表未按运行批次隔离 → 摘要统计口径失真（21 条被统计成 42 条） | ✅ 已修复 |
| BUG-002 | 结果库用相对路径 → 跨目录运行写到另一份库 | ✅ 已修复 |
| BUG-003 | 空 body 用例断言过宽 → 失去缺陷检出能力 | ✅ 已修复 |
| BUG-006 | 用例全部依赖外部实时接口 → CI 结果不稳定（flaky） | ✅ 已修复（重试封装） |
| BUG-004 | 正常用例硬编码数据量（100/500）→ 数据变化即假失败 | ⏸ 保留待修 |
| BUG-005 | `check()` 与 `conn` fixture 在两个测试文件中重复实现 | ⏸ 保留待修 |

## 已知限制与下一步

- **UI 自动化**未涉及，目前只覆盖接口层
- `report.py` 只输出当前批次统计，**尚未做趋势图**
- BUG-004 / BUG-005 待后续迭代处理（低优先级）
- 用例依赖外部公开接口，长期方案是引入本地桩服务，彻底消除网络抖动
