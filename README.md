# Paper Radar · 项目说明

> 论文情报 Agent：给时间稀缺的领域追踪者，一个每天自动更新的情报雷达，10 分钟掌握一个领域一周的进展。
> 定位：订阅式领域情报追踪（非通用搜索）。核心卖点：引用溯源防编造、领域趋势雷达、中文结构化摘要。

## 目录结构

```
E:\paper-radar\
├── README.md              ← 本文件（项目说明 + 索引）
├── AGENTS.md              ← 项目规则（Codex/agent 自动读取）
├── DESIGN.md              ← 设计定案（经典苹果白，统一参照）
├── prototype-prompt.txt   ← Codex 原型规格 prompt
├── index.html             ← 前端原型（Codex 产出，待验收）
└── docs\
    ├── PRD.md             ← 产品需求文档（副本）
    ├── TASKS.md           ← 分步任务清单（副本）
    ├── TOOLING.md         ← 工具与技能盘点（副本）
    ├── SCOPE.md           ← MVP 范围共识书（副本）
    └── BASELINE.md        ← 参考标准基线（副本）
```

## 文档索引

| 文档 | 位置 | 用途 |
|---|---|---|
| 设计定案 | `DESIGN.md` | 配色/字体/组件/动效权威定义 |
| PRD | `docs/PRD.md` | 功能需求 + 验收标准 |
| 任务清单 | `docs/TASKS.md` | 推进依据（T0~T3） |
| 工具盘点 | `docs/TOOLING.md` | 环境就绪情况 |
| **完整文档链（含定位/竞品/用户研究/发展路径）** | Obsidian：`论文情报Agent/` | 项目全案叙事，源头文档 |

## 当前状态

- [x] 范围共识冻结（MVP = 领域雷达/结构化摘要/深度问答/文献推荐）
- [x] 参考标准基线确认（Elicit/paper-qa 等四层对标）
- [x] PRD v1.0
- [x] 任务清单 + 工具盘点（环境实测就绪）
- [x] 设计定案（经典苹果白）
- [x] 前端原型（Codex 制作 + 两步验收通过，见 index.html）
- [x] 开发 T0 环境准备（venv/依赖/.env/embedding 全验收通过）
- [x] 开发 M1 数据管道（arXiv→chunk→bge→ChromaDB，陌生主题 35.6s 入库）
- [x] 开发 M2 核心功能（雷达/摘要/推荐/界面，陌生主题 23s 出图，10/10 摘要完整）
- [x] 开发 M3（问答溯源 20/20 通过 / 评测集 / GitHub 仓库 / 部署文档）
- [x] 上线（Streamlit Community Cloud：https://paper-rad-adzueyihx6gb3swigyfd3g.streamlit.app/）

## 技术栈

arXiv API（免费）→ 本地 bge embedding（E:\models 已有）→ ChromaDB → deepseek LLM → Streamlit 界面

## 快速开始（本地）

前置：Python 3.12 + uv；本地 embedding 模型 `E:\models\bge-small-zh-v1.5`；deepseek key。

```bash
cd E:\paper-radar
unset PYTHONPATH                      # Windows: Hermes 终端会劫持 venv，必须先清
uv venv .venv --python 3.12
uv pip install --index-url https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
# 配置 .env：DEEPSEEK_API_KEY=sk-...
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
uv run streamlit run app/app.py
```

数据管道（可选，界面内搜索会自动入库）：

```bash
uv run python -m app.pipeline "retrieval augmented generation" 30 100
```

## 架构

```
arXiv API ──> arxiv_fetcher.py ──> papers ──> embedder.py (chunk 500/100 + bge 512d)
                                                      │
                                                      ▼
user 提问 ──> LLM 翻译成英文 ──> ChromaDB (cosine) ──> top-k chunks
                                      │
                                      ▼
              deepseek LLM ──> 中文回答 + [n] 引用角标 + 来源卡片
```

## 评测

```bash
uv run python -m app.run_eval        # 20 问：溯源率/拒绝率自动判定，见 eval/test_set.md
```

## 部署（Streamlit Community Cloud）

1. 仓库：`github.com/w3118597378-max/paper-radar`
2. Cloud 绑定仓库 → 主分支，入口 `app/app.py`，`.python-version` 锁 Python 3.12
3. Secrets 配 `DEEPSEEK_API_KEY`
4. 公网地址：https://paper-rad-adzueyihx6gb3swigyfd3g.streamlit.app/
5. 已知坑位：arXiv API 必须用 https（http 会 301 且 urllib 跨协议重定向不稳）；requirements 里 langchain-community 最高 1.0.0a1（用 >=0.4,<1.1）；embedding 模型云端从 ModelScope 下载（首次冷启动较慢）

## 功能冻结

M3 结束功能冻结，只修 bug 不增需求；v1.1 backlog：每日推送 / 收藏 / 导出。

