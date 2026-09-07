# Security Policy

## Secrets

Do not commit API keys, access tokens, cookies, provider credentials, or private
endpoints. Model credentials must be injected through environment variables at
runtime. The repository intentionally excludes `.env` files and common private
key formats.

Challenge artifacts, recovery probes, and ledgers must not contain credentials.
Before publishing a new artifact, scan both tracked files and Git history.

## Reporting a vulnerability

Please report security issues privately through GitHub's private vulnerability
reporting feature when it is available. Do not open a public issue containing a
working exploit, credential, or personally identifying data.

## Scope

This is a research benchmark and portfolio project, not a production service.
Its failure-handling and security checks are engineering evidence, not a
production security certification.
