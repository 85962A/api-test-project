"""AI 评测小模块：用「评测集 + 指标」对 LLM 回答做质量打分。

背景（为什么把它加进 API 测试项目）：
    传统接口测试用「断言」判对错（PASS/FAIL，见 test_api.py）；
    而 AI 产品输出是概率性的、没有唯一标准答案，所以要把「断言」换成「评测」——
    用一组评测集提问，再用指标量化回答质量。本模块演示这一方法迁移。

评测指标：
    - 事实性 factual：回答是否给出具体、可核对的事实依据（术语 / 数字 / 年份）
    - 来源可验证性 source：回答是否给出可回溯的来源（URL / 引用）

用法：
    # 1. 配置 API Key（OpenAI 兼容接口，DeepSeek / Kimi / 任意兼容模型均可）
    set DEEPSEEK_API_KEY=sk-xxx        # Windows
    # 或 export DEEPSEEK_API_KEY=sk-xxx  # Linux/macOS

    # 2. 运行
    python ai_eval.py

可选环境变量：
    AI_EVAL_BASE_URL   默认 https://api.deepseek.com/v1
    AI_EVAL_MODEL      默认 deepseek-chat

说明：本模块用「规则引擎」打分为最小可用版本（可运行、可演示）；
      生产级 AI 评测通常改用 LLM-as-judge（让更强模型评分）+ 评测集版本管理。
"""
import os
import json
import time
import pathlib

import requests


def _load_env_file():
    """从同目录 .env 读取 KEY=VALUE（无需第三方库）；已存在的环境变量优先。"""
    env_path = pathlib.Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("\ufeff")          # 防 BOM（记事本/PowerShell 写文件常带 BOM）
        if line.lower().startswith("export "):       # 兼容 .env 里的 export KEY=VALUE 写法
            line = line[7:].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


_load_env_file()

BASE_URL = os.environ.get("AI_EVAL_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("AI_EVAL_MODEL", "deepseek-chat")
API_KEY = ( os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_EVAL_API_KEY"))

# 评测集：技术类、有明确标准答案的问题，便于判断回答是否可靠（覆盖事实/过程/对比/概念四类）
EVAL_CASES = [
    "请说明 HTTP 404 状态码的含义，并给出你的信息来源。",
    "TCP 三次握手的具体过程是什么？请分步骤说明。",
    "Python 中 list 与 tuple 有什么区别？",
    "大语言模型的「幻觉」指什么？请举例说明。",
]

# 事实信号：回答里出现这些词/模式，说明给出了具体依据
FACT_SIGNALS = [
    "例如", "具体", "404", "200", "第一次", "第二次", "第三次",
    "握手", "元组", "列表", "不可变", "可变", "Transformer", "概率",
]
# 模糊信号：出现这些说明回答含糊、可能编造
VAGUE_SIGNALS = ["可能", "大概", "不确定", "记不清", "应该", "估计", "我猜"]


def call_llm(question):
    """调用 OpenAI 兼容 chat completions 接口，返回回答文本。"""
    if not API_KEY:
        raise SystemExit(
            "未配置 API Key。三选一：\n"
            "  1) 当前窗口临时设置：  set DEEPSEEK_API_KEY=sk-xxxx\n"
            "     （PowerShell：$env:DEEPSEEK_API_KEY=\"sk-xxxx\"）\n"
            "  2) 永久设置：          setx DEEPSEEK_API_KEY \"sk-xxxx\"  然后重开终端\n"
            "  3) 推荐：项目根目录建 .env 文件，写一行 DEEPSEEK_API_KEY=sk-xxxx（已加入 .gitignore）\n"
            "注意：等号两边不要空格、cmd 下不要加引号、不要把 key 写进代码。"
        )
    resp = requests.post(
        BASE_URL.rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是被评测对象，请直接回答问题，尽量给出可核对的事实依据和来源。",
                },
                {"role": "user", "content": question},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def score_factual(answer):
    """事实性打分：具体依据加分、模糊措辞减分，结果落在 0-5 分。"""
    score = 3.0
    for s in FACT_SIGNALS:
        if s in answer:
            score += 0.5
    for s in VAGUE_SIGNALS:
        if s in answer:
            score -= 0.5
    return round(max(0.0, min(5.0, score)), 1)


def score_source(answer):
    """来源可验证性打分：URL / 引用词加分，结果落在 0-5 分。"""
    score = 0.0
    if "http" in answer:
        score += 2.5
    for s in ["根据", "来源", "引用", "RFC", "官方", "文档"]:
        if s in answer:
            score += 0.5
    return round(min(5.0, score), 1)


def run():
    """跑完整评测集，逐题打分并输出汇总，结果写 ai_eval_results.json。"""
    results = []
    print("=" * 60)
    print("AI 评测：评测集 %d 题 ｜ 模型 %s" % (len(EVAL_CASES), MODEL))
    print("API Key：" + (("已加载 %s…（长度 %d）" % (API_KEY[:6], len(API_KEY))) if API_KEY else "未加载（请见下方提示）"))
    print("=" * 60)
    for i, question in enumerate(EVAL_CASES, 1):
        print("\nQ%d: %s" % (i, question))
        answer = call_llm(question)
        factual = score_factual(answer)
        source = score_source(answer)
        results.append(
            {
                "id": i,
                "question": question,
                "factual": factual,
                "source": source,
                "answer": answer,
            }
        )
        print("  factual=%s/5  source=%s/5" % (factual, source))
        print("  回答(前 180 字): %s" % answer[:180])
        time.sleep(1)  # 简单限流，避免请求过快

    avg_factual = round(sum(r["factual"] for r in results) / len(results), 1)
    avg_source = round(sum(r["source"] for r in results) / len(results), 1)
    print("\n" + "=" * 60)
    print(
        "汇总：平均事实性=%s/5  平均来源可验证性=%s/5" % (avg_factual, avg_source)
    )
    print("=" * 60)

    out_path = "ai_eval_results.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "model": MODEL,
                "avg_factual": avg_factual,
                "avg_source": avg_source,
                "cases": results,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )
    print("评测结果已写入 " + out_path)
    return results


if __name__ == "__main__":
    run()
