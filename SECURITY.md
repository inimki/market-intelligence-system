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
