"""论文入库模块：摘要切块 → bge 向量化 → ChromaDB 落盘。

- chunk: 500 字符 / overlap 100, 中文分隔符优先
- embedding: 本地 E:\\models\\bge-small-zh-v1.5 (512 维, normalize)
- 存储: chroma_db/ (PersistentClient 落盘, 重启数据仍在)

用法:
    from embedder import index_topic
    index_topic("retrieval augmented generation", papers)
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# 项目根目录（app/ 的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
EMBEDDING_MODEL_PATH = r"E:\models\bge-small-zh-v1.5"
# 云端(Linux)无本地模型时的 fallback：从 ModelScope 下载到项目缓存
EMBEDDING_MODEL_FALLBACK = "AI-ModelScope/bge-small-zh-v1.5"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

_model: SentenceTransformer | None = None


def _resolve_model_path() -> str:
    """返回可用的模型路径：本地优先，云端 fallback 到 ModelScope 下载。"""
    if os.path.isdir(EMBEDDING_MODEL_PATH):
        return EMBEDDING_MODEL_PATH
    # 云端/其他机器：尝试已下载缓存，否则从 ModelScope 拉取（hf 国内不可达）
    cached = os.path.join(PROJECT_ROOT, "models", "bge-small-zh-v1.5")
    if os.path.isdir(cached):
        return cached
    try:
        from modelscope import snapshot_download

        logger.info("本地模型不存在，从 ModelScope 下载 %s ...", EMBEDDING_MODEL_FALLBACK)
        path = snapshot_download(EMBEDDING_MODEL_FALLBACK, cache_dir=os.path.join(PROJECT_ROOT, "models"))
        return path
    except Exception as exc:  # noqa: BLE001
        logger.warning("ModelScope 下载失败，回退本地路径（若也不存在会报错）: %s", exc)
        return EMBEDDING_MODEL_PATH


def _get_model() -> SentenceTransformer:
    """懒加载单例 embedding 模型（首次加载 ~5s，之后复用）。"""
    global _model
    if _model is None:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        _model = SentenceTransformer(_resolve_model_path())
        logger.info("embedding 模型已加载: %s", EMBEDDING_MODEL_PATH)
    return _model


def _collection_name(topic: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", topic.strip().lower())
    return f"papers_{safe[:40]}" or "papers_default"


def _make_chunks(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把论文摘要切成 chunk，每条带元数据。标题作为 chunk 前缀（利于检索命中）。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    )
    chunks: list[dict[str, Any]] = []
    for p in papers:
        doc_id = p["arxiv_id"]
        text = f"标题: {p['title']}\n摘要: {p['abstract']}"
        for i, piece in enumerate(splitter.split_text(text)):
            chunks.append(
                {
                    "id": f"{doc_id}#{i}",
                    "paper_id": doc_id,
                    "text": piece,
                    "title": p["title"],
                    "url": p["url"],
                    "published": p.get("published") or "",
                    "authors": ", ".join(p.get("authors", [])[:3]),
                }
            )
    return chunks


def index_topic(topic: str, papers: list[dict[str, Any]], batch_size: int = 32) -> int:
    """把论文切块入库。返回入库 chunk 数。已存在的同论文 chunk 先删再插（幂等）。

    验收: 入库成功 + 落盘 chroma_db/，重启后数据仍在。
    """
    import chromadb

    chunks = _make_chunks(papers)
    if not chunks:
        logger.warning("无可入库 chunk (主题 %s)", topic)
        return 0

    # 幂等：先按 paper_id 清掉旧 chunk（metadata 过滤）
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection_name = _collection_name(topic)
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # bge 归一化后 cosine 匹配
        )

    paper_ids = {c["paper_id"] for c in chunks}
    for pid in paper_ids:
        try:
            collection.delete(where={"paper_id": pid})
        except Exception:
            pass

    model = _get_model()
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    embeddings: list[list[float]] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        for c, vec in zip(batch, vecs):
            ids.append(c["id"])
            docs.append(c["text"])
            metas.append(
                {
                    "paper_id": c["paper_id"],
                    "title": c["title"],
                    "url": c["url"],
                    "published": c["published"],
                    "authors": c["authors"],
                }
            )
            embeddings.append(vec.tolist())

    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
    logger.info("主题 %s 入库 %d 个 chunk (%d 篇论文)", topic, len(ids), len(paper_ids))
    return len(ids)


def count_in_collection(topic: str) -> int:
    """返回某主题库中论文数（distinct paper_id）。"""
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        collection = client.get_collection(_collection_name(topic))
    except Exception:
        return 0
    all_meta = collection.get(include=["metadatas"])
    papers = {m.get("paper_id") for m in all_meta.get("metadatas", []) if m}
    return len(papers)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from arxiv_fetcher import fetch_papers

    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    papers = fetch_papers(topic, max_results=100, days_back=days)
    print(f"拉取 {len(papers)} 篇，开始入库...")
    n = index_topic(topic, papers)
    print(f"入库完成: {n} chunks, 库中论文 {count_in_collection(topic)} 篇")
