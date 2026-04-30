"""
Real research tools: web search, page scraping, and LLM calls.
"""

import json
import re
import asyncio
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from ddgs import DDGS
except Exception as exc:
    print(f"[startup] DuckDuckGo search unavailable: {exc}")
    DDGS = None

try:
    from firecrawl import FirecrawlApp
except Exception as exc:
    print(f"[startup] Firecrawl unavailable: {exc}")
    FirecrawlApp = None

try:
    from openai import AsyncOpenAI
except Exception as exc:
    print(f"[startup] OpenAI-compatible client unavailable: {exc}")
    AsyncOpenAI = None

from config import Config

# Initialize clients
_firecrawl = None
_openai = None


def _get_firecrawl() -> Any:
    global _firecrawl
    if FirecrawlApp is None:
        return None
    if _firecrawl is None and Config.firecrawl_api_key:
        _firecrawl = FirecrawlApp(api_key=Config.firecrawl_api_key)
    return _firecrawl


def _get_openai() -> Any:
    global _openai
    if AsyncOpenAI is None:
        return None
    if _openai is None and Config.kimi_api_key:
        _openai = AsyncOpenAI(
            api_key=Config.kimi_api_key,
            base_url=Config.kimi_api_url
        )
    return _openai


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Search DuckDuckGo and return structured results."""
    try:
        if DDGS is None:
            return []
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                }
                for r in results
                if r.get("href")
            ]
    except Exception as e:
        print(f"[search_web] Error: {e}")
        return []


def scrape_page(url: str) -> Dict[str, Any]:
    """Scrape a page using Firecrawl, fallback to basic requests."""
    try:
        fc = _get_firecrawl()
        if fc:
            if hasattr(fc, "scrape_url"):
                result = fc.scrape_url(url, params={"formats": ["markdown"]})
            else:
                result = fc.scrape(url, formats=["markdown"])

            markdown, title = _extract_firecrawl_content(result, url)
            return {
                "url": url,
                "title": title,
                "markdown": _truncate_text(markdown, 12000),
                "success": bool(markdown)
            }
    except Exception as e:
        print(f"[scrape_page] Firecrawl failed for {url}: {e}")

    # Fallback: basic requests + regex strip HTML
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        text = _html_to_text(resp.text)
        return {
            "url": url,
            "title": url,
            "markdown": _truncate_text(text, 12000),
            "success": True
        }
    except Exception as e2:
        print(f"[scrape_page] Fallback failed for {url}: {e2}")
        return {
            "url": url,
            "title": url,
            "markdown": "",
            "success": False
        }


def _html_to_text(html: str) -> str:
    """Very basic HTML to text conversion."""
    # Remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace common block tags with newlines
    html = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<(br|hr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Remove remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode entities
    import html as html_module
    html = html_module.unescape(html)
    # Collapse whitespace
    html = re.sub(r"\n\s*\n", "\n\n", html)
    html = re.sub(r"[ \t]+", " ", html)
    return html.strip()


def _truncate_text(text: str, max_chars: int = 12000) -> str:
    """Truncate text to roughly max_chars, preserving word boundaries."""
    if len(text) <= max_chars:
        return text
    trunc = text[:max_chars]
    last_space = trunc.rfind(" ")
    if last_space > max_chars * 0.8:
        trunc = trunc[:last_space]
    return trunc + "\n\n[... content truncated ...]"


def _extract_firecrawl_content(result: Any, url: str) -> tuple[str, str]:
    """Normalize Firecrawl v1/v2 response shapes."""
    if isinstance(result, dict):
        data = result.get("data") if isinstance(result.get("data"), dict) else result
        markdown = data.get("markdown", "") or data.get("content", "")
        metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
        return markdown or "", metadata.get("title", url)

    markdown = getattr(result, "markdown", "") or getattr(result, "content", "")
    metadata = getattr(result, "metadata", {}) or {}
    title = metadata.get("title", url) if isinstance(metadata, dict) else url
    return markdown or "", title


async def call_llm(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: int = 4000
) -> str:
    """Call the LLM via OpenAI-compatible Kimi API."""
    client = _get_openai()
    if not client:
        print("[call_llm] No LLM client available. Check KIMI_API_KEY.")
        return ""

    try:
        response = await client.chat.completions.create(
            model=model or Config.kimi_model,
            messages=messages,
            temperature=0.5,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"[call_llm] Error: {e}")
        return ""


async def generate_research_plan(topic: str, depth: int, model: Optional[str] = None) -> List[str]:
    """Use LLM to generate focused sub-questions for research."""
    prompt = (
        f"You are a research planner. Given the topic \"{topic}\", "
        f"generate exactly {depth} focused, specific sub-questions that will help thoroughly research this topic. "
        f"Each sub-question should be concise (1 sentence) and designed to yield factual, citable information. "
        f"Return ONLY a JSON array of strings, nothing else. Example: [\"What is...?\", \"How does...?\"]"
    )
    content = await call_llm([{"role": "user", "content": prompt}], model=model, max_tokens=800)
    return _parse_json_list(content, depth, topic)


async def extract_claims(
    text: str,
    source_url: str,
    topic: str,
    model: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Use LLM to extract factual claims from scraped text."""
    prompt = (
        f"You are analyzing an article about \"{topic}\". "
        f"Extract 1-5 factual claims from the following text. "
        f"For each claim, assign a confidence level (high, medium, or low) based on how well-supported it is in the text. "
        f"Return ONLY a JSON array of objects with keys 'claim' and 'confidence'. "
        f"Example: [{{\"claim\": \"X happened in 2023\", \"confidence\": \"high\"}}]\n\n"
        f"TEXT:\n{text[:8000]}"
    )
    content = await call_llm([{"role": "user", "content": prompt}], model=model, max_tokens=1200)
    claims = _parse_json_claims(content)
    if not claims:
        claims = _extract_claims_without_llm(text, topic)
    for c in claims:
        c["source_url"] = source_url
    return claims


