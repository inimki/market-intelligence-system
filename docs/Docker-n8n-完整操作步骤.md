# Docker + n8n 完整操作步骤

这份文档按“先会用，再理解原理”的顺序编写。当前电脑已经完成安装和首次构建；你平时从第 2 步开始即可。

## 1. 首次部署需要什么

必须具备：

1. Windows 已启用虚拟化。
2. WSL 2 可运行，`wsl --version` 能显示版本。
3. Docker Desktop 已启动，左下角显示 Engine running。
4. 新版双击根目录 `一键部署.cmd` 会自动创建 `.env`；`AI_API_KEY` 是可选项。
5. Docker 至少分配约 4 GB 内存，磁盘保留约 10 GB 空间。

验证命令：

```powershell
wsl --version
docker version
docker compose version
```

三条命令都能正常显示版本后，运行：

```powershell
cd path\to\market-intelligence-system
.\scripts\finish-docker-n8n.ps1
```

脚本会自动检查环境、创建五个容器、等待健康检查、加入三个官方公开信源，并导入和发布 n8n 工作流。

## 2. 平时启动和停止

启动：

```powershell
cd path\to\market-intelligence-system
docker compose up -d
```

查看状态：

```powershell
docker compose ps
```

正常时会看到 `postgres`、`api`、`collector`、`analysis`、`n8n` 五个服务。

停止但保留数据：

```powershell
docker compose stop
```

重新启动：

```powershell
docker compose start
```

不要随意执行 `docker compose down -v`，其中 `-v` 会删除数据库、n8n 配置和报告卷。

## 3. 第一次打开 n8n

浏览器访问 <http://127.0.0.1:5678>。第一次会要求创建本机管理员账号，邮箱和密码由你自己设置。

进入后应看到“市场情报自动收集与报告”。该工作流已经发布，默认每天 08:00 自动运行：

```text
每天08:00 / 手动触发
        ↓
POST http://api:8000/api/runs
        ↓
判断运行结果
   ├─ 生成成功摘要
   └─ 生成失败告警
```

## 4. 手动跑一次完整流程

最直观的方法：

1. 打开 n8n。
2. 打开“市场情报自动收集与报告”。
3. 点击 Execute workflow。
4. 等待节点变绿。

也可以打开 <http://127.0.0.1:8000/api/docs>，在 `POST /api/runs` 点击 `Try it out` 和 `Execute`。

结果字段含义：

- `source_count`：本次启用的信源数。
- `collected_count`：采集到的网页数。
- `inserted_count`：数据库中新加入的数量。
- `duplicate_count`：根据 URL 与内容指纹识别出的重复数量。
- `failed_count`：失败信源数。
- `report_path`：生成的 HTML 报告路径。

## 5. 查看结果

- 最新报告：<http://127.0.0.1:8000/reports/latest>
- API 操作页：<http://127.0.0.1:8000/api/docs>
- 信源列表：<http://127.0.0.1:8000/api/sources>
- 运行历史：<http://127.0.0.1:8000/api/runs>
- 已入库情报：<http://127.0.0.1:8000/api/items>

## 6. 添加新信源

在 API 页面使用 `POST /api/sources`：

```json
{
  "name": "某公司新闻中心",
  "url": "https://example.com/news",
  "kind": "static",
  "enabled": true,
  "tags": ["竞争对手", "产品动态"]
}
```

- 普通公开页面用 `static`，由 Crawl4AI 采集。
- 必须点击或翻页的页面才用 `interactive`，由 Browser Use 操作。
- 只添加公开且允许访问的网页；遇到登录、验证码、付费墙或明确禁止自动访问时应停止。

## 7. 使用 PandasAI + DeepSeek 提问

在 API 页面调用 `POST /api/analysis/ask`：

```json
{
  "question": "根据已采集内容，概括三家公司值得关注的市场信号，并说明信息不足之处。",
  "item_limit": 100
}
```

固定数量、去重和报告统计由普通 Pandas 代码完成；PandasAI 只负责自然语言探索，重要结论仍要回到原始来源核对。

## 8. 五个服务分别做什么

| 服务 | 作用 |
|---|---|
| PostgreSQL | 保存信源、情报、运行历史及 n8n 数据 |
| API | 整条业务流水线入口、去重、报告访问 |
| Collector | Crawl4AI 普通采集 + Browser Use 交互采集 |
| Analysis | 在隔离的只读容器中运行 PandasAI + DeepSeek |
| n8n | 定时触发、流程判断、后续通知扩展 |

## 9. 常见故障

### Docker 显示 Virtualization support not detected

先重启 Windows，再检查：

```powershell
wsl --status
docker version
```

如果 `docker version` 没有 Server 部分，打开 Docker Desktop 并等待 Engine running。

### 端口 8000 或 5678 被占用

```powershell
Get-NetTCPConnection -LocalPort 8000,5678 -State Listen
```

先确认占用进程属于什么程序，不要直接结束不认识的进程。

### 查看容器错误

```powershell
docker compose logs --tail 120 api
docker compose logs --tail 120 collector
docker compose logs --tail 120 analysis
docker compose logs --tail 120 n8n
```

### 修改代码后重新构建

```powershell
docker compose build api collector analysis
docker compose up -d
```

首次构建 Collector 很慢，因为它包含 Chromium；后续构建通常会使用缓存。

## 10. 验收命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
docker compose config --quiet
docker compose ps
```

本次本机验收结果见 `docs\验收记录.md`。
