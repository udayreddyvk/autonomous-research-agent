# Autonomous Research Agent - MVP Plan

## Overview

A command-line AI agent that accepts a research topic, autonomously searches the web, synthesizes findings, cross-references sources for accuracy, and produces a cited markdown report.

**Core Learning Goals:** Tool use, planning loops, source verification, context window management.

---

## Architecture

```
User Input (Topic/Question)
    |
    v
+--------------------------------+
|         Planner (LLM)          |
|  - Decomposes topic into       |
|    sub-questions               |
|  - Generates search strategy   |
+--------------------------------+
    |
    v
+--------------------------------+
|      Executor (Loop)           |
|  - Calls Search Tool           |
|  - Calls Fetch/WebRead Tool    |
|  - Calls Summarize Tool        |
+--------------------------------+
    |
    v
+--------------------------------+
|      Synthesizer (LLM)         |
|  - Merges findings             |
|  - Cross-references sources    |
|  - Detects conflicts           |
+--------------------------------+
    |
    v
+--------------------------------+
|      Report Generator          |
|  - Structured markdown output  |
|  - Inline citations            |
|  - Source bibliography         |
+--------------------------------+
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| LLM Client | `openai` SDK → Kimi API (`moonshot-v1-8k` / `moonshot-v1-32k` free tier)<br>Base URL: `https://api.kimi.com/coding/` |
| Web Search | DuckDuckGo (`duckduckgo-search`) — completely free, no API key |
| Web Fetch | Firecrawl API (`firecrawl-py`) — free tier available |
| Planning | ReAct pattern with tool-calling loop |
| Context Mgmt | Sliding window + summarization cache |
| Output | Markdown files |

---

## Phase 1: Core Loop (Week 1)

### 1.1 Tool Definitions

Define 4 tools as JSON schemas for the LLM:

**`search_web(query: str, num_results: int = 5)`**
- Uses DuckDuckGo to get result titles, URLs, snippets.
- Returns structured JSON list.

**`fetch_page(url: str)`**
- Scrapes and extracts clean markdown via Firecrawl API (`/scrape`).
- Returns `{url, title, markdown, status}`.

**`summarize_text(text: str, context: str)`**
- LLM call to extract key claims relevant to the research topic.
- Returns bullet points with inline source markers.

**`write_note(claim: str, source_url: str, confidence: str)`**
- Appends to an internal evidence bank (SQLite or JSONL).
- Confidence levels: `high` / `medium` / `low`.

### 1.2 ReAct Planning Loop

```python
system_prompt = """You are a research agent. Given a topic, plan and execute research.
You have access to tools: search_web, fetch_page, summarize_text, write_note.

Rules:
1. First, create a research plan with 3-5 sub-questions.
2. Execute steps one at a time.
3. After gathering evidence, call write_note for each distinct claim.
4. When sufficient evidence is collected, respond with FINAL_ANSWER.
5. Cite every claim with its source URL.

Think step by step. Respond in this format:
Thought: [your reasoning]
Action: [tool_name]
Action Input: [json]
Observation: [result]
"""
```

The executor runs a `while` loop:
1. Send conversation history to LLM.
2. Parse `Thought`/`Action`/`Action Input`.
3. Execute tool locally.
4. Append `Observation` to history.
5. Repeat until `FINAL_ANSWER` or max iterations (default: 15).

### 1.3 Context Window Management

Problem: 15 tool calls + large web pages can exceed 200k tokens.

Solutions:
- **Truncation:** After fetching a page, truncate to first 8,000 tokens before sending to LLM. Add a marker `[... truncated ...]`.
- **Rolling Summary:** Every 5 loop iterations, ask the LLM to summarize the conversation so far into a `progress_summary`. Replace earlier tool calls with this summary.
- **Evidence Bank:** Offload claims to SQLite. The LLM only holds the research plan + recent 3 observations + a compressed evidence digest.

---

## Phase 2: Source Verification (Week 2)

### 2.1 Cross-Referencing Engine

After initial evidence collection, run a verification pass:

