# Privacy and compliance

This document describes the intended safe use of the self-hosted market
intelligence platform. It is operational guidance, not legal advice.

## Intended use

The platform is designed to collect low-frequency market intelligence from
public company websites and other pages that can be viewed without logging in.
It must not be used to bypass authentication, CAPTCHAs, paywalls, access
controls, rate limits, or technical restrictions.

Operators must review and comply with applicable laws, website terms of
service, robots.txt directives, copyright rules, database rights, and personal
information requirements before adding a source.

## Data processed

Depending on the configured sources, the system may store:

- source names, URLs, tags, and extraction hints;
- public page titles, text, publication times, links, and evidence excerpts;
- collection timestamps, hashes, errors, and run statistics;
- generated HTML reports and raw evidence snapshots;
- user-supplied industry, company, keyword, and analysis questions.

Do not configure sources that contain sensitive personal information,
confidential information, credentials, or data that you are not authorized to
process. Review generated reports before sharing them.

## Storage and retention

The default deployment stores PostgreSQL data, reports, raw evidence, and n8n
state in local Docker volumes. The repository excludes `.env`, databases, raw
evidence, generated reports, and logs. Operators should define their own
retention period, delete data that is no longer needed, encrypt backups, and
restrict filesystem and database access.

## External services

- Search discovery currently reads public search-result pages at low frequency.
  It is experimental and may stop working when the provider changes its page.
  Public or commercial deployments should use a search API with an appropriate
  service agreement.
- Crawl4AI and Browser Use may request configured public websites.
- PandasAI or Browser Use may send selected text to the configured model API.
  Review the model provider's privacy and data-retention terms before enabling
  these features.
- n8n stores workflow configuration and credentials in its own database. Never
  expose the n8n editor directly to the public internet.

## Secrets

Real credentials belong only in the local `.env` file or a production secret
manager. Never commit API keys, database passwords, encryption keys, browser
profiles, cookies, session tokens, or generated credential files. The
`.env.example` file must contain placeholders only.

If a secret is committed, removing the file in a later commit is not enough.
Revoke and rotate the secret immediately, then remove it from Git history.

## Public deployment

Before exposing this platform to other users, add authentication,
authorization, request quotas, job concurrency limits, complete DNS/IP-based
SSRF protection, outbound network controls, audit logs, HTTPS, backups, and
monitoring. Keep PostgreSQL, collector, analysis, and n8n management ports off
the public internet.

## Content and decisions

Collected pages may be inaccurate, outdated, incomplete, or copyrighted.
Generated summaries are not investment, legal, or business advice. Keep source
links, cite original publishers, minimize copied content, and verify important
claims manually before making decisions or redistributing a report.

## Reporting concerns

For security issues, open a private GitHub security advisory after the
repository is published. For privacy or content-removal concerns, contact the
repository owner through the GitHub profile without posting sensitive data in
a public issue.
