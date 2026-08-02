"""结构化摘要模块：deepseek LLM 生成四字段中文摘要（问题/方法/结论/创新点）。

- 缓存: data/cache/summaries/{arxiv_id}.json，同篇不重复生成（PRD 7.3）
- 铁律: 基于摘要内容生成，信息不足则明说，不编造
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "summaries")

_llm = None


def _get_llm():
    """懒加载 ChatOpenAI（deepseek OpenAI 兼容端点）。"""
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置（检查 .env）")
        _llm = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0,
            max_tokens=600,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        logger.info("LLM 已初始化: %s", DEEPSEEK_MODEL)
    return _llm


_SUMMARY_PROMPT = """你是论文摘要助手。根据给出的论文标题与英文摘要，生成四字段中文结构化摘要。

规则:
1. 四个字段都必须输出: problem(研究问题), method(方法), conclusion(结论), innovation(创新点)
2. 每个字段 1~2 句中文，总字数 ≤ 120 字
3. 严格基于摘要内容，摘要未提及的信息写「未提及」，禁止编造
4. 只输出 JSON，不要多余文字

论文标题: {title}
英文摘要: {abstract}

输出 JSON 格式:
{{"problem": "...", "method": "...", "conclusion": "...", "innovation": "..."}}
"""


def _cache_path(arxiv_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", arxiv_id)
    return os.path.join(CACHE_DIR, f"{safe}.json")


def summarize_paper(paper: dict[str, Any], use_cache: bool = True) -> dict[str, str]:
    """单篇生成四字段中文摘要。带缓存，同篇不重复调用 LLM。"""
    arxiv_id = paper.get("arxiv_id", "")
    if use_cache and arxiv_id:
        path = _cache_path(arxiv_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

    prompt = _SUMMARY_PROMPT.format(title=paper.get("title", ""), abstract=paper.get("abstract", ""))
    llm = _get_llm()
    try:
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        # 抽取 JSON（容错模型偶尔包 markdown 代码块）
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError(f"LLM 返回非 JSON: {text[:200]}")
        summary = json.loads(m.group(0))
        result = {
            "problem": str(summary.get("problem", "未提及")),
            "method": str(summary.get("method", "未提及")),
            "conclusion": str(summary.get("conclusion", "未提及")),
            "innovation": str(summary.get("innovation", "未提及")),
        }
    except Exception as exc:
        logger.warning("摘要生成失败 %s: %s", arxiv_id, exc)
        result = {"problem": "生成失败", "method": "生成失败", "conclusion": "生成失败", "innovation": "生成失败"}

    if use_cache and arxiv_id:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(arxiv_id), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
    return result


def summarize_papers(papers: list[dict[str, Any]], limit: int | None = None) -> dict[str, dict[str, str]]:
    """批量摘要（串行，命中缓存不消耗 token）。返回 {arxiv_id: summary}。"""
    out: dict[str, dict[str, str]] = {}
    for p in papers[:limit] if limit else papers:
        aid = p.get("arxiv_id", "")
        if not aid:
            continue
        out[aid] = summarize_paper(p)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from arxiv_fetcher import fetch_papers

    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    papers = fetch_papers(topic, max_results=100, days_back=30)
    for p in papers[:3]:
        s = summarize_paper(p)
        print(f"\n== {p['arxiv_id']} | {p['title'][:60]}")
        for k, v in s.items():
            print(f"  {k}: {v}")
