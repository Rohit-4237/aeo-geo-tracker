# AEO / GEO Brand Tracker

A locally-hosted tool that monitors your brand's presence across AI search platforms — ChatGPT, Gemini, Perplexity, Google AI Overviews, and Google AI Mode. Track mentions, citations, and sentiment for your brand versus up to 4 competitors.

---

## Features

- **Multi-platform tracking** — ChatGPT (GPT-4o), Gemini (2.0 Flash Lite), Perplexity, Google AI Overviews, Google AI Mode
- **Brand comparison** — 1 primary brand + up to 4 competitors
- **Prompt management** — upload prompts via CSV, organised by category
- **Analytics dashboard**
  - Total mentions and citations per brand
  - Per-prompt breakdown, filterable by platform
  - Cited pages list per brand per prompt
  - Sentiment analysis (positive / negative / neutral counts + net score)
- **Dual API mode**
  - **BYOK** — users enter their own API keys via the Settings page
  - **Platform** — operator pre-fills keys in `.env` (keys never exposed to users)
- **No Node.js required** — pure HTML + Alpine.js + Chart.js frontend
- **Fully local / self-hosted** — SQLite database, no external dependencies at runtime

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), SQLite |
| Frontend | HTML, Alpine.js, Chart.js, Tailwind CSS (CDN) |
| Sentiment | VADER (offline, no API needed) |
| Google scraping | Playwright (headless Chromium) |
| HTTP client | httpx (async) |

---

## Quick Start (Windows)

### 1. Prerequisites

- [Python 3.11+](https://www.python.org/downloads/) installed and on PATH
- Internet access for first-time dependency install

### 2. Clone the repo

```bat
git clone https://github.com/Rohit-4237/aeo-geo-tracker.git
cd aeo-geo-tracker
```

### 3. Configure environment (optional)

```bat
copy backend\.env.example backend\.env
```

Edit `backend\.env` if you want to pre-fill API keys for platform mode. Leave blank to use BYOK mode.

### 4. Start the server

```bat
start.bat
```

The script will:
- Install all Python dependencies automatically
- Install Playwright browsers (first run only)
- Start the server at **http://127.0.0.1:3000**
- Open the browser automatically

---

## Quick Start (Linux / macOS)

```bash
git clone https://github.com/Rohit-4237/aeo-geo-tracker.git
cd aeo-geo-tracker/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --host 127.0.0.1 --port 3000
```

Then open http://127.0.0.1:3000 in your browser.

---

## Docker

```bash
docker-compose up --build
```

App will be available at http://localhost:3000.

---

## Usage

### Step 1 — Add brands
Go to **Brands** → add your primary brand (name + website URL) and up to 4 competitors.

### Step 2 — Upload prompts
Go to **Prompts** → upload a CSV file. Required column: `prompt`. Optional column: `category`.

Example CSV format:
```
prompt,category
"What is the best project management tool?",Awareness
"Compare Asana vs Monday.com",Comparison
```

### Step 3 — Configure API keys
Go to **Settings** → enter your API keys:
- **OpenAI** key for ChatGPT results
- **Gemini** key for Google Gemini results
- **Perplexity** key for Perplexity results
- Google AI Overviews and AI Mode use Playwright scraping (no key needed)

### Step 4 — Run a tracking job
Go to **Dashboard** → click **New Run** → name your run, select platforms, and start.

### Step 5 — View results
Go to **Results** → select a completed run to view:
- Overview (total mentions + citations per brand)
- By Prompt (per-prompt breakdown)
- Citations (exact URLs cited per brand)
- Sentiment (positive/negative/neutral scores)

---

## Project Structure

```
aeo-geo-tracker/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── models.py                # SQLAlchemy ORM models
│   ├── database.py              # DB connection + session
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   ├── routers/
│   │   ├── brands.py            # Brand CRUD
│   │   ├── prompts.py           # Prompt upload + CRUD
│   │   ├── tracking.py          # Run management + execution
│   │   ├── analytics.py         # Analytics endpoints
│   │   └── settings.py          # API key settings
│   └── services/
│       ├── openai_service.py    # ChatGPT integration
│       ├── gemini_service.py    # Gemini REST integration
│       ├── perplexity_service.py
│       ├── google_scraper.py    # Playwright scraper
│       └── sentiment.py         # VADER sentiment analysis
├── frontend/
│   ├── index.html               # Single-page application
│   └── static/
│       ├── app.js               # Alpine.js app logic
│       └── styles.css
├── docker-compose.yml
├── start.bat                    # Windows one-click launcher
└── Prompt example.csv           # Sample prompts file
```

---

## API Reference

The backend exposes a REST API. Interactive docs available at http://127.0.0.1:3000/docs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/brands/` | List all brands |
| POST | `/brands/` | Add a brand |
| DELETE | `/brands/{id}/` | Remove a brand |
| GET | `/prompts/` | List all prompts |
| POST | `/prompts/upload` | Upload CSV of prompts |
| GET | `/runs/` | List all tracking runs |
| POST | `/runs/` | Start a new run |
| GET | `/runs/{id}/` | Get run status |
| GET | `/analytics/{id}/overview/` | Brand mention totals |
| GET | `/analytics/{id}/by-prompt/` | Per-prompt breakdown |
| GET | `/analytics/{id}/citations/` | Cited URLs per brand |
| GET | `/analytics/{id}/sentiment/` | Sentiment scores |
| GET | `/settings/` | Get current settings |
| POST | `/settings/` | Update API keys / mode |

---

## Environment Variables

| Variable | Description |
|---|---|
| `PLATFORM_OPENAI_API_KEY` | OpenAI key (platform mode only) |
| `PLATFORM_GEMINI_API_KEY` | Gemini key (platform mode only) |
| `PLATFORM_PERPLEXITY_API_KEY` | Perplexity key (platform mode only) |
| `DATABASE_URL` | SQLAlchemy DB URL (default: SQLite) |
| `CORS_ORIGINS` | Allowed CORS origins |

---

## License

MIT
