"""arXiv 论文拉取模块。

- 数据源: arXiv API (http://export.arxiv.org/api/query), 免费无 key
- 限流: 官方建议 ~1 req/3s, 内置重试 + 节流
- 缓存: 结果按主题缓存到 data/cache/, 避免重复请求触发限流

用法:
    from arxiv_fetcher import fetch_papers
    papers = fetch_papers("retrieval augmented generation", max_results=100)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
CACHE_TTL_SECONDS = 6 * 3600  # 缓存 6 小时

# arXiv Atom 命名空间
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivFetchError(RuntimeError):
    """arXiv 拉取失败（重试耗尽）。"""


def _cache_path(topic: str) -> str:
    key = hashlib.md5(topic.strip().lower().encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{key}.json")


def _load_cache(topic: str, days_back: int) -> list[dict[str, Any]] | None:
    path = _cache_path(topic)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("topic") != topic or data.get("days_back") != days_back:
        return None
    age = time.time() - data.get("fetched_at", 0)
    if age > CACHE_TTL_SECONDS:
        return None
    logger.info("缓存命中: %s (%.0f 分钟前)", topic, age / 60)
    return data["papers"]


def _save_cache(topic: str, days_back: int, papers: list[dict[str, Any]]) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    payload = {"topic": topic, "days_back": days_back, "fetched_at": time.time(), "papers": papers}
    with open(_cache_path(topic), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def _parse_entry(entry: ET.Element) -> dict[str, Any]:
    def text(tag: str) -> str:
        node = entry.find(tag, NS)
        return (node.text or "").strip() if node is not None else ""

    # arxiv:id 有时缺失，从 atom:id (https://arxiv.org/abs/XXXX.XXXXXvN) 兜底提取
    arxiv_id = text("arxiv:id")
    if not arxiv_id:
        atom_id = text("atom:id")
        m = re.search(r"/abs/([^/]+)", atom_id)
        if m:
            arxiv_id = m.group(1)

    published_raw = text("atom:published")
    published = None
    if published_raw:
        try:
            published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        except ValueError:
            published = None

    authors = [a.find("atom:name", NS).text for a in entry.findall("atom:author", NS) if a.find("atom:name", NS) is not None]
    categories = [c.get("term", "") for c in entry.findall("atom:category", NS)]

    return {
        "arxiv_id": arxiv_id,
        "title": text("atom:title").replace("\n ", " ").replace("\n", " "),
        "abstract": text("atom:summary").replace("\n ", " ").replace("\n", " "),
        "authors": authors,
        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else text("atom:id"),
        "published": published.isoformat() if published else None,
        "categories": categories,
    }


def _request_with_retry(url: str, max_retries: int = 3, sleep_seconds: float = 3.0) -> str:
    """带重试 + 节流的请求。arXiv 限流 ~1 req/3s。"""
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-radar/0.1 (mailto:research@example.com)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - 网络层错误统一重试
            last_err = exc
            wait = sleep_seconds * attempt
            logger.warning("arXiv 请求失败 (第 %d/%d 次): %s, %.1fs 后重试", attempt, max_retries, exc, wait)
            time.sleep(wait)
    raise ArxivFetchError(f"arXiv API 重试 {max_retries} 次仍失败: {last_err}")


def fetch_papers(
    topic: str,
    max_results: int = 100,
    days_back: int = 30,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """按主题拉取近 days_back 天的论文。

    返回: [{arxiv_id, title, abstract, authors, url, published, categories}, ...]
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic 不能为空")

    if use_cache:
        cached = _load_cache(topic, days_back)
        if cached is not None:
            return cached

    query = urllib.parse.quote(f'all:"{topic}"')
    url = (
        f"{ARXIV_API}?search_query={query}"
        f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    logger.info("请求 arXiv: %s", url)
    xml_text = _request_with_retry(url)

    root = ET.fromstring(xml_text)
    papers = [_parse_entry(e) for e in root.findall("atom:entry", NS)]

    # 过滤近 days_back 天
    if days_back > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        papers = [p for p in papers if p["published"] and datetime.fromisoformat(p["published"]) >= cutoff]

    logger.info("拉取到 %d 篇论文（近 %d 天）", len(papers), days_back)
    if use_cache and papers:
        _save_cache(topic, days_back, papers)
    return papers


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    papers = fetch_papers(topic, max_results=100, days_back=days)
    print(f"主题「{topic}」近 {days} 天: {len(papers)} 篇")
    for p in papers[:5]:
        print(f"  - {p['published'][:10]} | {p['arxiv_id']} | {p['title'][:80]}")