async def verify_claim(claim: str, source_text: str, model: Optional[str] = None) -> str:
    """Use LLM to determine if a source supports, contradicts, or is unrelated to a claim."""
    prompt = (
        f"Claim: \"{claim}\"\n\n"
        f"Source text:\n{source_text[:6000]}\n\n"
        f"Does this source support, contradict, or not address the claim? "
        f"Answer with exactly one word: supports, contradicts, or unrelated."
    )
    content = await call_llm([{"role": "user", "content": prompt}], model=model, max_tokens=20)
    verdict = content.strip().lower()
    if "support" in verdict:
        return "supports"
    elif "contradict" in verdict:
        return "contradicts"
    return "unrelated"


async def synthesize_report(
    topic: str,
    evidence_bank: List[Dict[str, Any]],
    model: Optional[str] = None,
    use_llm: bool = True
) -> str:
    """Use LLM to synthesize evidence into a human-readable markdown report."""
    if not use_llm:
        return _build_fallback_report(topic, evidence_bank)

    evidence_text = "\n\n".join(
        f"- [{e['confidence'].upper()}] {e['claim']} (Source: {e['source_url']})"
        for e in evidence_bank
    )

    prompt = (
        f"Write a concise, beginner-friendly visual explainer on the topic: \"{topic}\".\n\n"
        f"Use the following evidence gathered from web sources. Cite sources naturally using [^1], [^2] style.\n\n"
        f"EVIDENCE:\n{evidence_text}\n\n"
        f"STRUCTURE:\n"
        f"# {topic}\n"
        f"## Quick Picture\n"
        f"(2 short sentences explaining the topic like the reader is new)\n\n"
        f"## Cartoon Map\n"
        f"(3 short bullet points that could become simple cartoon panels)\n\n"
        f"## Key Ideas\n"
        f"(5 short bullets maximum, each with a citation)\n\n"
        f"## Simple Analogy\n"
        f"(1 short analogy that makes the topic easy to remember)\n\n"
        f"## Sources\n"
        f"(Numbered list of all sources with URLs)\n\n"
        f"Keep the whole report compact. Use short paragraphs. Avoid long academic wording. "
        f"Prioritize clarity, visual imagination, and beginner-friendly language."
    )
    content = await call_llm([{"role": "user", "content": prompt}], model=model, max_tokens=1200)
    if content and len(content.strip()) >= 250:
        return content
    return _build_fallback_report(topic, evidence_bank)


