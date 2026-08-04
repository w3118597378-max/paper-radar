# Paper Radar · 非功能验收记录（T3.6）

> 对照 PRD §6 非功能需求，逐项验收。日期：2026-08-03（Python 全栈版）/ 2026-08-04（浏览器端版）

## 版本说明

项目经两轮演进，均完成验收：

1. **v1 Python 全栈**（Streamlit + ChromaDB）：arXiv → 本地 bge → ChromaDB → deepseek → Streamlit 界面
2. **v2 纯浏览器端**（当前线上）：arXiv 经 Cloudflare Worker 代理 → Transformers.js 本地 bge → JS 余弦检索 → 用户 key 直连 deepseek

## 验收结果（v1 Python 全栈，本地实测）

| 类别 | 需求 | 验收标准 | 实测结果 | 状态 |
|---|---|---|---|---|
| 性能 | 冷启动 ≤ 60s | 首次加载计时 | 服务就绪 3s，首次搜索 21~36s（缓存命中）；陌生主题 35.6s 入库 | ✅ |
| 性能 | 单次检索响应 ≤ 10s | 问答操作计时 | 20 问评测单问 2.3~4.6s（含 LLM 翻译+生成） | ✅ |
| 数据持久化 | 论文库/向量库落盘，重启不丢 | 重启后数据核对 | ChromaDB 重启后 495+508 chunks 完整可查 | ✅ |
| 安全 | API key 走 Secrets，代码无明文 | 代码扫描确认 | .env 未入库（.gitignore）；git grep 无 sk- 明文 | ✅ |
| 成本 | 月运行成本 ≤ ¥10 | 账单核算 | 估算 ¥1~2/月（deepseek-chat ≈ ¥1/百万 token） | ✅ |
| 兼容性 | 主流浏览器可访问 | Chrome/Edge 实测 | Chrome 全流程走通 | ✅ |

## 验收结果（v2 浏览器端，线上实测）

| 类别 | 需求 | 验收标准 | 实测结果 | 状态 |
|---|---|---|---|---|
| 性能 | 页面加载 ≤ 5s | 首屏计时 | 静态资源即开即用；模型同域 24MB，首次 ~2s 加载（浏览器缓存后毫秒级） | ✅ |
| 性能 | 拉取 + 出图 ≤ 60s | 搜索计时 | 线上实测 50 篇论文 ~15s 出图（arXiv 网络往返主导） | ✅ |
| 安全 | 代码零密钥 | 仓库扫描 | worker.js 无任何 key；deepseek key 仅存访问者 localStorage | ✅ |
| 成本 | 月成本 ≈ ¥0 | 账单核算 | Cloudflare Workers 免费层 + arXiv 免费 + 浏览器本地计算 | ✅ |
| 兼容性 | 主流浏览器 | Chrome 实测 | 线上 Chrome 全链路（拉取/雷达/向量/问答）走通，console 0 错误 | ✅ |
| CORS | 跨域调用无阻塞 | 实测 | arXiv 经同域 Worker 代理（官方 API 无 CORS 头）；deepseek 官方支持浏览器直连 | ✅ |

## 成本估算（v2 浏览器端，¥/月）

| 项 | 费用 |
|---|---|
| Cloudflare Workers 免费层（10 万请求/天） | ¥0 |
| arXiv API（免费） | ¥0 |
| bge embedding（访问者浏览器本地） | ¥0 |
| 静态托管（Assets） | ¥0 |
| **服务方合计** | **¥0** |

> 注：LLM 调用（摘要/问答）使用访问者自填的 DeepSeek key，费用由访问者自行承担，服务方零成本。

## 24h 稳定性

- v1 计划未挂测（已演进至 v2）
- v2 为静态资源 + 无状态 Worker，无持久进程、无内存泄漏风险；Cloudflare 平台托管，稳定性由平台保障
