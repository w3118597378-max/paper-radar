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
- [ ] 开发 M3（问答溯源/部署/测试）
- [ ] 上线（Streamlit Community Cloud）

## 技术栈

arXiv API（免费）→ 本地 bge embedding（E:\models 已有）→ ChromaDB → deepseek LLM → Streamlit 界面
