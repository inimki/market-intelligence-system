# Security policy

## Supported version

Security fixes are applied to the latest commit on the default branch.

## Reporting a vulnerability

Do not publish credentials, exploit details, or personal information in a
public issue. Use GitHub's private vulnerability reporting/security advisory
feature when available, or contact the repository owner through the GitHub
profile.

## Deployment warning

The default Docker Compose setup is intended for local self-hosting. Do not
expose PostgreSQL, the collector service, the analysis service, or the n8n
editor directly to the public internet. See `PRIVACY_AND_COMPLIANCE.md` before
deploying a public service.

## Public source and learning site

The bundled `learning-site/` is a static export served by Nginx, not a Next.js
production server. Never store credentials in frontend source, public assets,
build arguments, reports, screenshots, or issue attachments. The only learning
build parameter is a non-sensitive HTTP(S) origin.

Before publishing, run `python scripts/check-publication.py`, a redacted
Gitleaks scan of Git history, and `npm audit` inside `learning-site/`.
CI repeats these checks and a static build. Audit results are time-dependent;
passing them is not a guarantee that the entire platform is vulnerability-free.
Private `.env`, runtime data and the original personal hosting directory are
not part of the release. Never force-add ignored files or post expanded
`docker compose config` output containing credentials.
