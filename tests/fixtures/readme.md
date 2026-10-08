<p align="center"><img src="logo.png" width="120"></p>

# Project

[![CI](https://img.shields.io/badge/ci-passing-green)](https://ci.example) ![stars](https://img.shields.io/github/stars/x/y)

A small, self-hosted tool you can run on one machine. It replaces a paid service with about 300 lines of code and a SQLite file. See the [docs](https://example.com/docs) for setup.

## Install

```bash
go install example.com/tool@latest
```

## Why

Most teams pay for this every month even though the core job is tiny: read a schedule, run a command, keep a history, and show it in a browser. This project does exactly that and nothing else, so one person can understand, fork and maintain all of it in an afternoon. It is deliberately boring: no queue, no cluster, no plugin system, just a single binary and a database file that you can back up by copying it somewhere safe.

## Roadmap

Email alerts, a dark theme, and import from existing crontabs are next on the list for the coming weeks.
