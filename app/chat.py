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
import time
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

from embedder import _collection_name, _get_model  # noqa: E402

# 相似度阈值：低于此值判定无相关论文（不回答）。
# query 经 LLM 翻译成英文后，相关论文相似度普遍 0.7+；0.45 可区分相关/无关
MIN_SCORE = 0.45
RETRIEVE_K = 10  # 检索 chunk 数（去重后压缩到 5 篇，保证每篇方法细节 chunk 有入场机会）
MAX_SOURCES = 5


_en_cache: dict[str, str] = {}


def _translate_to_en(question: str) -> str:
    """把中文问题翻译成英文检索词（bge-zh 对英文文档需英文 query 才精准）。

    - 只调一次 LLM，结果按问题缓存到内存
    - 翻译失败时原样返回（检索兜底）
    """
    key = question.strip().lower()
    if key in _en_cache:
        return _en_cache[key]
    try:
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return question
        llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            temperature=0,
            max_tokens=80,
        )
        prompt = (
            "把下面这个论文检索问题翻译成英文检索词（只输出英文检索词，不要解释，不要引号）:\n" + question
        )
        last_err: Exception | None = None
        for attempt in range(2):  # 批量调用偶发限流，重试 1 次
            try:
                resp = llm.invoke(prompt)
                break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(1.0 * (attempt + 1))
        else:
            raise last_err  # type: ignore[misc]
        text = (resp.content if hasattr(resp, "content") else str(resp)).strip().strip('"')
        if not text:
            raise ValueError("空翻译结果")
        _en_cache[key] = text
        logger.info("翻译 query: %s → %s", question, text)
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("query 翻译失败，用原文检索: %s", exc)
        return question


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

    # 中文问题 → 英文检索词（bge-zh 对英文库需英文 query 才精准）
    search_query = _translate_to_en(query)
    hits = _retrieve(search_query, topic)
    # 英文检索无结果时，用中文原文兜底再检索一次（防止翻译失效导致漏召回）
    if not hits or max(h["score"] for h in hits) < MIN_SCORE:
        zh_hits = _retrieve(query, topic)
        if zh_hits and max(h["score"] for h in zh_hits) >= MIN_SCORE:
            logger.info("英文检索无结果，中文原文兜底命中 %d 条", len(zh_hits))
            hits = zh_hits
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

    # LLM 判定资料与问题无关时（回答含拒绝字样），统一归为 no_sources
    if "库中无相关论文" in answer or "无法回答" in answer:
        return {
            "answer": "库中无相关论文，无法回答该问题。（检索内容与问题不相关，为防编造未生成回答）",
            "sources": [],
            "status": "no_sources",
        }

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
