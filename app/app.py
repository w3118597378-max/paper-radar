"""Paper Radar · Streamlit 界面

三页: 首页(搜索入口) / 领域雷达(结果页) / 深度问答(引用溯源)
设计: 经典苹果白 (DESIGN.md) — #ffffff 底 + #0071e3 蓝 + #1d1d1f 近黑
运行: streamlit run app/app.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arxiv_fetcher import fetch_papers  # noqa: E402
from embedder import index_topic  # noqa: E402
from radar import stats as radar_stats  # noqa: E402
from recommend import recommend_papers  # noqa: E402
from summarizer import summarize_paper  # noqa: E402

# ---------- 设计令牌 (DESIGN.md) ----------
BG = "#ffffff"
BG_SOFT = "#f5f5f7"
TEXT_PRIMARY = "#1d1d1f"
TEXT_SECONDARY = "#6e6e73"
ACCENT = "#0071e3"
SUCCESS = "#34c759"
WARNING = "#ff9500"
BORDER = "#d2d2d7"
FONT_STACK = '-apple-system, "SF Pro Text", "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif'

st.set_page_config(page_title="Paper Radar · 论文情报雷达", page_icon="📡", layout="wide")

CUSTOM_CSS = f"""
<style>
:root {{
    --bg: {BG}; --bg-soft: {BG_SOFT}; --text-primary: {TEXT_PRIMARY};
    --text-secondary: {TEXT_SECONDARY}; --accent: {ACCENT};
    --success: {SUCCESS}; --warning: {WARNING}; --border: {BORDER};
}}
html, body, [data-testid="stAppViewContainer"] {{
    background: var(--bg); color: var(--text-primary); font-family: {FONT_STACK};
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1100px; padding-top: 2rem; padding-bottom: 4rem; }}

/* 顶部导航 */
.nav-bar {{
    display: flex; align-items: center; gap: 2rem;
    padding-bottom: 1.2rem; border-bottom: 1px solid var(--border);
    margin-bottom: 2.5rem;
}}
.nav-logo {{ font-weight: 600; font-size: 1.15rem; color: var(--text-primary); letter-spacing: -0.02em; }}
.nav-logo span {{ color: var(--accent); }}
.nav-item {{ color: var(--text-secondary); font-size: 0.95rem; cursor: pointer; padding: 0.25rem 0.1rem; }}
.nav-item.active {{ color: var(--accent); font-weight: 600; border-bottom: 2px solid var(--accent); }}

/* Hero */
.hero-title {{ font-size: 2.6rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1.15; margin: 3rem 0 0.6rem; }}
.hero-sub {{ color: var(--text-secondary); font-size: 1.05rem; margin-bottom: 2.2rem; }}
.search-box {{ display: flex; gap: 0.6rem; max-width: 640px; margin: 0 auto 1rem; }}
.stTextInput input {{ border-radius: 8px !important; border: 1px solid var(--border) !important; padding: 0.7rem 1rem !important; }}
.hot-tags {{ display: flex; gap: 0.6rem; justify-content: center; flex-wrap: wrap; margin: 0.6rem 0 3.5rem; }}
.tag-chip {{
    background: var(--bg-soft); border: 1px solid var(--border); border-radius: 999px;
    padding: 0.4rem 1.1rem; font-size: 0.85rem; color: var(--text-primary); cursor: pointer;
}}
.tag-chip:hover {{ border-color: var(--accent); color: var(--accent); }}

