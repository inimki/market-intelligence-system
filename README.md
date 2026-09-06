# 市场情报自动收集与报告平台

[![CI](https://github.com/inimki/market-intelligence-system/actions/workflows/ci.yml/badge.svg)](https://github.com/inimki/market-intelligence-system/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

输入行业和公司，发现公开官网信源，采集、清洗和去重，生成有来源链接的中文 HTML 报告。
适合本地调研、个人学习和市场情报工作流实践。

**Windows：安装并启动 Docker Desktop → 下载并解压代码 → 双击 `一键部署.cmd`。**

[下载项目 ZIP](https://github.com/inimki/market-intelligence-system/archive/refs/heads/main.zip) ·
[中文使用说明（TXT）](使用说明.txt) · [开发与代码解析](docs/开发指南.md) ·
[部署设计参考](docs/部署设计与参考.md)

## 可以完成什么

- 中文控制台输入行业、最多 8 家公司和关注主题。
- 发现候选公开官网页面，采集正文，规范化 URL、生成内容指纹并去重入库。
- Pandas 生成可复算统计；报告支持浏览器预览和 HTML 下载。
- Crawl4AI 用于普通网页，Browser Use 用于可授权交互的网页。
- 可选 PandasAI 问答；支持 DeepSeek、OpenAI 和其他 OpenAI 兼容 API。
- n8n 定时运行；Nginx 提供网页、API、报告和帮助页的统一入口。

搜索发现依赖公开搜索页面，可能受网络和网页改版影响。报告包含统计、摘要及证据，
并不保证搜索穷尽，也不替代人工研判。配置 Key 后的 AI 问答是独立的可选功能。

## 环境要求

| 项目 | 要求 |
|---|---|
| 推荐环境 | 支持当前 Docker Desktop 的 64 位 Windows，WSL 2 后端和 CPU 虚拟化已启用 |
| 必须安装 | Docker Desktop（含 Docker Compose V2），并确认 Engine running |
| 建议资源 | 4 核 CPU、16 GB 内存、15 GB 以上可用磁盘；更多并发浏览器需要更多内存 |
| 网络 | 能访问镜像仓库、Python 软件源、浏览器下载服务与目标网页 |
| 端口 | 8080 网页、8000 本地 API 调试、5678 n8n |
| 不必单独安装 | Python、Nginx、PostgreSQL、Node.js 和三个 Python 组件环境 |
| AI Key | 可选；普通网页采集、统计和 HTML 报告不要求 Key |

[Docker Desktop 官方安装说明](https://docs.docker.com/desktop/setup/install/windows-install/)。
系统组件初次安装可能需要管理员操作和重启；项目脚本会在 Docker 未就绪时说明原因。

## Windows 一键部署

1. 在 GitHub 点击 **Code → Download ZIP**，解压到普通文件夹。不能直接在压缩包内运行。
2. 打开 Docker Desktop，等待 **Engine running**。
3. 双击项目根目录 **一键部署.cmd**。
4. 首次下载和构建可能持续较长时间；以终端进度为准。完成后浏览器自动打开控制台。

脚本自动执行：检测 Docker → 首次生成 `.env` 和两份独立随机凭据 → 构建并启动六个服务
→ 空数据库添加示例信源 → 导入并发布 n8n 工作流 → 验证 Nginx 与应用健康状态 → 打开网页。
首次访问 n8n 仍需要本人创建管理账号。

已有 `.env`、API Key、数据库和报告会保留。再次双击可启动服务、更新镜像并应用新配置。
安装失败会停留在终端显示错误，不会把失败报告为成功。

命令行等效入口：

```powershell
git clone https://github.com/inimki/market-intelligence-system.git
cd market-intelligence-system
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy.ps1
```

## 打开和使用

| 页面 | 地址 |
|---|---|
| 平台首页（Nginx） | http://127.0.0.1:8080/ |
| 浏览器使用指南 | http://127.0.0.1:8080/help |
| API 操作页 | http://127.0.0.1:8080/api/docs |
| 最新报告 | http://127.0.0.1:8080/reports/latest |
| n8n 管理页面 | http://127.0.0.1:5678/ |

在首页点击“新建市场调研”，输入行业、公司及关注主题，提交后打开或下载报告。
未生成过报告时，“最新报告”暂时不可用。n8n 保持独立管理入口。

Nginx 负责转发请求和提供静态帮助页，FastAPI 继续生成页面、执行调研和报告。
该调整便于以后配置域名、HTTPS 与访问控制；它本身不会提高抓取成功率或 AI 分析质量。

## 可选：接入 AI

首次部署不需要提供 Key。要启用 AI，在本机 `.env` 中修改下面四项：

| 变量 | DeepSeek | OpenAI / OpenAI 兼容服务 |
|---|---|---|
| `AI_PROVIDER` | `deepseek` | `openai` |
| `AI_API_KEY` | 自己的 DeepSeek Key | 自己的服务商 Key |
| `AI_BASE_URL` | `https://api.deepseek.com` | OpenAI 为 `https://api.openai.com/v1`；其他服务按官方文档 |
| `AI_MODEL` | `deepseek-v4-flash` | 账户可用且支持该集成的模型 ID |

修改后再次双击一键部署，或执行：

```powershell
docker compose up -d collector analysis
```

**只运行 `docker compose restart` 不会更新容器环境变量。**
其他兼容接口需要支持所用的工具调用和结构化输出，并非全部模型都已在本项目验证。
OpenAI 兼容示例不是成功测试承诺。可另填 `BROWSER_USE_API_KEY` 为交互采集使用独立模型服务。
详见 [.env.example](.env.example)，不要共享真实 Key。

## 日常操作

```powershell
docker compose ps                       # 查看六个服务
docker compose stop                     # 停止并保留数据
docker compose start                    # 启动已有容器
docker compose logs --tail 80 nginx api  # 网页故障日志
```

通过 Git 下载的用户，更新前备份数据，执行 `git pull` 后再次双击一键部署。
不要使用 `docker compose down -v`，除非确实要删除全部持久化卷。
数据库密码和 n8n 加密密钥初始化后不能随意修改；脚本不会自动轮换已有值。

## Linux / macOS

Compose 配置使用 Linux 容器；当前一键入口和端到端验收面向 Windows Docker Desktop。
其他系统需要 Docker Engine/Desktop 和 Compose V2，按以下顺序手动部署：

```bash
cp .env.example .env
# 编辑 .env，给数据库密码和 n8n 加密密钥分别填写独立随机十六进制字符串。
docker compose up -d --build
docker compose ps
```

进入首页添加行业和公司即可调研。n8n 首次创建管理账号后，在界面导入
`workflows/market-intelligence.json` 并发布工作流。此手动路线不会自动添加示例信源或发布工作流。

## 服务组成

```text
浏览器 → Nginx :8080 → FastAPI → PostgreSQL
                          ├→ Collector（Crawl4AI / Browser Use）
                          └→ Analysis（PandasAI，可选）
n8n :5678 ────────────→ FastAPI
```

六个服务由 Compose 管理。数据库、原始证据、报告及 n8n 配置保存在 Docker 数据卷中。
当前默认仅监听本机地址，适用于本地部署。公网部署还需自行配置认证、HTTPS、域名、
备份及适用的合规措施；本项目未提供已完成加固的公共 SaaS 部署包。

## 开发、许可证和参考

本地 Python 开发需 3.11 和三个独立虚拟环境，详见 [开发指南](docs/开发指南.md)。
测试：`pytest -q`；代码检查：`ruff check app tests`。

原创应用代码采用 [MIT](LICENSE)；n8n 使用 Sustainable Use License，其余第三方依赖
分别遵循上游条款。参见 [第三方声明](THIRD_PARTY_NOTICES.md)、
[隐私与合规说明](PRIVACY_AND_COMPLIANCE.md) 和 [安全政策](SECURITY.md)。

部署文档参考 [Crawl4AI](https://github.com/unclecode/crawl4ai/blob/main/deploy/docker/README.md)
及 [Browser Use Web UI](https://github.com/browser-use/web-ui) 的环境模板、Compose 与健康检查做法。
Nginx 配置参考[官方反向代理文档](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)。