```python
def verify_claim(claim: str, source_url: str, evidence_bank: list):
    # Find 2-3 other sources making the same or contradictory claim
    related = search_web(claim[:100], num_results=5)
    for result in related:
        if result.url == source_url:
            continue
        text = fetch_page(result.url)
        verdict = llm_check(claim, text)  # supports / contradicts / unrelated
        store_verification(claim, result.url, verdict)
```

### 2.2 Confidence Scoring

| Criteria | Modifier |
|----------|----------|
| Claim found in 3+ independent sources | `high` |
| Claim found in 1-2 sources | `medium` |
| Only found in original source | `low` |
| Sources contradict each other | `conflict` |

Conflicting claims are flagged in the final report for human review.

---

## Phase 3: Report Generation (Week 2)

### 3.1 Structure Template

```markdown
# Research Report: {topic}

## Executive Summary
3-4 sentences on key findings.

## Key Findings
### 1. [Sub-question 1]
- Claim A [^1]
- Claim B [^2]

### 2. [Sub-question 2]
...

## Conflicts & Uncertainties
- Source X says A; Source Y says B. (Flagged for review)

## Sources
[^1]: [Title](URL) - Retrieved 2026-04-28
[^2]: [Title](URL) - Retrieved 2026-04-28
```

### 3.2 Citation Integrity

- Every claim in the report must map to an entry in the evidence bank.
- Broken URLs or fetch failures are logged but not cited.
- Reports are saved to `reports/{topic_slug}_{timestamp}.md`.

---

## Phase 4: Polish & CLI (Week 3)

### 4.1 CLI Interface

```bash
python -m research_agent "Impact of AI on software engineering jobs"
  --depth 3              # Number of search iterations
  --verify               # Enable cross-reference pass
  --output ./reports     # Output directory
  --model moonshot-v1-8k
```

### 4.2 Logging & Observability

- `logs/research_{timestamp}.jsonl`: Every Thought/Action/Observation.
- `logs/evidence.db`: SQLite with tables `claims`, `sources`, `verifications`.
- Progress printed to stdout: `[1/15] Searching: "AI job displacement statistics"`

### 4.3 Cost Controls

- Track input/output tokens per run.
- Limit `fetch_page` to pages < 500KB.
- Hard stop at max iterations + token budget.

---

## File Structure

```
autonomous-research-agent/
├── research_agent/
│   ├── __init__.py
│   ├── main.py              # CLI entrypoint
│   ├── planner.py           # Research plan generation
│   ├── executor.py          # ReAct loop
│   ├── tools.py             # search_web, fetch_page, etc.
│   ├── evidence_bank.py     # SQLite storage
│   ├── verifier.py          # Cross-reference logic
│   ├── synthesizer.py       # Report generation
│   └── context_manager.py   # Truncation & rolling summaries
├── reports/                 # Generated reports
├── logs/                    # JSONL logs + SQLite DB
├── tests/
│   ├── test_tools.py
│   └── test_verifier.py
├── requirements.txt
└── README.md
```

---

## Milestones

| Week | Deliverable | Success Criteria |
|------|-------------|------------------|
| 1 | Core loop | Agent can take a topic, run 5+ searches, and output raw findings |
| 2 | Verification + Reports | Cross-referencing works; markdown report with citations generated |
| 3 | CLI + Polish | Usable CLI, logging, cost tracking, 3 example reports committed |

---

## Example Run

```bash
$ python -m research_agent "Latest treatments for type 2 diabetes 2025"
[1/15] Planning research...
[2/15] search_web: "type 2 diabetes new treatments 2025"
[3/15] fetch_page: https://...
[4/15] summarize_text: extracted 3 claims
[5/15] write_note: GLP-1 receptor agonists...
...
[12/15] verify_claim: cross-referencing GLP-1 efficacy...
[13/15] FINAL_ANSWER

Report written to: reports/latest_treatments_type_2_diabetes_20250428.md
Tokens used: 142,301
Sources cited: 8
```

---

## Future Enhancements (Post-MVP)

- **Parallel tool execution:** Fetch multiple pages simultaneously.
- **Recursive depth:** Follow links within fetched pages.
- **PDF support:** Ingest academic papers via `pymupdf`.
- **Structured output:** Use Pydantic models + Kimi tool use / JSON mode for stricter parsing.
- **Persistent memory:** Remember past research to avoid re-searching.