/* 能力卡片 */
.cap-cards {{ display: flex; gap: 1.2rem; justify-content: center; margin-top: 1rem; }}
.cap-card {{
    flex: 1; max-width: 320px; background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    padding: 1.6rem 1.4rem; text-align: left; transition: all .2s ease;
}}
.cap-card:hover {{ transform: translateY(-1px); border-color: #a8c9f5; }}
.cap-icon {{ font-size: 1.6rem; margin-bottom: 0.7rem; }}
.cap-title {{ font-weight: 600; font-size: 1rem; margin-bottom: 0.35rem; }}
.cap-desc {{ color: var(--text-secondary); font-size: 0.85rem; line-height: 1.55; }}

/* 结果页 */
.radar-header {{ display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap; margin-bottom: 0.4rem; }}
.radar-topic {{ font-size: 1.7rem; font-weight: 700; letter-spacing: -0.02em; }}
.updated-badge {{
    background: #e8f8ee; color: var(--success); border: 1px solid #b7e8c9;
    border-radius: 999px; padding: 0.2rem 0.8rem; font-size: 0.8rem; font-weight: 500;
}}
.radar-meta {{ color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.6rem; }}
.stat-panel {{
    background: var(--bg-soft); border-radius: 8px; padding: 1.1rem 1.3rem; margin-bottom: 1.4rem;
    display: flex; gap: 2.4rem;
}}
.stat-num {{ font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
.stat-label {{ color: var(--text-secondary); font-size: 0.8rem; }}

/* 论文卡片 */
.paper-card {{
    background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04); padding: 1.2rem 1.4rem; margin-bottom: 1rem;
    transition: all .2s ease;
}}
.paper-card:hover {{ transform: translateY(-1px); border-color: #a8c9f5; }}
.paper-title {{ font-weight: 600; font-size: 1.02rem; line-height: 1.4; margin-bottom: 0.35rem; }}
.paper-title a {{ color: var(--text-primary); text-decoration: none; }}
.paper-title a:hover {{ color: var(--accent); }}
.paper-meta {{ color: var(--text-secondary); font-size: 0.82rem; margin-bottom: 0.8rem; }}
.summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem 1.2rem; }}
.summary-field {{ font-size: 0.86rem; line-height: 1.5; }}
.summary-label {{ color: var(--accent); font-weight: 600; font-size: 0.78rem; margin-right: 0.4rem; }}
.section-title {{ font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin: 2rem 0 1rem; }}

/* 问答页 */
.qa-container {{ max-width: 1100px; }}
.rule-card {{
    border: 1px solid var(--accent); border-left: 3px solid var(--accent);
    background: #f5f9ff; border-radius: 8px; padding: 1.1rem 1.3rem; margin-bottom: 1.6rem;
}}
.qa-answer {{ background: var(--bg-soft); border-radius: 8px; padding: 1.1rem 1.3rem; margin: 0.8rem 0 1.4rem; }}
.source-card {{
    border: 1px solid var(--border); border-radius: 8px; padding: 0.7rem 1rem;
    margin: 0.4rem 0; font-size: 0.85rem;
}}
.source-card b {{ color: var(--accent); }}
.cite-sup {{ color: var(--accent); font-size: 0.75rem; font-weight: 600; vertical-align: super; }}
.footer-note {{ color: var(--text-secondary); font-size: 0.85rem; margin-top: 2.5rem; padding-top: 1.2rem; border-top: 1px solid var(--border); }}
div[data-testid="stButton"] button {{
    border-radius: 8px; border: 1px solid var(--border); background: var(--bg);
    color: var(--text-primary); font-weight: 500;
}}
div[data-testid="stButton"] button:hover {{ border-color: var(--accent); color: var(--accent); }}
div[data-testid="stButton"] button[kind="primary"] {{
    background: var(--accent); color: #fff; border: none;
}}
div[data-testid="stButton"] button[kind="primary"]:hover {{ background: #0077ed; color: #fff; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

HOT_TOPICS = ["RAG", "AI Agents", "Multimodal LLM"]


def nav_bar(active: str) -> None:
    """顶部导航：logo + 雷达/论文/问答三页切换（按钮，当前页高亮）。active 传当前页 label。"""
    st.markdown(
        f'<div class="nav-bar"><span class="nav-logo">Paper <span>Radar</span></span></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 1, 1, 1, 7])
    for col, (label, view) in zip(cols[:3], [("雷达", "radar"), ("论文", "radar"), ("问答", "qa")]):
        with col:
            if st.button(label, key=f"nav_{label}", type="primary" if label == active else "secondary", use_container_width=True):
                st.session_state["view"] = view
                if view == "qa":
                    st.session_state["topic"] = st.session_state.get("topic", "retrieval augmented generation")
                st.rerun()


@st.cache_data(ttl=3600, show_spinner=False)
def load_topic(topic: str, days: int = 30, max_results: int = 100):
    """拉取 + 入库（带缓存，1 小时内重复访问不重跑）。"""
    papers = fetch_papers(topic, max_results=max_results, days_back=days)
    if papers:
        index_topic(topic, papers)
    return papers


def render_trend_chart(trend: list[dict]) -> None:
    """SVG 折线图：描边动画 + 数据点浮现（DESIGN.md 签名动效）。"""
    if not trend:
        st.caption("暂无趋势数据")
        return
    w, h, pad = 620, 180, 24
    counts = [t["count"] for t in trend]
    max_c = max(counts) or 1
    n = len(trend)
    step_x = (w - 2 * pad) / max(n - 1, 1)
    pts = [(pad + i * step_x, h - pad - (c / max_c) * (h - 2 * pad)) for i, c in enumerate(counts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#0071e3"><animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="{0.5+i*0.12:.2f}s" fill="freeze"/></circle>' for i, (x, y) in enumerate(pts))
    labels = "".join(
        f'<text x="{x:.1f}" y="{h-6}" font-size="10" fill="#6e6e73" text-anchor="middle">{t["date"][5:]}</text>'
        for t, (x, y) in zip(trend[:: max(n // 8, 1)], pts[:: max(n // 8, 1)])
    )
    svg = f"""<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto">
        <path d="M {line}" fill="none" stroke="#0071e3" stroke-width="2"
              stroke-dasharray="1200" stroke-dashoffset="1200">
            <animate attributeName="stroke-dashoffset" from="1200" to="0" dur="1.6s" fill="freeze"/>
        </path>{dots}{labels}
    </svg>"""
    st.markdown(svg, unsafe_allow_html=True)


def page_qa() -> None:
    """深度问答页：RAG + 强制引用溯源（PRD FR-3 / DESIGN.md 页 3）。"""
    from chat import chat

    nav_bar("问答")
    topic = st.session_state.get("topic", "retrieval augmented generation")
    st.markdown(f'<div class="radar-header"><span class="radar-topic">深度问答</span>'
                f'<span class="updated-badge">● 已连接知识库</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="radar-meta">知识库主题：<b>{topic}</b> · 回答均附来源，无来源不回答</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="rule-card"><b>无来源不回答</b> · 每个回答的关键结论都附来源论文（arXiv ID + 链接）。'
        '检索不到相关内容时，系统会明确提示「库中无相关论文」，绝不编造。</div>',
        unsafe_allow_html=True,
    )

    if "qa_history" not in st.session_state:
        st.session_state["qa_history"] = []

    question = st.text_input("对论文库提问", placeholder="例如: RAG 在图增强方面有什么新方法？",
                             label_visibility="collapsed")
    ask = st.button("提问", type="primary")
    if ask and question.strip():
        with st.spinner("检索论文并生成回答..."):
            result = chat(question.strip(), topic)
        st.session_state["qa_history"].append({"q": question.strip(), **result})

    for turn in st.session_state["qa_history"][-5:]:
        st.markdown(f'<div class="source-card" style="background:#f5f9ff;border-color:#a8c9f5"><b>问：</b>{turn["q"]}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="qa-answer">{turn["answer"]}</div>', unsafe_allow_html=True)
        if turn.get("sources"):
            for s in turn["sources"]:
                st.markdown(
                    f'<div class="source-card"><b>[来源]</b> {s["arxiv_id"]} · '
                    f'<a href="{s["url"]}" target="_blank" style="color:#0071e3">{s["title"][:80]}</a>'
                    f'<br><span style="color:#6e6e73;font-size:0.8rem">相似度 {s["score"]:.2f}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="source-card"><b>来源</b> 无 · 已按「无来源不回答」规则拒绝编造</div>',
                        unsafe_allow_html=True)

    st.markdown(
        '<div class="footer-note">提问建议：① 图增强 RAG 有什么新方法？ ② 多模态 RAG 的挑战？ ③ 记忆机制如何工作？</div>',
        unsafe_allow_html=True,
    )


def page_home() -> None:
    nav_bar("雷达")
    st.markdown('<div class="hero-title">你的领域，<br>10 分钟掌握一周进展</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">输入研究主题，自动扫描 arXiv 近 30 天论文，生成领域雷达、中文摘要与深度问答。</div>', unsafe_allow_html=True)

    topic = st.text_input(
        "领域主题", placeholder="例如: retrieval augmented generation",
        label_visibility="collapsed", key="home_topic",
    )
    col_btn, col_sp = st.columns([1, 5])
    with col_btn:
        go = st.button("搜索", type="primary", use_container_width=True)
    with col_sp:
        st.markdown("")

    # 热门主题标签（Streamlit 按钮，避免内联 onclick 被 React/DOMPurify 拦截）
    tag_cols = st.columns([1, 1, 1, 3])
    for col, t in zip(tag_cols[:3], HOT_TOPICS):
        with col:
            if st.button(t, key=f"hot_{t}", use_container_width=True):
                st.session_state["topic"] = t
                st.session_state["view"] = "radar"
                st.rerun()

    st.markdown(
        """<div class="cap-cards">
        <div class="cap-card"><div class="cap-icon">🔗</div><div class="cap-title">引用溯源</div><div class="cap-desc">每个回答都附来源论文与 arXiv 链接。无来源不回答，拒绝编造。</div></div>
        <div class="cap-card"><div class="cap-icon">📈</div><div class="cap-title">领域雷达</div><div class="cap-desc">论文数量趋势 + 高频关键词，30 秒判断领域冷热。</div></div>
        <div class="cap-card"><div class="cap-icon">🇨🇳</div><div class="cap-title">中文摘要</div><div class="cap-desc">问题 / 方法 / 结论 / 创新点，四段式中文结构化摘要。</div></div>
        </div>""",
        unsafe_allow_html=True,
    )

    if go and topic.strip():
        st.session_state["topic"] = topic.strip()
        st.session_state["view"] = "radar"
        st.rerun()


def main() -> None:
    if "view" not in st.session_state:
        st.session_state["view"] = "home"
    if st.session_state["view"] == "home":
        page_home()
        return
    if st.session_state["view"] == "qa":
        page_qa()
        return
    nav_bar("雷达")
    if "topic" not in st.session_state:
        st.session_state["topic"] = "retrieval augmented generation"

    topic = st.session_state["topic"]
    st.markdown(
        f'<div class="radar-header"><span class="radar-topic">{topic}</span>'
        f'<span class="updated-badge">● 数据已更新</span></div>',
        unsafe_allow_html=True,
    )

    t0 = time.time()
    with st.spinner("正在扫描 arXiv 并构建领域库..."):
        papers = load_topic(topic)
    if not papers:
        st.warning("未检索到论文，请换一个主题。")
        return

    s = radar_stats(papers)
    st.markdown(
        f'<div class="radar-meta">近 30 天 · <b>{s["total"]}</b> 篇新论文 · 数据截止 {s["latest_date"]} · 本次耗时 {time.time()-t0:.1f}s</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">领域趋势</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        render_trend_chart(s["trend"])
    with c2:
        st.markdown('<div class="stat-panel">'
                    f'<div><div class="stat-num">{s["total"]}</div><div class="stat-label">近 30 天论文</div></div>'
                    f'<div><div class="stat-num">{len(s["trend"])}</div><div class="stat-label">活跃天数</div></div>'
                    '</div>', unsafe_allow_html=True)
        kws = "".join(f'<span class="tag-chip" style="font-size:{0.72 + (kw["count"] / (s["keywords"][0]["count"] or 1)) * 0.25:.2f}rem">{kw["word"]} <span style="color:#6e6e73;font-size:0.7rem">×{kw["count"]}</span></span>' for kw in s["keywords"][:12])
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:0.5rem">{kws}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">本周论文</div>', unsafe_allow_html=True)
    for p in papers[:20]:
        with st.expander(f"{p['title']}", expanded=False):
            st.markdown(
                f'<div class="paper-meta">{", ".join(p["authors"][:3])}{" 等" if len(p["authors"]) > 3 else ""} · {p["published"][:10]} · {p["arxiv_id"]} · <a href="{p["url"]}" target="_blank" style="color:#0071e3">arXiv 原文 ↗</a></div>',
                unsafe_allow_html=True,
            )
            with st.spinner("生成中文摘要..."):
                sm = summarize_paper(p)
            st.markdown(
                '<div class="summary-grid">'
                f'<div class="summary-field"><span class="summary-label">问题</span>{sm["problem"]}</div>'
                f'<div class="summary-field"><span class="summary-label">方法</span>{sm["method"]}</div>'
                f'<div class="summary-field"><span class="summary-label">结论</span>{sm["conclusion"]}</div>'
                f'<div class="summary-field"><span class="summary-label">创新点</span>{sm["innovation"]}</div>'
                '</div>', unsafe_allow_html=True,
            )
            with st.spinner("查找相关文献..."):
                recs = recommend_papers(p, topic, top_n=3)
            for r in recs:
                st.markdown(
                    f'<div class="source-card"><b>相关文献</b> · {r["arxiv_id"]} · <a href="{r["url"]}" target="_blank" style="color:#0071e3">{r["title"][:70]}</a><br><span style="color:#6e6e73;font-size:0.8rem">{r["reason"]}</span></div>',
                    unsafe_allow_html=True,
                )

    st.markdown(f'<div class="footer-note">Paper Radar · 数据源 arXiv (近 30 天) · 摘要由 deepseek 生成，回答均附来源 · 界面设计遵循 DESIGN.md</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
