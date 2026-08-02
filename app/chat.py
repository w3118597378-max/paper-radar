"""深度问答模块（RAG + 强制引用溯源）——差异化核心（PRD FR-3）。

铁律:
- 每个关键结论必须附来源（arXiv ID + 链接），回答中带 [1][2] 角标
- 检索不到相关内容时明确提示「库中无相关论文」，绝不编造
- 检索相似度低于阈值 → 不回答

用法:
    from chat import chat
    result = chat("RAG 的最新进展是什么?", "retrieval augmented generation")
    # {"answer": "...[1]...", "sources": [{arxiv_id, title, url, ...}], "status": "answered"}
"""

from __future__ import annotations

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

# 相似度阈值：低于此值判定无相关论文（不回答）。
# bge-small-zh 对英文内容整体分数偏低（相关 0.45~0.55），实测 0.40 能正确区分相关/无关
MIN_SCORE = 0.40
RETRIEVE_K = 10  # 检索 chunk 数（去重后压缩到 5 篇，保证每篇方法细节 chunk 有入场机会）
MAX_SOURCES = 5


def _retrieve(query: str, topic: str, k: int = RETRIEVE_K) -> list[dict[str, Any]]:
    """向量检索 top-k chunk，附带相似度。"""
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(_collection_name(topic))

    model = _get_model()
    vec = model.encode([query], normalize_embeddings=True)[0].tolist()
    res = collection.query(query_embeddings=[vec], n_results=k, include=["metadatas", "documents", "distances"])

    metas = res.get("metadatas", [[]])[0]
    docs = res.get("documents", [[]])[0]
    dists = res.get("distances", [[]])[0]

    out: list[dict[str, Any]] = []
    for meta, doc, dist in zip(metas, docs, dists):
        m = meta or {}
        out.append(
            {
                "arxiv_id": m.get("paper_id", ""),
                "title": m.get("title", ""),
                "url": m.get("url", ""),
                "published": m.get("published", ""),
                "authors": m.get("authors", ""),
                "score": round(1.0 - dist, 4),
                "text": doc,
            }
        )
    return out


_CHAT_PROMPT = """你是论文情报助手，基于提供的论文资料回答用户问题。

规则（必须严格遵守）:
1. 回答必须基于资料内容，关键结论后加引用角标 [1][2][3]（对应下方「资料」编号）
2. 每条核心结论必须有来源；资料中找不到答案的部分，明确写「资料中未提及」
3. 如果用户问题与资料主题完全无关，只回答「库中无相关论文，无法回答」
4. 中文回答，简洁，3~6 句

资料:
{context}

用户问题: {question}

回答:"""


def chat(query: str, topic: str) -> dict[str, Any]:
    """问答主入口。返回 {answer, sources, status}。

    status: "answered" 正常回答 | "no_sources" 库中无相关论文（不编造）
    """
    query = query.strip()
    if not query:
        return {"answer": "请输入问题。", "sources": [], "status": "no_sources"}

    hits = _retrieve(query, topic)
    # 过滤：相似度低于阈值视为无相关论文
    hits = [h for h in hits if h["score"] >= MIN_SCORE]
    if not hits:
        logger.info("无相关论文（最高相似度低于 %.2f），拒绝回答", MIN_SCORE)
        return {
            "answer": "库中无相关论文，无法回答该问题。（检索相似度低于阈值，为防编造未生成回答）",
            "sources": [],
            "status": "no_sources",
        }

    # 按论文去重：每篇保留得分最高的 2 个 chunk（方法细节常在多个 chunk 中）
    seen: dict[str, list[dict[str, Any]]] = {}
    for h in hits:
        lst = seen.setdefault(h["arxiv_id"], [])
        if len(lst) < 2 or h["score"] > min(x["score"] for x in lst):
            lst.append(h)
            lst.sort(key=lambda x: -x["score"])
            if len(lst) > 2:
                lst.pop()
    unique: list[dict[str, Any]] = []
    for h in sorted(seen.values(), key=lambda lst: -lst[0]["score"]):
        unique.extend(h)
    unique = unique[:MAX_SOURCES]

    context = "\n\n".join(
        f"[{i+1}] 论文 {h['arxiv_id']} 《{h['title']}》\n摘录: {h['text'][:800]}"
        for i, h in enumerate(unique)
    )
    prompt = _CHAT_PROMPT.format(context=context, question=query)

    from langchain_openai import ChatOpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")
    llm = ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=0.2,
        max_tokens=600,
    )
    resp = llm.invoke(prompt)
    answer = resp.content if hasattr(resp, "content") else str(resp)

    sources = [
        {
            "arxiv_id": h["arxiv_id"],
            "title": h["title"],
            "url": h["url"],
            "published": h["published"],
            "authors": h["authors"],
            "score": h["score"],
        }
        for h in unique
    ]
    return {"answer": answer, "sources": sources, "status": "answered"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    question = sys.argv[2] if len(sys.argv) > 2 else "RAG 最近有什么重要进展？"
    result = chat(question, topic)
    print(f"问题: {question}\n")
    print(f"回答: {result['answer']}\n")
    print(f"状态: {result['status']} | 来源 {len(result['sources'])} 篇:")
    for s in result["sources"]:
        print(f"  [{s['arxiv_id']}] {s['title'][:70]} (相似度 {s['score']})")
