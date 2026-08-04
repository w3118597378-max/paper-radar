# Paper Radar · 项目规则（AGENTS.md）

Codex / agent 在本项目目录内工作时自动读取本文件。请遵守。

## 项目一句话

论文情报 Agent（Paper Radar）：给领域追踪者一个情报雷达，输入研究主题后 10 分钟掌握该领域一周进展。核心卖点：**引用溯源防编造（无来源不回答）**、领域趋势雷达、中文结构化摘要。

## 铁律

1. **设计定案不可自由发挥**：配色/字体/组件/动效以 `DESIGN.md` 为准（经典苹果白：`#ffffff` 底 + `#0071e3` 苹果蓝 + `#1d1d1f` 近黑字）。禁止「软件默认感」（默认灰蓝渐变）。
2. **MVP 范围冻结**：只做 领域雷达 / 结构化摘要 / 深度问答（引用溯源）/ 相关文献推荐。每日推送、收藏、注册、导出、全文解析一律后置 v1.1。
3. **引用溯源是差异化核心**：任何回答必须附来源；检索不到就明说，绝不编造。
4. **界面中文**，数据/论文标题保留英文原文。

## 关键路径

- 设计定案：`DESIGN.md`
- 功能需求/验收：`docs/PRD.md`
- 推进任务：`docs/TASKS.md`
- 环境与工具：`docs/TOOLING.md`

## 技术栈约定

- 数据源：arXiv API（`https://export.arxiv.org/api/query`，免费无 key，限流约 1 req/3s，需缓存+重试；浏览器端经 Cloudflare Worker 代理绕 CORS）
- Embedding：本地 `E:\models\bge-small-zh-v1.5`（**不要尝试从 HuggingFace 下载，国内不可达；ModelScope 可作后备源**）
- 向量库：v1 用 ChromaDB（落盘，Python 管道）；**v2 线上版为纯浏览器端 JS 余弦检索**（零后端）
- LLM：deepseek（`https://api.deepseek.com/v1`，OpenAI 兼容），v1 key 从 `.env` 读；**v2 线上版由访问者浏览器 localStorage 自填 key 直连（CORS 已验证放行）**
- 界面：**v2 线上版 = 纯 HTML 前端（`public/index.html`，浏览器端 RAG）**；v1 Python 版 = Streamlit（`app/app.py`，本地可跑）

## Windows 环境坑位（实测）

- Hermes 终端会注入 `PYTHONPATH` 指向 hermes-agent venv：运行本项目 Python 前**先 `unset PYTHONPATH`**
- 环境变量用 Windows 格式（`E:\...`），不要用 MSYS 路径（`/e/...`）
- pip/uv 镜像用阿里云 `https://mirrors.aliyun.com/pypi/simple/`（清华源部分包 403）
- 加载 embedding 模型前设 `HF_HUB_DISABLE_SYMLINKS_WARNING=1`