def build_instant_report(topic: str, mode: str = "fast") -> str:
    """Create an immediate readable draft while live research continues."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    mode_name = {
        "fast": "Fast Brief",
        "balanced": "Balanced Study",
        "deep": "Deep Review",
    }.get(mode, "Research")

    return "\n".join([
        f"# {topic}",
        "",
        "## Instant Brief",
        "",
        f"This is a quick starter view for **{topic}**. The live research agent has already started collecting source evidence, and this draft will be replaced by the sourced report when the run finishes.",
        "",
        "## What You Can Read First",
        "",
        f"- **Topic:** {topic}",
        f"- **Mode:** {mode_name}",
        "- **Status:** live web search and evidence collection are running in the background.",
        "- **Best use:** read this as a launch pad, then inspect the final source-backed report.",
        "",
        "## What Happens Next",
        "",
        "- The agent searches the live web.",
        "- It collects snippets and source pages as evidence.",
        "- It verifies selected claims when the mode allows it.",
        "- It builds a final report with receipts you can inspect.",
        "",
        "## Sources",
        "",
        "Sources are still being collected. Check the Receipts tab as the run progresses.",
        "",
        f"_Instant draft generated {now}._",
    ])


# --- Helpers ---

def _parse_json_list(text: str, depth: int, topic: str) -> List[str]:
    """Parse a JSON array of strings from LLM output."""
    try:
        # Find JSON array in the text
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                return data[:depth]
    except Exception:
        pass

    # Fallback: split by lines/numbers
    lines = [re.sub(r"^\s*[-*\d.)]+\s*", "", line).strip()
             for line in text.split("\n") if line.strip()]
    lines = [l for l in lines if l and len(l) > 10]
    if len(lines) >= depth:
        return lines[:depth]

    # Ultimate fallback
    return [
        f"What is the current state of {topic}?",
        f"What are recent developments in {topic}?",
        f"What are the main challenges and future outlook for {topic}?"
    ][:depth]


def _parse_json_claims(text: str) -> List[Dict[str, str]]:
    """Parse a JSON array of claim objects from LLM output."""
    try:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [
                    {
                        "claim": str(item.get("claim", "")),
                        "confidence": item.get("confidence", "medium").lower()
                    }
                    for item in data
                    if isinstance(item, dict) and item.get("claim")
                ]
    except Exception:
        pass

    # Fallback: regex extraction
    claims = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith(("[", "{")):
            continue
        # Look for claim-like sentences
        if len(line) > 20 and any(c.isupper() for c in line):
            claims.append({"claim": line, "confidence": "medium"})
    return claims[:5]


def claim_from_search_result(result: Dict[str, str], topic: str) -> Optional[Dict[str, str]]:
    """Turn a search result snippet into evidence when page scraping is unavailable."""
    snippet = (result.get("snippet") or "").strip()
    title = (result.get("title") or "").strip()
    url = (result.get("url") or "").strip()

    if not url:
        return None
    if _is_low_signal_url(url):
        return None

    text = snippet or title
    if not text:
        return None

    cleaned = _clean_sentence(text)
    if len(cleaned) < 35:
        cleaned = _clean_sentence(f"{title}: {snippet}")

    if len(cleaned) < 35:
        return None

    if not _mentions_topic(f"{title} {cleaned}", topic):
        return None

    return {
        "claim": cleaned,
        "source_url": url,
        "confidence": "medium"
    }


def _extract_claims_without_llm(text: str, topic: str, limit: int = 5) -> List[Dict[str, str]]:
    """Extract readable factual sentences when the LLM is unavailable or returns invalid JSON."""
    candidates = []
    topic_terms = _topic_terms(topic)

    for sentence in re.split(r"(?<=[.!?])\s+", text):
        cleaned = _clean_sentence(sentence)
        if len(cleaned) < 60 or len(cleaned) > 320:
            continue
        if not _looks_informative(cleaned):
            continue

        score = sum(1 for term in topic_terms if term in cleaned.lower())
        score += 1 if re.search(r"\b(19|20)\d{2}\b|\b\d+(\.\d+)?%\b", cleaned) else 0
        candidates.append((score, cleaned))

    candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)

    seen = set()
    claims = []
    for score, sentence in candidates:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        claims.append({
            "claim": sentence,
            "confidence": "medium" if score > 0 else "low"
        })
        if len(claims) >= limit:
            break

    return claims


def _build_fallback_report(topic: str, evidence_bank: List[Dict[str, Any]]) -> str:
    """Create a deterministic markdown report so the UI never receives a blank report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    evidence = [e for e in evidence_bank if e.get("claim") and e.get("source_url")]

    lines = [
        f"# {topic}",
        "",
        "## Quick Picture",
        "",
    ]

    if not evidence:
        lines.extend([
            "The research agent could not collect usable source evidence for this topic. This usually means web search, scraping, or the configured LLM provider was unavailable during the run.",
            "",
            "## What To Check",
            "",
            "- Confirm the API key, model, and base URL in `.env` are valid.",
            "- Confirm this machine can reach the web search and source pages.",
            "- Try a more specific topic or reduce verification depth for a faster first run.",
            "",
            "## Sources",
            "",
            "No sources were collected.",
            "",
            f"_Generated {now}._",
        ])
        return "\n".join(lines)

    source_numbers = {}
    sources = []
    for item in evidence:
        url = item["source_url"]
        if url not in source_numbers:
            source_numbers[url] = len(sources) + 1
            sources.append(url)

    high = [e for e in evidence if e.get("confidence") == "high"]
    medium = [e for e in evidence if e.get("confidence") == "medium"]
    low = [e for e in evidence if e.get("confidence") not in {"high", "medium"}]
    best = (high + medium + low)[:2]

    summary_claims = " ".join(
        f"{_ensure_terminal_punctuation(e['claim'])} [{source_numbers[e['source_url']]}]"
        for e in best
    )
    lines.extend([
        f"Here is the short version from {len(sources)} source{'s' if len(sources) != 1 else ''}. {summary_claims}",
        "",
        "## Cartoon Map",
        "",
        f"- Imagine {topic} as a big scene with a few important moving parts.",
        "- Each source adds one labeled object to the scene.",
        "- The most useful facts become the captions.",
        "",
        "## Key Ideas",
        "",
    ])

    grouped = [
        ("High Confidence Findings", high),
        ("Moderate Confidence Findings", medium),
        ("Additional Findings", low),
    ]
    for heading, items in grouped:
        if not items:
            continue
        lines.extend([f"### {heading}", ""])
        for item in items[:5]:
            citation = source_numbers[item["source_url"]]
            lines.append(f"- {_ensure_terminal_punctuation(item['claim'])} [{citation}]")
        lines.append("")

    domains = Counter(_domain_from_url(url) for url in sources)
    top_domains = ", ".join(domain for domain, _ in domains.most_common(4) if domain)

    lines.extend([
        "## Source Notes",
        "",
        f"The source set includes {len(sources)} unique URL{'s' if len(sources) != 1 else ''}"
        + (f", with recurring material from {top_domains}." if top_domains else "."),
        "",
        "## Simple Analogy",
        "",
        f"Think of {topic} like a storyboard: sources provide the frames, evidence provides the captions, and the report connects the story.",
        "",
        "## Sources",
        "",
    ])

    for index, url in enumerate(sources, start=1):
        lines.append(f"{index}. {url}")

    lines.extend(["", f"_Generated {now}._"])
    return "\n".join(lines)


