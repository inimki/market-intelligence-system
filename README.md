# 市场情报自动收集与报告系统

[![CI](https://github.com/inimki/market-intelligence-system/actions/workflows/ci.yml/badge.svg)](https://github.com/inimki/market-intelligence-system/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

这是一个可运行的学习型完整项目，把 **Crawl4AI + Browser Use + n8n + PandasAI + Python** 组合成一条可追溯的市场情报流水线。

本仓库的原创应用代码采用 MIT License。第三方组件保留各自许可证；其中 n8n 使用
Sustainable Use License，不属于 OSI 定义的传统开源许可证。详情见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

如果你想边运行边理解，请直接阅读：[`docs/一步一步理解系统.md`](docs/一步一步理解系统.md)。

如果你只想先把系统用起来，请阅读：[`先看这里-操作步骤.md`](先看这里-操作步骤.md)，也可以双击 `scripts/启动系统.cmd` 一键启动三个本地服务。

系统做的事情：

1. 读取要关注的网站和采集方式。
2. 普通页面使用 Crawl4AI；必须点击、登录或翻页的页面使用 Browser Use。
3. Python 统一 URL、标题、时间和正文格式。
4. 使用“规范化 URL + 内容 SHA-256”阻止重复入库。
5. Pandas 生成可复算指标；PandasAI只负责可选的探索性问数。
6. 生成带原文证据和来源链接的 HTML 报告。
7. n8n 定时调用整条流水线，并处理成功通知和失败告警。
8. 在中文控制台输入行业、公司和关注主题，自动发现公开官网信源并生成可在线浏览、可下载的 HTML 报告。

主要第三方组件：

- [Crawl4AI](https://github.com/unclecode/crawl4ai)
- [Browser Use](https://github.com/browser-use/browser-use)
- [n8n](https://github.com/n8n-io/n8n)
- [PandasAI](https://github.com/sinaptik-ai/pandas-ai)

## 先理解项目的六个入口

| 入口 | 作用 |
|---|---|
| `app/cli.py` | 初学者首先运行的命令行入口 |
| `app/main.py` | FastAPI 服务入口，n8n 调用它 |
| `app/pipeline.py` | 一次完整情报运行的主调用链 |
| `app/collectors/router.py` | 根据 source.kind 选择采集器 |
| `app/normalization.py` | 标准化、内容指纹和证据提取 |
| `app/reporting.py` | 把数据和指标写入 HTML 报告 |

完整调用链：

```text
CLI / POST /api/runs
        ↓
MarketIntelligencePipeline.run()
        ↓
Repository.list_sources()
        ↓
CollectorRouter
   ├─ DemoCollector
   ├─ Crawl4AICollector
   └─ BrowserUseCollector
        ↓
to_intel_item() → Repository.insert_item()
        ↓
DeterministicAnalyzer → HtmlReportGenerator
        ↓
RunResult + HTML报告
```

---

## 第 1 步：运行不需要 Key 的离线演示

本机已经安装过依赖时，可以直接双击 PowerShell 执行：

```powershell
.\scripts\run-demo.ps1
```

### 1.1 创建 Python 3.11 虚拟环境

Windows PowerShell：

```powershell
cd path\to\market-intelligence-system
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

预期：

```text
Python 3.11.x
```

### 1.2 安装基础依赖

```powershell
pip install -U pip
pip install -e ".[dev]"
```

这一步只安装数据库、Pandas、FastAPI、报告和测试依赖，不会安装浏览器组件。

### 1.3 运行完整离线链路

```powershell
market-intel demo --open
```

预期中间结果：

- 创建 `data/market_intel.db`。
- 读取 `data/demo_documents.json` 的 4 条样例。
- 识别其中 1 条重复记录。
- 数据库保留 3 条唯一情报。
- 创建 `data/reports/market-intelligence-run-0001.html`。
- 自动打开报告。

第二次再运行：

```powershell
market-intel demo
```

预期 `inserted_count=0`、`duplicate_count=4`，证明任务重跑不会重复入库。

---

## 第 2 步：启动 API，观察 n8n 将要调用什么

```powershell
uvicorn app.main:app --reload
```

浏览器打开：

- 中文控制台：<http://127.0.0.1:8000/>
- API 文档：<http://127.0.0.1:8000/api/docs>
- 健康检查：<http://127.0.0.1:8000/health>
- 信源列表：<http://127.0.0.1:8000/api/sources>

在 API 文档页面执行：

```text
POST /api/runs
```

它会同步运行一次完整流水线，并返回报告路径、成功数、重复数和错误列表。

---

## 第 3 步：接入真实公开网页（Crawl4AI）

### 在中文控制台直接新建调研

打开 <http://127.0.0.1:8000/#research>，填写：

1. 行业，例如“储能”。
2. 1–8 家公司，例如“宁德时代、阳光电源”。
3. 可选的关注主题，例如“新品、产能、订单”。

系统会通过公开搜索结果发现公司官网新闻页，过滤搜索平台、社交平台、招聘站、百科、聚合站和
内网地址，检查页面可访问性后加入信源，只运行本次发现的信源，并生成独立 HTML 报告。完成后
页面会显示“在线浏览报告”和“下载 HTML”两个入口。

对应接口是 `POST /api/research`。搜索发现当前使用无需 Key 的公开搜索页，适合本地学习和低频
使用；搜索服务页面结构可能变化，生产部署建议替换成有正式服务协议的搜索 API。

n8n 仍然负责每天 08:00 定时执行所有已启用信源。自动发现过的官网会保留在信源列表，进入以后
的定时任务。

### 3.1 创建独立的采集环境

> 不要把采集器安装进基础 `.venv`。当前 Browser Use 要求 Pillow 11+，而
> PandasAI 3 要求 Pillow 11 以下，放进一个 Python 环境会产生依赖冲突。
> 本项目因此使用三个独立服务，这是正式部署中更稳定、也更安全的做法。

```powershell
py -3.11 -m venv .venv-collector
.\.venv-collector\Scripts\Activate.ps1
pip install -U pip
pip install -e ".[collectors]"
python -m playwright install --with-deps chromium
crawl4ai-doctor
uvicorn app.collector_service:app --host 127.0.0.1 --port 8011
```

这里有意安装标准 Playwright Chromium，而不把 Patchright 的“undetected/反检测”模式作为默认能力；本项目不用于绕过验证码或网站访问限制。`crawl4ai-doctor` 通过即表示标准采集环境可用。

另开一个 PowerShell，在基础 API 的 `.env` 中设置：

```dotenv
COLLECTOR_SERVICE_URL=http://127.0.0.1:8011
```

### 3.2 添加普通网页信源

在 <http://127.0.0.1:8000/api/docs> 使用 `POST /api/sources`：

```json
{
  "name": "某公司新闻中心",
  "url": "https://example.com/news",
  "kind": "static",
  "enabled": true,
  "tags": ["竞争对手", "产品动态"]
}
```

然后再次执行 `POST /api/runs`。

### 3.3 查看真实采集入口

文件：`app/collectors/crawl4ai_collector.py`

核心调用：

```python
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url=str(source.url), config=config)
```

这一层只负责得到网页正文；标准化、去重和报告不依赖 Crawl4AI 的内部格式。

---

## 第 4 步：接入必须交互的页面（Browser Use）

Browser Use 不是默认采集器，只用于：

- 必须点击“下一页”；
- 必须选择筛选条件；
- 内容只有登录后才能访问且你拥有合法账号；
- 页面结构不稳定，但人类可通过视觉和文本完成操作。

复制环境配置：

```powershell
Copy-Item .env.example .env
```

默认复用通用 `AI_*` 配置中的 DeepSeek，不需要额外 Key。若要改用 Browser Use 云模型，才在 `.env` 填写：

```dotenv
BROWSER_USE_API_KEY=你的Key
```

添加交互信源：

```json
{
  "name": "动态行业页面",
  "url": "https://example.com/dynamic-list",
  "kind": "interactive",
  "enabled": true,
  "tags": ["行业动态"],
  "extraction_hint": "点击下一页，提取最新页面的主标题、正文和发布时间"
}
```

安全限制在 `app/collectors/browser_use_collector.py`：

- 只允许目标域名；
- 最多 10 步；
- 禁止提交表单、购买和发布；
- 最终必须返回约定 JSON。

生产环境还应增加人工审批、Cookie 加密和浏览器执行日志。

---

## 第 5 步：理解 Pandas 和 PandasAI 的边界

`app/analysis.py` 有两个分析器：

### DeterministicAnalyzer

生产报告默认使用它：

- 信源数量；
- 每个信源的情报数；
- 每日数量；
- 高频主题；
- 可重复计算的摘要。

### PandasAIAnalyzer

用于临时问题，例如：

```text
本周哪些竞争对手同时提到了节能和预测性维护？
```

创建独立的 PandasAI 环境：

```powershell
py -3.11 -m venv .venv-ai
.\.venv-ai\Scripts\Activate.ps1
pip install -U pip
pip install -e ".[ai]"
uvicorn app.ai_service:app --host 127.0.0.1 --port 8012
```

在基础 API 的 `.env` 中设置：

```dotenv
ANALYSIS_SERVICE_URL=http://127.0.0.1:8012
AI_PROVIDER=deepseek
AI_API_KEY=你的DeepSeek_Key
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
```

修改 `.env` 后要重启 API/Collector/Analysis 进程，运行中的进程不会自动重新读取 Key。

随后可以调用 `POST /api/analysis/ask`。PandasAI会生成并执行代码，所以本项目把它
放在独立容器中，并设置只读文件系统、移除 Linux capabilities 和临时目录限额。
固定经营指标仍由确定性 Pandas 代码计算，不能只靠 LLM 生成。

---

## 第 6 步：接入 n8n 自动运行

项目已经提供：

```text
workflows/market-intelligence.json
```

工作流内容：

```text
每天08:00 / 手动测试
        ↓
POST http://api:8000/api/runs
        ↓
判断是否失败
   ├─ 成功摘要
   └─ 失败告警
```

导入后，可以在成功节点后增加：

- Gmail/Outlook 邮件；
- 企业微信机器人；
- 飞书消息；
- 保存到 Google Drive/OneDrive；
- 人工审批节点。

不要把 API Key 直接写进工作流 JSON，应使用 n8n Credentials。

---

## 第 7 步：Docker Compose 部署

当前电脑已经完成 Docker Desktop 与 WSL 2 安装。首次部署或需要自动检查时，运行：

```powershell
.\scripts\finish-docker-n8n.ps1
```

脚本会检查 Docker、启动五个服务、在空数据库中加入三个官方公开信源，并自动导入和发布 n8n 工作流。手动部署其他电脑时，先准备环境文件：

```powershell
Copy-Item .env.example .env
```

修改 `.env`：

```dotenv
POSTGRES_PASSWORD=换成强密码
N8N_ENCRYPTION_KEY=换成至少32位随机字符串
BROWSER_USE_API_KEY=可选
AI_API_KEY=可选
```

手动启动：

```powershell
docker compose up -d
```

打开：

- 中文控制台：<http://localhost:8000/>
- API 文档：<http://localhost:8000/api/docs>
- n8n：<http://localhost:5678>

系统首次部署默认加入施耐德电气中国官网、西门子中文新闻中心和 ABB 中国官网。
已有数据库会保留历史记录，可在中文控制台看到哪些旧信源已经停用。

> n8n 支持 `N8N_DEFAULT_LOCALE` 配置项，但官方 2.32.7 镜像没有内置简体中文翻译包，
> 强行设置后未翻译内容仍会回退为英文。本项目因此保持 n8n 官方界面稳定，并将工作流名称、
> 节点名称、通知文本以及本系统控制台全部设置为中文。

正常情况下启动脚本已经导入并发布工作流。仅在手动恢复备份时才需要从界面导入：

```text
n8n → Workflows → Import from File
选择 workflows/market-intelligence.json
```

Docker Compose 中包含：

- PostgreSQL：情报数据和 n8n 数据；
- API：业务接口、去重、存储、确定性 Pandas 分析和报告；
- Collector：Crawl4AI + Browser Use 浏览器采集；
- Analysis：隔离运行 PandasAI 探索性问数；
- n8n：定时编排；
- 持久化卷：数据库、报告、原始证据。

Compose 将 n8n 固定在 `2.32.7`，避免 `latest` 自动升级后工作流格式突然变化；升级时应先备份并重新执行验收。

当前本机实测版本与结果见 `docs/验收记录.md`；逐步操作教程见 `docs/Docker-n8n-完整操作步骤.md`。

服务关系：

```text
n8n → API → PostgreSQL
        ├→ Collector (Crawl4AI / Browser Use)
        └→ Analysis  (PandasAI，可选)
```

---

## 第 8 步：部署到云服务器

最低建议：4 核 8 GB；同时运行多个 Chromium 时建议 8 核 16 GB。

服务器还要增加：

1. Caddy 或 Nginx 反向代理。
2. HTTPS 证书。
3. 防火墙只开放 80/443。
4. 不直接向公网开放 PostgreSQL。
5. n8n 登录认证。
6. 数据库每日备份。
7. 报告和原始证据对象存储。
8. CPU、内存、磁盘和失败率告警。

---

## 数据库里有什么

| 表 | 内容 |
|---|---|
| `sources` | 信源地址、类型、标签和是否启用 |
| `intel_items` | 标准化正文、摘要、证据、指纹和原始链接 |
| `runs` | 每次任务的时间、状态、错误和报告路径 |

关键唯一约束：

```text
canonical_url + content_hash
```

同一URL内容发生变化时会生成新版本；同一版本反复抓取不会重复入库。

---

## 测试与验收

运行：

```powershell
pytest -q
ruff check app tests
```

当前测试覆盖：

- 去除追踪参数并规范化 URL；
- 内容指纹稳定性；
- 文本空白清洗；
- 4 条样例去重为 3 条；
- 重复运行不重复入库；
- HTML 报告成功生成。

真实上线前再补：

- 每个目标网站的黄金样本；
- CSS/页面改版回归测试；
- 网络超时和重试测试；
- 数据质量门槛；
- Browser Use 危险操作审批；
- 报告数字复算测试。

## 合规边界

只采集允许自动访问的页面。遵守 robots.txt、网站服务条款、版权和个人信息保护要求；不要绕过验证码、访问控制或付费墙。

公开部署前请阅读 [`PRIVACY_AND_COMPLIANCE.md`](PRIVACY_AND_COMPLIANCE.md) 和
[`SECURITY.md`](SECURITY.md)。生成内容仅供研究参考，重要结论必须回到原始来源核验。

## License

本仓库的原创应用代码采用 [MIT License](LICENSE)。第三方组件、容器镜像、模型 API
及其传递依赖不因本仓库的 MIT License 而改变，完整说明见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
