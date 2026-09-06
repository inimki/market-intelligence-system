# Nginx 与一键部署验收

日期：2026-09-06；环境：Windows、Docker Desktop Linux 容器。

| 验收项 | 结果 |
|---|---|
| `scripts/deploy.ps1 -NoBrowser` | 完整执行成功，退出码 0 |
| 六个服务 | nginx、api、collector、analysis、postgres、n8n 全部 healthy |
| Nginx 配置 | `nginx -t` 通过 |
| 网页与接口 | 首页、`/health`、`/api/docs` 返回 200 |
| 浏览器指南 | `/help` 跳转保留端口；`/help.html`、`/guide.txt` 返回 200 |
| 实际调研 | 经 Nginx 提交工业自动化 / 西门子调研，1 个信源、采集 1 条、失败 0 个 |
| 报告 | HTML 可浏览；下载接口 200，带 attachment 响应头 |
| 新 API 镜像的离线演示 | 无 Key、断网、空 SQLite 数据库：4 条样例首次新增 3、重复 1；重跑新增 0、重复 4 |
| 新分析镜像 | 无 Key、断网、只读运行，健康函数和 PandasAI/LiteLLM 导入通过 |
| 采集镜像 | 实际启动 Chromium 并渲染测试页面 |
| Browser Use 模型配置 | DeepSeek / OpenAI 构造通过；未进行真实模型请求，不代表所有供应商和模型已验证 |
| 全新配置 | 临时空目录自动生成 .env、独立随机凭据；重跑配置文件哈希不变 |
| 新 n8n 环境 | 一次性空容器成功导入并发布工作流，测试后容器自动移除 |
| 自动测试 | Python 12 项测试、Ruff 和 Windows 配置初始化测试通过 |

## 构建范围与限制

API 和 Analysis 镜像完成了从 Python 基础镜像的重新构建。Collector 的完整首次构建
在 Debian 系统库下载阶段遇到构建连接 EOF；为完成本机部署，最终复用了本机原有且已
验证的采集依赖镜像，并重新安装应用、验证浏览器与启动流程。

本机 `.env` 的 `COLLECTOR_BASE_IMAGE` 指向本机缓存标签，该配置和真实 Key 不会进入仓库。
新用户生成的 `.env` 不包含该缓存设置，仍走官方 Python 基础镜像的完整安装流程。
此次未在另一台全新电脑上完成全量冷安装；首次下载的成功与耗时仍依赖网络和上游服务。

已将 Collector 的 Python 包、系统库、浏览器安装拆分缓存，并启用 pip 下载缓存，
降低中断后重试的成本。实际生成的调研数据与报告只保留在本机 Docker 数据卷中。
