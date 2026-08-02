"""领域雷达模块：论文数量趋势 + 高频关键词（纯统计，数据直接来自 arXiv 返回）。

- trend_data(): 按日期统计论文数量，与 arXiv 返回逐篇对应
- keywords(): 标题+摘要提取高频关键词（英文为主，去停用词/数字/短词）
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "we", "our", "you", "your", "they", "their", "them",
    "he", "she", "his", "her", "i", "me", "my", "not", "no", "yes", "so", "if", "then",
    "than", "too", "very", "can", "could", "would", "should", "may", "might", "must",
    "will", "shall", "do", "does", "did", "have", "has", "had", "which", "what", "when",
    "where", "who", "whom", "why", "how", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "about", "into", "over",
    "after", "before", "between", "under", "again", "further", "once", "also", "using",
    "used", "use", "via", "per", "among", "toward", "against", "during", "without",
    "within", "across", "along", "around", "down", "up", "out", "off", "above", "below",
    "new", "recent", "recently", "show", "shows", "shown", "propose", "proposed",
    "proposes", "present", "presents", "presented", "introduce", "introduced", "based",
    "approach", "methods", "method", "results", "result", "performance", "task", "tasks",
    "model", "models", "paper", "papers", "work", "works", "study", "studies", "data",
    "set", "sets", "system", "systems", "framework", "frameworks", "e.g", "i.e", "et",
    "al", "etc", "fig", "figs", "table", "tables", "section", "see", "using", "well",
    "however", "while", "due", "yet", "much", "many", "one", "two", "three", "first",
    "second", "also", "via", "across", "large", "significant", "significantly", "state",
    "of-the-art", "sota",
}

_WORD_RE = re.compile(r"[a-z][a-z\-]{2,}")


def _stem(word: str) -> str:
    """轻量词干化：去常见复数/分词后缀。"""
    w = word.strip("-")
    if len(w) <= 4:
        return w
    if w.endswith("ies") and len(w) > 5:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and not w.endswith("us"):
        return w[:-1]
    if w.endswith("ing") and len(w) > 6:
        return w[:-3]
    if w.endswith("ed") and len(w) > 5:
        return w[:-2]
    return w


def trend_data(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按日期统计论文数量。数据逐篇对应 arXiv 返回（验收：抽样核对一致）。

    返回: [{"date": "2026-07-30", "count": 12}, ...] 升序
    """
    counter: Counter = Counter()
    for p in papers:
        published = p.get("published")
        if not published:
            continue
        day = published[:10]  # YYYY-MM-DD
        counter[day] += 1
    return [{"date": d, "count": c} for d, c in sorted(counter.items())]


def keywords(papers: list[dict[str, Any]], top_n: int = 20) -> list[dict[str, Any]]:
    """标题+摘要高频关键词。返回: [{"word": "...", "count": N}, ...] 降序。"""
    counter: Counter = Counter()
    for p in papers:
        text = f"{p.get('title', '')} {p.get('abstract', '')}".lower()
        for word in _WORD_RE.findall(text):
            if word in STOPWORDS or len(word) < 3:
                continue
            stemmed = _stem(word)
            if stemmed in STOPWORDS or len(stemmed) < 3:
                continue
            counter[stemmed] += 1
    return [{"word": w, "count": c} for w, c in counter.most_common(top_n)]


def stats(papers: list[dict[str, Any]], days: int = 30) -> dict[str, Any]:
    """雷达统计汇总。"""
    trend = trend_data(papers)
    return {
        "total": len(papers),
        "days": days,
        "trend": trend,
        "keywords": keywords(papers),
        "latest_date": trend[-1]["date"] if trend else None,
    }


if __name__ == "__main__":
    import json
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from arxiv_fetcher import fetch_papers

    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    papers = fetch_papers(topic, max_results=100, days_back=30)
    s = stats(papers)
    print(f"主题: {topic} | 论文数: {s['total']}")
    print("趋势(前8天):")
    for d in s["trend"][:8]:
        print(f"  {d['date']}: {d['count']} 篇")
    print("关键词 Top 10:")
    for k in s["keywords"][:10]:
        print(f"  {k['word']}: {k['count']}")
