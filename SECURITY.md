# Security policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through
[GitHub's private vulnerability reporting](https://github.com/padovanl/bitloom/security/advisories/new).

Include:
- the affected version;
- how to reproduce the problem;
- what an attacker can achieve.

You will get an answer within a week. Once a fix is released, you will be credited in its advisory unless you ask otherwise.

## What is in scope

- **The web dashboard and build service:** authentication tokens, the HTTP API, file access outside the project.
- **Commands Bitloom runs:** command injection through profile fields, recipe names or file paths.
- **Release artifacts:** the `.deb`, the wheel and `bitloom.pyz`.

The dashboard listens on localhost by default. Exposing it on a network is your choice; put it behind TLS and a reverse proxy when you do.
