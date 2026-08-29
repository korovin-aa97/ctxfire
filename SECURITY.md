# Security policy

## Supported versions

Security fixes are provided for the latest released minor version.

## Reporting a vulnerability

Please use GitHub's private **Report a vulnerability** flow in the Security tab
instead of filing a public issue. Include the affected version, operating
system, minimal reproduction, and impact.

If private reporting is unavailable, contact the repository owner through the
email address shown on the GitHub profile and avoid including secrets in the
first message. You should receive an acknowledgment within 72 hours.

## Threat model

`ctxfire` scans an untrusted local repository. It never executes repository
files or configuration commands. It invokes only the local `git` executable
with a fixed argument list, does not use a shell, and does not follow symlinks.
The default estimator reads metadata only. The explicitly enabled tokenizer
reads matched bytes locally in memory but does not print, retain, or upload
their content.

Treat third-party repositories as untrusted anyway: run in a normal
least-privilege account and inspect dependency changes before upgrading.
