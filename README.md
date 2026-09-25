# vedio-download · 万能视频下载（学习项目）

多平台视频链接解析与下载，核心能力基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp)。**仅供学习研究，请尊重版权与平台服务条款。**

## 文档（扩展功能请先读）

| 文档 | 说明 |
|------|------|
| [docs/README.md](./docs/README.md) | 文档索引与给 AI 的阅读说明 |
| [docs/01-需求分析.md](./docs/01-需求分析.md) | 需求、范围、已确认决策 |
| [docs/02-技术方案.md](./docs/02-技术方案.md) | 架构、双下载模式、yt-dlp 集成 |
| [docs/03-设计文档.md](./docs/03-设计文档.md) | UI、API 契约、模块与扩展点 |

## 技术栈

- 前端：Vue 3 + Vite + Tailwind CSS（端口 5173，`/api` 代理到后端）
- 后端：Python 3.10+、FastAPI、yt-dlp（端口 8000）
- 可选：ffmpeg（HLS/DASH 或音视频分离合并时需要）

## 本地运行

### 1. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

健康检查：<http://127.0.0.1:8000/api/health>

### 2. 前端（另开终端）

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 <http://localhost:5173>）。

### 3. ffmpeg（推荐）

Windows 可将 ffmpeg 加入 PATH。未安装时，部分清晰度无法服务端合并，页面会提示。

## 下载模式

| mode | 行为 |
|------|------|
| `server` | yt-dlp 落盘到 `backend/downloads/`，再通过 `/api/video/file/{task_id}` 下载（约 1 小时过期） |
| `redirect` | 返回直链，浏览器直接跳转 |
| `proxy` | 服务端带 header 流式转发 `/api/video/proxy/{token}` |

解析结果会给出 `recommended_mode`；下载页可在高级选项里选 `auto` / `server` / `direct`。直链不可用时自动回退 `server`。

## 冒烟测试

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m unittest tests.test_strategy -v
```

联网后可用公开短视频链接在网页完成解析与下载。建议各测一条「易直链」与一条「需服务端」的链接。
