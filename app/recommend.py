"""相关文献推荐模块：基于向量相似度，从库里推荐 3~5 篇相关论文（PRD FR-4）。

- 推荐理由: 由 LLM 基于目标论文与候选论文标题/摘要生成一句中文理由
- 候选: ChromaDB cosine 检索 top-k（排除目标论文自身）
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

from embedder import _collection_name, _get_model  # noqa: E402


def recommend_papers(
    target_paper: dict[str, Any],
    topic: str,
    k: int = 6,
    top_n: int = 4,
) -> list[dict[str, Any]]:
    """基于目标论文标题+摘要向量，在主题库中检索相似论文。

    返回: [{arxiv_id, title, url, published, authors, score, reason}, ...]
    """
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(_collection_name(topic))

    model = _get_model()
    query_text = f"标题: {target_paper.get('title', '')}\n摘要: {target_paper.get('abstract', '')}"
    vec = model.encode([query_text], normalize_embeddings=True)[0].tolist()

    target_id = target_paper.get("arxiv_id", "")
    # 多取几篇，过滤目标论文自身后仍够 top_n
    res = collection.query(query_embeddings=[vec], n_results=k + 3, include=["metadatas", "documents", "distances"])
    metas = res.get("metadatas", [[]])[0]
    docs = res.get("documents", [[]])[0]
    dists = res.get("distances", [[]])[0]

    seen: set[str] = set()
    cands: list[dict[str, Any]] = []
    for meta, doc, dist in zip(metas, docs, dists):
        pid = (meta or {}).get("paper_id", "")
        if not pid or pid == target_id or pid in seen:
            continue
        seen.add(pid)
        score = 1.0 - dist  # cosine distance → 相似度
        cands.append(
            {
                "arxiv_id": pid,
                "title": (meta or {}).get("title", ""),
                "url": (meta or {}).get("url", ""),
                "published": (meta or {}).get("published", ""),
                "authors": (meta or {}).get("authors", ""),
                "score": round(score, 4),
                "_doc": doc[:500],
            }
        )
        if len(cands) >= k:
            break

    result = [c for c in cands[:k]]
    # 生成推荐理由（LLM 一次批量生成，省调用）
    _attach_reasons(target_paper, result)
    return result[:top_n]


_RECOMMEND_PROMPT = """你是论文推荐助手。目标论文与候选论文如下，为每个候选写一句中文推荐理由（≤40字），说明它与目标论文的相关性。

目标论文标题: {target_title}
目标论文摘要: {target_abstract}

候选论文:
{candidates}

只输出 JSON 数组，每项 {{"arxiv_id": "...", "reason": "..."}}，不要多余文字。"""


def _attach_reasons(target_paper: dict[str, Any], cands: list[dict[str, Any]]) -> None:
    """为候选论文批量生成推荐理由（失败时用相似度兜底，不阻塞推荐）。"""
    if not cands:
        return
    try:
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置")
        llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            temperature=0,
            max_tokens=400,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        lines = [f"[{i}] {c['arxiv_id']} | {c['title'][:100]}" for i, c in enumerate(cands)]
        prompt = _RECOMMEND_PROMPT.format(
            target_title=target_paper.get("title", ""),
            target_abstract=(target_paper.get("abstract", "") or "")[:1500],
            candidates="\n".join(lines),
        )
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r"\[.*\]", text, re.S) or re.search(r"\{.*\}", text, re.S)
        if m:
            data = json.loads(m.group(0))
            reasons = {d.get("arxiv_id"): d.get("reason", "") for d in data}
            for c in cands:
                c["reason"] = reasons.get(c["arxiv_id"], "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("推荐理由生成失败（用相似度兜底）: %s", exc)
    for c in cands:
        if not c.get("reason"):
            c["reason"] = f"与目标论文主题相似（相似度 {c['score']:.2f}）"


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    topic = "retrieval augmented generation"
    papers = __import__("arxiv_fetcher", fromlist=["fetch_papers"]).fetch_papers(topic, max_results=100, days_back=30)
    target = papers[0]
    print(f"目标论文: {target['title'][:70]}\n")
    recs = recommend_papers(target, topic)
    for r in recs:
        print(f"- {r['arxiv_id']} | score={r['score']} | {r['title'][:60]}")
        print(f"  理由: {r['reason']}")
