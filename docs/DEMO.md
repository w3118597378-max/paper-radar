# Paper Radar · 30 秒演示脚本

> 用途：给面试官/导师快速演示，总时长 ≤30 秒。演示环境需已跑过 `uv run python -m app.pipeline "retrieval augmented generation" 30 100`（缓存命中，秒开）。

## 开场（5s）

> 「Paper Radar 是一个论文情报雷达：输入研究主题，10 分钟掌握该领域一周进展。核心差异化是引用溯源，每个回答都附来源，无来源不回答。」

## 演示一：领域雷达（10s）

1. 打开 `streamlit run app/app.py`，输入主题 `retrieval augmented generation`（或点热门标签 RAG）
2. 指向趋势图：「近 30 天 100 篇论文的数量趋势，一眼看出领域冷热」
3. 指向关键词云：「高频词是 rag / retrieval / generation，领域热点清晰」

## 演示二：中文结构化摘要（5s）

1. 展开第一篇论文
2. 指向四段式摘要：「每篇论文自动生成问题/方法/结论/创新点四段中文摘要，不用读英文原文」

## 演示三：深度问答 + 引用溯源（10s）

1. 切到「问答」页，提问：`RAG 系统如何复用答案来降低成本？`
2. 指向回答中的 [1][2] 角标：「每个关键结论都带引用角标」
3. 指向来源卡片：「点击即可跳转 arXiv 原文——这是防编造的核心机制」
4. 追加提问：`梵高和毕加索谁更伟大？` → 指向拒绝提示：「库中无相关论文时明确拒绝，绝不编造」

## 收尾（5s）

> 「技术栈：arXiv API 免费数据源 + 本地 bge embedding（零 API 费用）+ ChromaDB 向量库 + deepseek 生成，月成本 3~6 元。」

## 数据准备

```bash
cd E:\paper-radar
unset PYTHONPATH
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
uv run python -m app.pipeline "retrieval augmented generation" 30 100   # 首次约 40s，之后缓存命中
uv run streamlit run app/app.py
```
