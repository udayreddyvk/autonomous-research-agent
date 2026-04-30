# Autonomous Research Agent

A web-based AI research workspace that searches the internet, collects source evidence, tracks progress, and turns findings into a readable report.

Unlike a normal one-shot chatbot answer, this project is built around a visible research workflow: search, collect, verify, synthesize, and inspect.

## What This Project Does

- Accepts any research topic from the browser UI.
- Searches the web in real time using DuckDuckGo search.
- Scrapes useful source pages with Firecrawl when configured, with a basic fallback scraper.
- Uses an OpenAI-compatible LLM endpoint through OpenRouter.
- Generates a compact report with evidence and source links.
- Shows progress while the research job runs.
- Saves past searches in the browser.
- Stores generated reports locally in `reports/`.

## Why Use This Instead Of A Chatbot?

Chatbots are great for quick answers, brainstorming, and explanations. This project is for when you want a more traceable research flow.

This app gives users:

- A clear progress view instead of a black-box wait.
- Source evidence collected during the run.
- A final report that can be inspected, downloaded, and reviewed.
- Separate research modes for speed versus depth.
- A local record of generated reports.

Some modern chatbots can browse the web too, but this project is intentionally shaped like a research desk rather than a chat window.

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- UI: React loaded from CDN in `ui/index.html`
- Search: DuckDuckGo via `ddgs`
- Scraping: Firecrawl when configured, fallback HTTP scraping otherwise
- LLM: OpenRouter using the OpenAI-compatible Python client
- Storage: SQLite database in `logs/research.db`
- Reports: Markdown files in `reports/`

## Project Structure

```text
autonomous-research-agent/
  backend.py                FastAPI app and API routes
  config.py                 Environment/config loader
  phase_agents.py           Research, verification, and reporting phases
  swarm_orchestrator.py     Session state and persistence
  tools.py                  Search, scrape, LLM, and report helpers
  start.py                  Local startup helper
  ui/index.html             Browser UI
  docs/                     Human-readable project guide
  requirements.txt          Python dependencies
  .env.example              Example environment variables
```

Generated local folders such as `logs/`, `reports/`, and `__pycache__/` should not be committed to GitHub.

## Requirements

- Python 3.10 or newer recommended
- OpenRouter API key
- Firecrawl API key optional

## Setup

1. Clone the project or download the source.

2. Create a virtual environment.

```bash
python -m venv .venv
```

3. Activate it.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

4. Install dependencies.

```bash
pip install -r requirements.txt
```

5. Create your environment file.

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

6. Edit `.env`.

```env
KIMI_API_URL=https://openrouter.ai/api/v1
KIMI_API_KEY=your_openrouter_api_key_here
KIMI_MODEL=deepseek/deepseek-v4-pro

FIRECRAWL_API_KEY=your_firecrawl_api_key_here
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
```

Do not commit `.env` to GitHub.

## Run Locally

Option 1:

```bash
python backend.py
```

Option 2:

```bash
python start.py
```

Open the site:

```text
http://127.0.0.1:8000
```

API health check:

```text
http://127.0.0.1:8000/api/health
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Deploy On Vercel

This project includes `app.py` as the Vercel FastAPI entrypoint. It imports the real FastAPI app from `backend.py`.

In the Vercel project dashboard, add these Environment Variables:

```env
KIMI_API_URL=https://openrouter.ai/api/v1
KIMI_API_KEY=your_openrouter_api_key_here
KIMI_MODEL=deepseek/deepseek-v4-pro
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
```

`FIRECRAWL_API_KEY` is optional. On Vercel, generated runtime files are stored in `/tmp`, because the deployed code folder should be treated as read-only.

## Research Modes

- Fast Brief: quickest run, source-backed overview, skips slower deep work.
- Balanced Study: recommended mode for normal use.
- Deep Review: slower, more careful, with stronger verification.

## GitHub Safety Checklist

Before uploading, confirm these files are not committed:

- `.env`
- `logs/`
- `reports/`
- `__pycache__/`
- `.venv/`
- Any private API keys

If an API key was ever committed by mistake, rotate the key immediately from the provider dashboard.

## Notes

- The app can still produce fallback reports if the LLM key is missing, but quality will be lower.
- Firecrawl improves page extraction but is optional.
- Generated reports and local session data are intentionally kept on your machine.
