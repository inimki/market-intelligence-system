# Third-party notices

This repository's original application code is licensed under the MIT License.
The project integrates, but does not relicense, the following independently
licensed components. Users remain responsible for complying with each upstream
license and service agreement.

## Crawl4AI

- Project: https://github.com/unclecode/crawl4ai
- License: Apache License 2.0 with the attribution requirement in its LICENSE

Required attribution:

> This product includes software developed by UncleCode
> (https://x.com/unclecode) as part of the Crawl4AI project
> (https://github.com/unclecode/crawl4ai).

## Browser Use

- Project: https://github.com/browser-use/browser-use
- License: MIT License
- Copyright: Gregor Zunic and contributors

## PandasAI

- Project: https://github.com/sinaptik-ai/pandas-ai
- License: MIT Expat License for the community code
- Exception: content under `pandasai/ee/` uses a separate enterprise license and
  is not included in this repository.

## n8n

- Project: https://github.com/n8n-io/n8n
- License: Sustainable Use License, with separate terms for enterprise files
- Note: n8n is source-available/fair-code rather than OSI-approved open source.
  Its license limits some commercial distribution and hosted-service uses. This
  repository references the official n8n container and does not relicense n8n.

## Nginx

- Project: https://nginx.org/
- License: 2-clause BSD-style license; see https://nginx.org/LICENSE
- This repository references the official Nginx container and includes its own proxy configuration.

## Additional dependencies

Python packages, container images, PostgreSQL, Playwright/Chromium, DeepSeek or
other model APIs, and their transitive dependencies remain under their own
licenses and terms. See `pyproject.toml` and `docker-compose.yml` for the
dependency inventory and pinned service versions.
