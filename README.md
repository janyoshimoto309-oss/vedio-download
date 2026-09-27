# vedio-download · 万能视频下载（学习项目）

多平台视频链接解析与下载。YouTube、B 站等走 [yt-dlp](https://github.com/yt-dlp/yt-dlp)；**抖音单独用无头浏览器**抓播放地址。**仅供学习研究，请尊重版权与平台服务条款。**

## 文档（扩展功能请先读）

| 文档 | 说明 |
|------|------|
| [docs/README.md](./docs/README.md) | 文档索引与给 AI 的阅读说明 |
| [docs/01-需求分析.md](./docs/01-需求分析.md) | 需求、范围、已确认决策 |
| [docs/02-技术方案.md](./docs/02-技术方案.md) | 架构、双下载模式、平台分流 |
| [docs/03-设计文档.md](./docs/03-设计文档.md) | UI、API 契约、组件清单 |
| [docs/04-实现与产品差异.md](./docs/04-实现与产品差异.md) | 用户界面 vs 后端下载策略 |
| [docs/05-视频下载功能总结.md](./docs/05-视频下载功能总结.md) | 已交付下载能力与踩坑 |
| [docs/06-AI学习笔记功能总结.md](./docs/06-AI学习笔记功能总结.md) | 已交付学习笔记能力与踩坑 |
| [docs/08-AI视频问答功能总结.md](./docs/08-AI视频问答功能总结.md) | 已交付解析后问答与踩坑 |

## 项目状态

**MVP 已实现**：前后端可本地运行，详见下方启动方式。抖音解析不依赖手动导出 Cookie（失败时仍可把 Netscape `cookies.txt` 放到 `backend/` 作 yt-dlp 回退）。

## 技术栈

- 前端：Vue 3 + Vite + Tailwind CSS（端口 5173，`/api` 代理到后端）；脑图画布为 `mind-elixir`（见 [06](./docs/06-AI学习笔记功能总结.md)）
- 后端：Python 3.10+、FastAPI、yt-dlp、Playwright（仅抖音）、httpx（端口 8000）
- 可选：ffmpeg（HLS/DASH 或音视频分离合并时需要）
- 可选：`backend/.env` 的 `DEEPSEEK_API_KEY`（学习笔记与问AI，默认 `deepseek-flash`；见 `backend/.env.example` 与 https://api-docs.deepseek.com/ ）

## 本地运行

### 1. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python -m uvicorn main:app --reload --port 8000
```

健康检查：<http://127.0.0.1:8000/api/health>。大模型是否配好看 <http://127.0.0.1:8000/api/notes/ready> 的 `llm`。

首次装 Playwright 会下载 Chromium，体积较大。必须用**装了依赖的同一个虚拟环境**启动 uvicorn，否则抖音解析会失败。

### 2. 前端（另开终端）

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 <http://localhost:5173>（Windows 上建议用 `localhost` 访问，以便 Vite 代理正常）。

### 3. ffmpeg（推荐）

未安装时，部分「视频+音频合并」清晰度无法服务端下载（B 站 / YouTube 高清常见）。

## 下载方式（用户 vs 技术）

- **用户界面**：选清晰度 →「开始下载」；不展示 server/直链等选项。
- **后端**：自动在 `server`（先落盘再发链接）、`redirect`、`proxy` 间选择；API 仍支持 `prefer_mode` 供调试。
- 说明见 [docs/04-实现与产品差异.md](./docs/04-实现与产品差异.md)（含本地 server 模式可能短暂占两份磁盘）。

## 测试

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

联网建议各测：一条 YouTube、一条 B 站、一条抖音分享口令或 `/video/{id}`。学习笔记与问AI请用**带 CC / 自动字幕**的油管或 B 站讲解；在 `backend/.env` 配置 `DEEPSEEK_API_KEY`（不要写进 `.env.example`）。无 Key 时仍可点「生成字幕」，问答不可用。解析成功后可直接在「问AI」连问两句，不必先生成笔记。

## 平台分流

| 平台 | 解析 | 下载 |
|------|------|------|
| YouTube / B 站等 | yt-dlp（不带抖音 Cookie） | yt-dlp；高清常为音视频分离，需 ffmpeg |
| 抖音 | Playwright 打开页面，按作品 id / 主播放器取直链 | httpx 拉 CDN；失败再回退 yt-dlp + 可选 `cookies.txt` |

输入框可粘贴分享口令；后端会抽出链接，并把用户主页 `modal_id` 改写成 `/video/{id}`。不要贴推荐首页（没有作品 id）。

`backend/cookies.txt`、`backend/downloads/` 已在 `.gitignore`，不要提交。
