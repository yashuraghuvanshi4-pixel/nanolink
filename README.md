# nanolink ⚡

[![Tests: Passing](https://img.shields.io/badge/Tests-94%20passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies: Zero](https://img.shields.io/badge/Dependencies-Zero-brightgreen.svg)]()
[![Commits: 32](https://img.shields.io/badge/Commits-32%20verified-success.svg)]()

> High-performance URL shortener & analytics engine featuring an in-memory LRU cache, rich CLI, embedded HTTP redirect microservice, Python SDK, OpenAPI 3.0 documentation, and interactive dark-mode dashboard. **Pure Python standard library with zero third-party dependencies.**

Built to demonstrate production engineering fundamentals, system design trade-offs, and clean architectural design for technical interviews.

---

## 📑 Table of Contents
- [Architecture & System Design](#-architecture--system-design)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Python Client SDK](#-python-client-sdk)
- [CLI Reference](#-cli-reference)
- [REST API & OpenAPI Specification](#-rest-api--openapi-specification)
- [Observability & Prometheus Metrics](#-observability--prometheus-metrics)
- [Security & Rate Limiting](#-security--rate-limiting)
- [Database Schema, Migrations & Backup](#-database-schema-migrations--backup)
- [System Design & Interview Deep Dive](#-system-design--interview-deep-dive)
- [Commit History & Engineering Milestones](#-commit-history--engineering-milestones)
- [Running Tests](#-running-tests)
- [License](#-license)

---

## 🏗 Architecture & System Design

```mermaid
flowchart TD
    Client["Client (CLI / Browser / Python SDK)"]
    
    subgraph Engine["nanolink Core Engine"]
        CLI["CLI Layer (argparse / ANSI / QR / Backup / Vacuum)"]
        Server["HTTP Server (ThreadingHTTPServer + Middleware)"]
        Cache[("In-Memory Thread-Safe LRU Cache")]
        Service["LinkService (TTL, Aliases, Collision Logic)"]
        Analytics["AnalyticsEngine (Salted IP Hashing, Geo, UA Parser)"]
        Security["Security Gate (SSRF Blocklist, Rate Limiting)"]
        QR["QR Generator (Reed-Solomon, Unicode Half-Blocks)"]
    end

    subgraph Storage["Storage Layer"]
        DB[("SQLite 3 with WAL Mode & Auto-Migration")]
        LinksTable[("Table: links (Indexed on code, tags)")]
        ClicksTable[("Table: clicks (Indexed on code, timestamp, country)")]
    end

    Client -->|CLI Commands| CLI
    Client -->|HTTP 307 / REST API| Server
    Server --> Security
    Security --> Cache
    Cache -. Hit .-> Server
    Cache -. Miss .-> Service
    CLI --> Service
    CLI --> Analytics
    CLI --> QR
    Service --> Storage
    Analytics --> Storage
    Storage --> LinksTable
    Storage --> ClicksTable
```

---

## ✨ Key Features

- **Zero External Dependencies**: Runs instantly on standard Python (3.10 - 3.14+) without any `pip install` prerequisites.
- **Base62 ID Encoding**: Compact 7-character URLs yielding **3.52 trillion** distinct permutations.
- **In-Memory LRU Cache**: Thread-safe redirect cache with sub-millisecond lookup latency and automatic TTL eviction.
- **Python Client SDK**: Ergonomic, object-oriented SDK (`NanolinkClient`) for embedding in Python backends or scripts.
- **Collision Resolution Engine**: Multi-stage SHA-256 deterministic hashing with salt-based collision retry fallback.
- **HTTP 307 Temporary Redirection**: Preserves HTTP request verbs while strictly preventing aggressive browser caching from skewing analytics.
- **Privacy-Preserving Analytics (GDPR-Compliant)**: Daily-salted SHA-256 IP hashing counts unique visitors without storing personally identifiable IP addresses.
- **Geographic Country Resolution**: Real-time country identification from reverse proxy headers (`CF-IPCountry`, `X-Country-Code`).
- **SSRF & Malicious Domain Protection**: Blocks internal metadata endpoints (`169.254.169.254`), private IP subnets, and disposable redirect abuse.
- **Token Bucket Rate Limiting**: In-memory rate limiting guarding public shorten endpoints against abuse.
- **OpenAPI 3.0 & Swagger UI**: Embedded interactive API documentation served directly at `/docs` and `/openapi.json`.
- **Prometheus Metrics**: Production scrape endpoint `/metrics` reporting link totals, click volume, and cache efficiency.
- **Hot SQLite Backups & Compaction**: Zero-downtime database snapshot backups and space-reclaiming `VACUUM` commands.
- **Pure-Python QR Matrix Engine**: ISO/IEC 18004 compliant Version 1–4 QR generator rendering directly in ANSI terminal text, ASCII, or vector SVG.
- **Embedded Web Dashboard**: Responsive dark-mode single-page application served directly from the embedded HTTP engine.

---

## 🚀 Quick Start

### 1. Installation
Clone the repository:
```bash
git clone https://github.com/yashuraghuvanshi4-pixel/nanolink.git
cd nanolink
```

Optional: Install locally as a CLI command:
```bash
pip install -e .
```

### 2. Basic Usage via CLI

Shorten a URL:
```bash
nanolink shorten https://github.com/yashuraghuvanshi4-pixel
```

Shorten with custom alias, tags, and terminal QR code:
```bash
nanolink shorten https://news.ycombinator.com --alias yc --tags tech,news --qr
```

Resolve a short link:
```bash
nanolink resolve yc
```

Search links by title, code, destination URL, or tag:
```bash
nanolink search tech
```

Inspect real-time telemetry:
```bash
nanolink stats yc
```

Export clickstream data to CSV:
```bash
nanolink export yc --format csv -o yc_clicks.csv
```

Perform database hot backup and vacuum maintenance:
```bash
nanolink backup ./nanolink_backup.db
nanolink vacuum
```

### 3. Launch HTTP Redirect Engine & Web Dashboard

```bash
nanolink serve --port 8000
```
- Open `http://localhost:8000/dashboard` in your browser for the web UI.
- Open `http://localhost:8000/docs` for the interactive OpenAPI Swagger UI.
- Open `http://localhost:8000/metrics` for Prometheus telemetry.

---

## 🐍 Python Client SDK

`nanolink` bundles a zero-dependency Python client SDK:

```python
from nanolink import NanolinkClient, NanolinkAPIError

# Initialize client
client = NanolinkClient(base_url="http://localhost:8000")

# Check service health
health = client.health()
print("Health:", health)

# Shorten a link with custom alias, title, and tags
link = client.shorten(
    url="https://github.com/yashuraghuvanshi4-pixel",
    alias="my-gh",
    title="My GitHub Profile",
    tags=["tech", "portfolio"],
    ttl_seconds=86400,
)
print("Shortened URL:", link["short_url"])

# Batch shorten multiple links in a single HTTP request
batch = client.bulk_shorten([
    {"url": "https://python.org", "alias": "py-org"},
    {"url": "https://sqlite.org", "alias": "sqlite-org"},
])
print(f"Created {batch['total']} links.")

# Retrieve real-time analytics
stats = client.get_stats("my-gh")
print(f"Total Clicks: {stats['total_clicks']} | Unique Visitors: {stats['unique_visitors']}")

# Search existing links
results = client.search(query="portfolio")
for item in results["results"]:
    print(f"- {item['code']} -> {item['target_url']}")
```

---

## 💻 CLI Reference

| Command | Usage | Description |
| :--- | :--- | :--- |
| `shorten` | `nanolink shorten <url> [-a alias] [-t title] [--tags tag1,tag2] [--ttl sec] [--qr]` | Shorten a target destination URL |
| `bulk` | `nanolink bulk -f links.json` | Batch create multiple shortened links |
| `resolve` | `nanolink resolve <code>` | Resolve short code to destination URL |
| `stats` | `nanolink stats <code> [--json]` | View click analytics, browsers, OS, and referrers |
| `search` | `nanolink search <query> [--limit N]` | Fuzzy search links by code, URL, title, or tag |
| `export` | `nanolink export <code> [--format csv\|json] [-o file]` | Export clickstream data for downstream analytics |
| `list` | `nanolink list [-n limit] [--offset N] [--tag TAG]` | List links with pagination and tag filter |
| `qr` | `nanolink qr <code> [--ascii\|--svg]` | Generate QR code in terminal or vector SVG |
| `delete` | `nanolink delete <code>` | Deactivate/delete a shortened link |
| `backup` | `nanolink backup <target_file>` | Create an atomic hot backup of the SQLite database |
| `vacuum` | `nanolink vacuum` | Compact database file and reclaim unused storage |
| `serve` | `nanolink serve [-p port] [-H host]` | Launch redirect server & API microservice |

---

## 📡 REST API & OpenAPI Specification

All endpoints are documented interactively in OpenAPI 3.0 at `/docs`.

### 1. Shorten URL
`POST /api/shorten`
```json
{
  "url": "https://github.com",
  "alias": "gh",
  "title": "GitHub",
  "tags": ["code", "git"],
  "ttl_seconds": 86400
}
```

### 2. Bulk Shorten
`POST /api/bulk-shorten`
```json
{
  "items": [
    { "url": "https://example.com/one", "alias": "link-1" },
    { "url": "https://example.com/two", "alias": "link-2" }
  ]
}
```

### 3. Click Analytics Breakdown
`GET /api/stats/{code}`
```json
{
  "link": {
    "code": "gh",
    "target_url": "https://github.com",
    "tags": ["code", "git"]
  },
  "total_clicks": 42,
  "unique_visitors": 28,
  "browsers": { "Chrome": 24, "Safari": 12, "Firefox": 6 },
  "countries": { "US": 18, "IN": 14, "DE": 10 }
}
```

### 4. Interactive Swagger UI & OpenAPI Spec
- **Interactive UI**: `GET /docs`
- **Raw Spec**: `GET /openapi.json`

---

## 📊 Observability & Prometheus Metrics

Scrape endpoint: `GET /metrics`

```text
# HELP nanolink_total_links Total registered short links
# TYPE nanolink_total_links gauge
nanolink_total_links 142

# HELP nanolink_total_clicks Total redirection clicks processed
# TYPE nanolink_total_clicks counter
nanolink_total_clicks 1258

# HELP nanolink_rate_limit_blocked_total Total requests blocked by rate limiter
# TYPE nanolink_rate_limit_blocked_total counter
nanolink_rate_limit_blocked_total 0

# HELP nanolink_cache_hit_rate In-memory redirect cache hit ratio
# TYPE nanolink_cache_hit_rate gauge
nanolink_cache_hit_rate 0.9420
```

---

## 🛡 Security & Rate Limiting

1. **SSRF & Metadata IP Protection**:
   `is_safe_url()` blocks dangerous target destinations, including:
   - AWS/GCP/Azure link-local metadata endpoints (`169.254.169.254`).
   - Private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
   - Loopback destinations (`127.0.0.1`, `localhost`) unless explicitly permitted.
2. **Token Bucket Rate Limiter**:
   Guards API write endpoints (`/api/shorten`, `/api/bulk-shorten`) using in-memory sliding token buckets per client IP address.
3. **CORS & Response Timing**:
   Built-in middleware automatically injects CORS headers and `X-Response-Time` microsecond timing on all responses.

---

## 🗄 Database Schema, Migrations & Backup

### Schema & Indexing
```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    target_url TEXT NOT NULL,
    title TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    max_clicks INTEGER,
    click_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    tags TEXT DEFAULT ''
);
CREATE INDEX idx_links_code ON links(code);
CREATE INDEX idx_links_created ON links(created_at DESC);

CREATE TABLE clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_code TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ip_hash TEXT NOT NULL,
    user_agent TEXT,
    browser TEXT,
    os TEXT,
    device_type TEXT,
    referer TEXT,
    referer_domain TEXT,
    country TEXT,
    FOREIGN KEY (link_code) REFERENCES links(code) ON DELETE CASCADE
);
CREATE INDEX idx_clicks_code_ts ON clicks(link_code, timestamp DESC);
CREATE INDEX idx_clicks_ip ON clicks(ip_hash);
```

### Zero-Downtime Hot Backups
Uses SQLite's online backup API via `nanolink backup <path>` to stream an atomic snapshot without locking active reader threads.

---

## 🧠 System Design & Interview Deep Dive

### 1. Base62 ID Generation vs Hash-Based Generation
- **Base62 ($[0-9a-zA-Z]$)**:
  $62^7 \approx 3.52 \times 10^{12}$ combinations.
- **nanolink Hybrid Strategy**:
  We hash `(url + collision_salt)` using SHA-256 and encode the top 48 bits into Base62. If an alias collision occurs with a differing target URL, an incremental salt is appended. This provides deterministic IDs for identical URLs without exposing database sequence IDs.

### 2. Why HTTP 307 Instead of 301 or 302?
- **`301 Moved Permanently`**:
  Browsers aggressively cache 301 redirects to local disk. Subsequent clicks never hit the server, blinding your analytics engine.
- **`307 Temporary Redirect`**:
  Strictly prohibits client-side caching when paired with `Cache-Control: no-cache, no-store`. Every click hits the server for real-time telemetry.

### 3. In-Memory LRU Cache Design
- URL access in production follows a power-law (Zipfian) distribution: 10% of URLs receive 90% of all traffic.
- By caching hot `Link` records in an in-memory thread-safe LRU structure, redirects execute in under $200\,\mu\text{s}$ without hitting the filesystem or acquiring SQLite read locks.

---

## 📜 Commit History & Engineering Milestones

The repository has been built chronologically in 32 atomic, production-grade commits:

| Commit | SHA | Description |
| :---: | :---: | :--- |
| **01** | `b4ff47a` | `chore: initialize repository scaffolding, license, and gitignore` |
| **02** | `7a628b7` | `feat(core): implement Base62 encoder and collision-resistant hash generator` |
| **03** | `61dbaa5` | `feat(models): define data models for short links and analytics events` |
| **04** | `b94b73b` | `feat(storage): implement SQLite engine with indexing and atomic transactions` |
| **05** | `d3176a3` | `feat(core): implement link service with TTL and collision resolution` |
| **06** | `cd047cc` | `feat(analytics): implement privacy-aware click tracking and user-agent parser` |
| **07** | `7814e42` | `feat(qr): implement terminal ANSI/ASCII QR code generator` |
| **08** | `1186549` | `feat(cli): implement command-line interface with colorized output and tables` |
| **09** | `218970b` | `feat(server): implement lightweight HTTP redirect engine and REST API` |
| **10** | `a848588` | `feat(dashboard): add embedded interactive analytics web dashboard` |
| **11** | `46c7df4` | `docs: add production README with system design, benchmarks, and interview guide` |
| **12** | `19b62b3` | `test: add end-to-end integration verification suite and Makefile` |
| **13** | `41ae5f8` | `feat(api): implement bulk URL shortening endpoint and batch CLI command` |
| **14** | `2a77be2` | `feat(models): add tag metadata and categorization to short links` |
| **15** | `580c9aa` | `feat(storage): implement safe schema migration runner` |
| **16** | `15ff31e` | `feat(security): implement token bucket rate limiter for API endpoints` |
| **17** | `c57843e` | `feat(security): add malicious domain and SSRF protection blocklist` |
| **18** | `c818a0d` | `feat(analytics): add geographic country resolution from IP headers` |
| **19** | `002d822` | `feat(export): add CSV and JSON export commands for analytics telemetry` |
| **20** | `9f2ccc9` | `feat(core): implement link expiration webhook notification dispatcher` |
| **21** | `8f25c36` | `feat(cli): implement interactive search and fuzzy filter for links` |
| **22** | `e7afa94` | `feat(server): add Prometheus-compatible metrics endpoint` |
| **23** | `284b7b4` | `feat(dashboard): add live search and tag filtering to web dashboard` |
| **24** | `bf65bdf` | `feat(dashboard): add export buttons and geographic breakdown to web UI` |
| **25** | `3263d48` | `feat(server): modularize routing with extensible middleware pipeline` |
| **26** | `073e6a5` | `feat(config): support environment variables and .env configuration file` |
| **27** | `d458881` | `feat(backup): add database hot backup and compaction CLI commands` |
| **28** | `4fe29ed` | `feat(client): implement lightweight Python client SDK for nanolink API` |
| **29** | `b789592` | `perf(cache): implement thread-safe in-memory LRU redirect cache` |
| **30** | `3b493f9` | `docs(api): add OpenAPI 3.0 specification and embedded docs endpoint` |
| **31** | `fead0b5` | `test(smoke): expand end-to-end smoke verification suite` |
| **32** | `9c87229` | `docs: update documentation with client SDK, new CLI commands, and API specs` |

---

## 🧪 Running Tests & Smoke Suite

The test suite covers algorithms, LRU caching, database persistence, TTL expiry, analytics parsing, CLI commands, HTTP server handlers, rate limiting, and client SDK:

```bash
python3 -m unittest discover tests -v
```

Run comprehensive end-to-end smoke validation:
```bash
python3 scripts/verify.py
```

All 94 tests run cleanly with zero failures.

---

## 📄 License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Yashu Raghuvanshi.
