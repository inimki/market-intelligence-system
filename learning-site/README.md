# 市场情报源码学习站（独立静态发行版）

本目录包含学习页面、样式、图片和完整构建源码，随主仓库一起下载。
页面介绍 Crawl4AI、Browser Use、n8n、PandasAI 和 Python 的分工与练习。
练习中的示例结果与验收目标不代表主系统已经达到相应指标。

## 随系统部署

在仓库根目录运行 `一键部署.cmd`。Docker 自动安装依赖并导出静态页面，
通过同一个 Nginx 提供 `/learn/`，无需本机安装 Node 或登录任何托管账号。

## 单独开发或构建

需要 Node.js 22.13 或以上版本，在本目录执行：

```bash
npm ci
npm run lint
npm run build:static
npm audit
```

输出为 `out/`，必须部署到 Web 根目录下的 `learn/`，而不是 `/`。
开发时运行 `npm run dev`，按终端显示的本机地址访问 `/learn/`。
没有 `next start` 服务端部署步骤；生产运行时是 Nginx 静态文件服务。
详情见[部署说明](../docs/学习站静态部署.md)。

## 发布边界

原创页面继承仓库根目录的 [MIT License](../LICENSE)。
第三方组件仍适用各自许可证，见[第三方声明](../THIRD_PARTY_NOTICES.md)。
此发行版从原学习站保留内容与样式，不包含其 `.git`、`.env`、
`.openai/hosting.json`、Sites/Vinext/Cloudflare 发布工具、缓存或个人账号标识。
原独立学习站目录不会自动同步；今后 GitHub 版本以本目录为准。
只允许非敏感 `LEARNING_SITE_ORIGIN` 构建参数；不要把任何密钥放入前端或 `public/`。
