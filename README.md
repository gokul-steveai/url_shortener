# ⚡ BoltLink — Production-Grade URL Shortener

A high-performance URL shortening service built with **FastAPI**, **PostgreSQL**, **Redis**, and a **Streamlit** analytics dashboard. Features AI-powered page summarization via Groq (LLaMA 3.3 70B), a multi-layer caching strategy, structured JSON logging, and real-time engagement tracking.

---

## Features

- **URL Shortening** — Base-62 encoding derived from the database primary key, guaranteeing uniqueness without collision checks
- **AI Summaries** — Groq LLaMA 3.3 70B scrapes and summarizes the destination page asynchronously in the background; served on-demand if not yet ready
- **Multi-layer Cache** — Redis-backed versioned pagination cache with MGET hydration, stampede protection via distributed lock, and 24h redirect cache
- **Click Tracking** — Atomic `UPDATE ... RETURNING` increments clicks on every redirect; cache invalidated immediately
- **Live Analytics Dashboard** — Streamlit UI with glassmorphism design, auto-refreshes every 10 seconds via JS interval
- **Structured Logging** — JSON log lines in production (Datadog/CloudWatch/Loki-ready), colored dev formatter, per-request `request_id` context propagation
- **Schema Migrations** — Alembic with versioned migration history

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.136 + Uvicorn |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) |
| Cache | Redis 7 (asyncio client) |
| AI | Groq API — LLaMA 3.3 70B Versatile |
| Scraping | httpx + BeautifulSoup4 |
| Dashboard | Streamlit + streamlit-autorefresh |
| Migrations | Alembic |
| Serialization | orjson |
| Config | pydantic-settings |
| Package Manager | uv |

---

## Project Structure

```
url-shortener/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   └── endpoints.py      # All route handlers
│   │   └── deps.py               # DB session & Redis dependency injection
│   ├── core/
│   │   ├── config.py             # Pydantic settings (reads from .env)
│   │   └── logging.py            # JSON + dev formatters, request-id context
│   ├── crud/
│   │   └── url.py                # DB operations with cache integration
│   ├── models/
│   │   └── url.py                # SQLAlchemy URL model
│   ├── schemas/
│   │   └── url.py                # Pydantic request/response schemas
│   ├── services/
│   │   ├── redis_service.py      # Versioned cache, stampede protection
│   │   ├── shortener.py          # Base-62 encode/decode
│   │   └── summarizer.py         # Scrape + Groq LLM summarization
│   ├── utils/
│   │   └── pagination.py         # Paginated response builder
│   └── main.py                   # App factory, middleware, startup
├── alembic/
│   └── versions/                 # Migration history
├── streamlit_app/
│   └── app_ui.py                 # Analytics dashboard
├── pyproject.toml
└── .env                          # Environment variables (not committed)
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/shorten` | Create a short URL |
| `GET` | `/{short_id}` | Redirect to original URL + increment click |
| `GET` | `/links` | Paginated list of all links |
| `GET` | `/links/{short_id}/summary` | Get AI summary for a link |
| `DELETE` | `/links/{id}` | Delete a link |
| `GET` | `/stats` | Aggregate total links + total clicks |
| `GET` | `/health` | Health check for load balancers |

### POST `/shorten`

```json
// Request
{
  "target_url": "https://example.com/very/long/url"
}

// Response
{
  "target_url": "https://example.com/very/long/url",
  "short_url": "http://localhost:8000/aB3x",
  "summary": "Example Domain is a placeholder domain used for illustrative examples in documents.",
  "expires_at": null
}
```

### GET `/links?page=1&limit=20`

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "limit": 20,
  "pages": 3,
  "has_next": true,
  "has_prev": false
}
```

---

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL
- Redis
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Clone & install dependencies

```bash
git clone https://github.com/your-username/url-shortener.git
cd url-shortener
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
API_URL=http://localhost:8000

# Optional — enables AI summaries
GROQ_API_KEY=your_groq_api_key_here

# Logging: use "json" in production, "dev" locally
LOG_LEVEL=INFO
LOG_FORMAT=dev
```

Get a free Groq API key at [console.groq.com](https://console.groq.com). Without it, the service falls back to meta description / text snippet summaries.

### 3. Run database migrations

```bash
uv run alembic upgrade head
```

### 4. Start the API

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 5. Start the dashboard

```bash
uv run streamlit run streamlit_app/app_ui.py
```

The dashboard will be available at `http://localhost:8501`.

---

## Caching Architecture

```
Request → Redis (redirect cache, 24h TTL)
              ↓ miss
         Redis (versioned paginated index + MGET object hydration)
              ↓ miss
         PostgreSQL (async connection pool, size=20)
              ↓
         Write-through to Redis
```

- **Versioned pagination** — a `links:version` counter in Redis is incremented on every write (create, delete, click). All paginated cache keys embed the version, so stale pages are never served — no explicit key scanning needed
- **Stampede protection** — a distributed `nx` lock prevents multiple concurrent requests from all hitting the DB simultaneously on a cold cache
- **MGET hydration** — paginated index stores only IDs; objects are fetched in a single `MGET` pipeline call

---

## Logging

Two modes controlled by `LOG_FORMAT` in `.env`:

**Development** (`LOG_FORMAT=dev`) — colored, human-readable:
```
12:34:56 INFO     [abc123] app.crud.url url.created id=7 short_id=aB3x
12:34:56 INFO     [abc123] app.services.redis_service cache.version_bump new_version=4
```

**Production** (`LOG_FORMAT=json`) — one JSON object per line:
```json
{"ts":"2024-01-15T12:34:56.123456","level":"INFO","logger":"app.crud.url","request_id":"abc123","msg":"url.created id=7 short_id=aB3x"}
```

Every log line carries a `request_id` (UUID) injected by the HTTP middleware, allowing full request tracing across all layers — API → CRUD → Redis → Summarizer.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | ❌ | `redis://localhost:6379/0` | Redis connection string |
| `API_URL` | ❌ | `http://localhost:8000` | Public base URL for generating short links |
| `GROQ_API_KEY` | ❌ | `None` | Enables AI summarization via Groq |
| `LOG_LEVEL` | ❌ | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_FORMAT` | ❌ | `dev` | `dev` for colored console, `json` for production |
