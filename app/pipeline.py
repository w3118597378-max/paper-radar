"""Paper Radar 数据管道 CLI：主题 → arXiv 拉取 → 切块 → bge 向量化 → ChromaDB 落盘。

用法:
    python -m app.pipeline "retrieval augmented generation" [days] [max_results]
"""

from __future__ import annotations

import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arxiv_fetcher import fetch_papers  # noqa: E402
from embedder import count_in_collection, index_topic  # noqa: E402


def run_pipeline(topic: str, days: int = 30, max_results: int = 100) -> dict:
    t0 = time.time()
    logger.info("[管道] 拉取 arXiv: 主题=%s 近%d天 max=%d", topic, days, max_results)
    papers = fetch_papers(topic, max_results=max_results, days_back=days)
    t1 = time.time()
    logger.info("[管道] 拉取完成: %d 篇, 耗时 %.1fs", len(papers), t1 - t0)

    if not papers:
        logger.warning("[管道] 无论文, 跳过入库")
        return {"papers": 0, "chunks": 0, "seconds": t1 - t0}

    chunks = index_topic(topic, papers)
    t2 = time.time()
    total = count_in_collection(topic)
    logger.info("[管道] 入库完成: %d chunks / 库中 %d 篇, 耗时 %.1fs", chunks, total, t2 - t1)
    return {"papers": len(papers), "chunks": chunks, "in_db": total, "seconds": t2 - t0}


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    result = run_pipeline(topic, days, max_results)
    print(f"\n管道完成: {result}")
