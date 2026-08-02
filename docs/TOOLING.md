# 10 · 工具与技能盘点（项目制作资源）

> 目的：动手前确认可用资源，评估哪些现成、哪些需准备/配置。
> 结论：**大部分已就绪，只有依赖安装和 Streamlit Cloud 账号两步需要准备。**

## 一、已就绪（实测确认，无需准备）

| 工具/资源 | 状态 | 用途 | 备注 |
|---|---|---|---|
| Python 3.12 + uv 0.11 | ✅ 已装 | 开发环境 | venv 管理用 uv |
| gh CLI 2.95 | ✅ 已登录 (w3118597378-max) | GitHub 仓库 + 部署 | keyring 认证 |
| git 2.52 | ✅ 已配置 | 版本管理 | user 已设 |
| codex 0.144 | ✅ 已装 | AI 代码生成/驱动开发 | 复杂代码可交 codex |
| modelscope 1.38 | ✅ 已装 | 模型源（hf 不可达时的替代） | hf-mirror 实测不通 |
| **本地 embedding 模型** | ✅ **E:\models\bge-small-zh-v1.5 已存在** | 向量化（免费） | **重大利好：无需下载，直接加载** |
| DEEPSEEK_API_KEY | ✅ 已配置 | LLM 生成 | hermes .env 中有 |
| arXiv API | ✅ 实测 200, 0.37s | 论文数据源 | 免费无 key |
| RTX 3060 6GB | ✅ | embedding 加速 | CPU 也能跑 |

## 二、现成方案（skill 提供的直接可用方法论）

| 方案 | 来源 | 价值 |
|---|---|---|
| **RAG 项目模式** | `python-ai-pipeline` skill → `references/rag-project-pattern.md` | **本项目技术蓝本**：DeepSeek + bge 本地 embedding + ChromaDB + Streamlit 完整代码模式、验证清单、Windows 坑位（HF 符号链接警告、中文 chunk 分隔符） |
| 中国网络绕行 | `win-toolchain` skill | 模型源（ModelScope）、pip 镜像（阿里云）、HF 符号链接警告处理 |

## 三、需准备/配置（3 项）

| # | 事项 | 动作 | 风险/成本 |
|---|---|---|---|
| 1 | 项目依赖安装 | uv 建 venv + 装 sentence-transformers/langchain/chromadb/streamlit | 无风险；用阿里云镜像（清华源 403 已知坑） |
| 2 | Streamlit Community Cloud 账号 | GitHub 登录创建（免费） | 免费；绑定仓库后 push 即部署 |
| 3 | 项目 .env | 复制 DEEPSEEK_API_KEY 到项目 .env（gitignored） | 无风险 |

## 四、Windows 特定坑位（提前规避，来自 win-toolchain 实测）

| 坑 | 规避 |
|---|---|
| Hermes 终端导出 PYTHONPATH 会劫持项目 venv | **运行项目 Python 前先 `unset PYTHONPATH`** |
| HuggingFace 符号链接警告（Windows 不支持 symlink） | 设 `HF_HUB_DISABLE_SYMLINKS_WARNING=1` |
| 模型下载 hf 源不可达 | 直接用本地 E:\models 模型，零下载 |
| pip 清华源对部分包 403 | 用阿里云 `https://mirrors.aliyun.com/pypi/simple/` |
| 环境变量 MSYS 路径被原生工具读成字面量 | 一律用 Windows 格式 `E:\...` 或 `D:\...` |

## 五、结论

现成资源覆盖了技术栈的全部核心：**embedding 模型本地已有、LLM key 已配、数据源可达、部署工具链（gh）就绪、且有一份与本项目同构的 RAG 代码模式文档**。缺的只是依赖安装和 Streamlit Cloud 注册，都属于启动时 30 分钟内可完成的操作。

→ 可以直接进入 T0（环境准备），无需等待任何外部条件。