def _topic_terms(topic: str) -> List[str]:
    return [
        term
        for term in re.findall(r"[a-z0-9]+", topic.lower())
        if len(term) > 2
    ]


def _mentions_topic(text: str, topic: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _topic_terms(topic))


def _looks_informative(sentence: str) -> bool:
    lowered = sentence.lower()
    weak_markers = ("cookie", "privacy policy", "terms of use", "subscribe", "sign in")
    if any(marker in lowered for marker in weak_markers):
        return False
    return bool(re.search(r"[a-zA-Z]{4,}", sentence))


def _is_low_signal_url(url: str) -> bool:
    domain = _domain_from_url(url).lower()
    blocked_domains = (
        "quora.com",
        "reddit.com",
        "physicsforums.com",
        "wikimili.com",
        "grokipedia.com",
        "superfactful.com",
        "academicinfluence.com",
    )
    return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in blocked_domains)


def _clean_sentence(text: str) -> str:
    replacements = {
        "\u00c2\u00b7": "-",
        "\u00e2\u0080\u0093": "-",
        "\u00e2\u0080\u0094": "-",
        "\u00e2\u0080\u0099": "'",
        "\u00e2\u0080\u009c": '"',
        "\u00e2\u0080\u009d": '"',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\-\*\d.)\s]+", "", text)
    return text.strip(" \t\r\n-")


def _ensure_terminal_punctuation(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    return text if text[-1] in ".!?" else f"{text}."


def _domain_from_url(url: str) -> str:
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1).removeprefix("www.") if match else url
