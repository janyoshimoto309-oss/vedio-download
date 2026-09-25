# vedio-download · 万能视频下载（学习项目）

多平台视频链接解析与下载，核心能力基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp)。**仅供学习研究，请尊重版权与平台服务条款。**

## 文档（扩展功能请先读）

| 文档 | 说明 |
|------|------|
| [docs/README.md](./docs/README.md) | 文档索引与给 AI 的阅读说明 |
| [docs/01-需求分析.md](./docs/01-需求分析.md) | 需求、范围、已确认决策 |
| [docs/02-技术方案.md](./docs/02-技术方案.md) | 架构、双下载模式、yt-dlp 集成 |
| [docs/03-设计文档.md](./docs/03-设计文档.md) | UI、API 契约、组件清单 |
| [docs/04-实现与产品差异.md](./docs/04-实现与产品差异.md) | 用户界面 vs 后端下载策略 |

## 项目状态

**MVP 已实现**：前后端可本地运行，详见下方启动方式。

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

浏览器打开 <http://localhost:5173>（Windows 上建议用 `localhost` 访问，以便 Vite 代理正常）。

### 3. ffmpeg（推荐）

未安装时，部分「视频+音频合并」清晰度无法服务端下载。

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

联网可用公开视频链接在网页走通解析与下载；建议各测一条易直链与一条偏 YouTube/B 站的链接。

## 抖音解析

抖音网页接口需要新鲜访客 Cookie（不必登录）。任选其一：

1. 用浏览器打开目标视频并过完验证码，导出 Netscape 格式 Cookie 为 `backend/cookies.txt`
2. 启动后端前设置 `YTDLP_COOKIES_FROM_BROWSER=chrome`（Chrome 正在运行时可能读失败）

分享口令可直接粘贴，后端会抽出其中的 `v.douyin.com` 链接。
