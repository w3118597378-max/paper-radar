"""评测集自动执行脚本：跑 20 问，自动判定溯源率/拒绝率。

用法:
    uv run python -m app.run_eval
输出: 每问状态 + 汇总溯源率/拒绝率（eval/test_set.md 的计分口径）
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat import chat  # noqa: E402

QUESTIONS = [
    # A. RAG 主题（8 问，预期有来源）
    ("retrieval augmented generation", "图增强的 RAG 方法有什么进展？", "answer"),
    ("retrieval augmented generation", "ConMem 如何评估历史日志的贡献？", "answer"),
    ("retrieval augmented generation", "RAG 在医疗/临床领域有哪些应用？", "answer"),
    ("retrieval augmented generation", "RAG 在多约束查询上有什么挑战？", "answer"),
    ("retrieval augmented generation", "最近 RAG 论文中记忆机制如何工作？", "answer"),
    ("retrieval augmented generation", "RAG 的安全与防护有什么进展？", "answer"),
    ("retrieval augmented generation", "RAG 系统如何复用答案来降低成本？", "answer"),
    ("retrieval augmented generation", "RAG 在心理健康领域的应用效果？", "answer"),
    # B. AI Agents 主题（8 问，预期有来源）
    ("AI Agents", "AI Agent 在生产环境发布有什么风险？", "answer"),
    ("AI Agents", "如何检测 AI Agent 的浏览器自动化行为？", "answer"),
    ("AI Agents", "评估 AI Agent 开放式研究能力的研究？", "answer"),
    ("AI Agents", "AI Agent 的记忆如何实现？", "answer"),
    ("AI Agents", "AI 代理在网络安全场景的表现？", "answer"),
    ("AI Agents", "对话式 AI 代理的持久记忆挑战？", "answer"),
    ("AI Agents", "医疗场景的 AI Agent 基准？", "answer"),
    ("AI Agents", "多代理技能混合与扩展？", "answer"),
    # C. 边界场景（4 问，预期拒绝或全来源）
    ("retrieval augmented generation", "梵高和毕加索谁更伟大？", "reject"),
    ("retrieval augmented generation", "中国人口普查 2026 年数据？", "reject"),
    ("retrieval augmented generation", "", "reject"),
    ("retrieval augmented generation", "量子计算的最新突破？", "answer_or_reject"),
]


def _has_citations(answer: str) -> bool:
    """回答中是否含 [n] 引用角标。"""
    return bool(re.search(r"\[\d+\]", answer))


def _run_all() -> None:
    results = []
    for i, (topic, q, expect) in enumerate(QUESTIONS, 1):
        t0 = time.time()
        r = chat(q, topic)
        dt = time.time() - t0
        status = r["status"]
        n_src = len(r.get("sources", []))
        cited = _has_citations(r.get("answer", ""))
        ans = r.get("answer", "")[:70].replace("\n", " ")

        # 判定
        if expect == "reject":
            ok = status == "no_sources"
        elif expect == "answer":
            ok = status == "answered" and n_src >= 1 and cited
        else:  # answer_or_reject
            ok = (status == "answered" and n_src >= 1 and cited) or status == "no_sources"

        results.append(ok)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] Q{i:02d} ({expect:15s}) {status:11s} src={n_src} cited={cited} {dt:.1f}s | {ans}")
        if not ok:
            print(f"        ⚠ 全回答: {r.get('answer','')[:200]}")

    n = len(results)
    n_pass = sum(results)
    answered = sum(1 for (_, _, e), r in zip(QUESTIONS, results) if e == "answer" and r)
    print(f"\n==== 汇总 ====")
    print(f"通过: {n_pass}/{n}")
    print(f"溯源率(有来源问题): {answered}/16")
    print(f"拒绝率(边界场景): {sum(1 for (_, _, e), ok in zip(QUESTIONS, results) if e == 'reject' and ok)}/3 + C4")


if __name__ == "__main__":
    _run_all()
