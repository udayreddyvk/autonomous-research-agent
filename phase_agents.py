"""
Phase-specific agent implementations with real research tools.
"""

import asyncio
import json
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from pathlib import Path

from swarm_orchestrator import orchestrator, ResearchSession
from tools import (
    search_web,
    scrape_page,
    extract_claims,
    verify_claim,
    generate_research_plan,
    synthesize_report,
    claim_from_search_result
)


class BaseAgent(ABC):
    """Base agent class for phase execution."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, session: ResearchSession) -> bool:
        """Execute agent phase. Returns True if successful."""
        pass

    def log(self, session_id: str, message: str):
        """Log agent activity."""
        print(f"[{self.name}] {message}")


MODE_SETTINGS = {
    "fast": {
        "questions": 1,
        "search_results": 4,
        "scrape_limit": 0,
        "llm_extract": False,
        "verify_claims": 0,
        "verify_sources": 0,
        "llm_report": False,
    },
    "balanced": {
        "questions": 2,
        "search_results": 5,
        "scrape_limit": 1,
        "llm_extract": True,
        "verify_claims": 6,
        "verify_sources": 1,
        "llm_report": True,
    },
    "deep": {
        "questions": 5,
        "search_results": 6,
        "scrape_limit": 2,
        "llm_extract": True,
        "verify_claims": 12,
        "verify_sources": 2,
        "llm_report": True,
    },
}


def get_mode_settings(session: ResearchSession) -> Dict[str, Any]:
    """Return bounded execution settings for the selected research mode."""
    mode = session.progress.get("settings", {}).get("mode", "balanced")
    return MODE_SETTINGS.get(mode, MODE_SETTINGS["balanced"])


class Phase1Agent(BaseAgent):
    """Planner & Executor - Generates plan, searches web, extracts claims."""

    def __init__(self):
        super().__init__("Phase1Agent (Planner & Executor)")

    async def execute(self, session: ResearchSession) -> bool:
        """Execute core research loop with real tools."""
        try:
            self.log(session.session_id, f"Starting research on: '{session.topic}'")
            orchestrator.update_session(
                session.session_id,
                status="executing",
                phase="phase_1"
            )

            # Step 1: Generate research plan via LLM
            settings = get_mode_settings(session)
            effective_depth = min(session.depth, settings["questions"])
            if session.progress.get("settings", {}).get("mode") == "fast":
                plan = [f"{session.topic} overview"]
            else:
                self.log(session.session_id, "Generating research plan...")
                plan = await generate_research_plan(session.topic, effective_depth, model=session.model)
            self.log(session.session_id, f"Plan: {plan}")

            # Step 2: Execute each sub-question
            for i, question in enumerate(plan):
                self.log(session.session_id, f"[{i+1}/{len(plan)}] Searching: {question}")

                # Search web
                results = await asyncio.to_thread(
                    search_web,
                    question,
                    max_results=settings["search_results"]
                )
                if not results:
                    self.log(session.session_id, f"No search results for: {question}")
                    continue

                # Search snippets provide useful cited evidence when pages block scraping.
                for result in results:
                    snippet_claim = claim_from_search_result(result, session.topic)
                    if snippet_claim:
                        orchestrator.add_evidence(
                            session.session_id,
                            claim=snippet_claim["claim"],
                            source_url=snippet_claim["source_url"],
                            confidence=snippet_claim["confidence"]
                        )

                if not settings["scrape_limit"]:
                    progress = session.progress
                    progress["phase_1"]["iterations"] = i + 1
                    progress["phase_1"]["evidence_count"] = len(session.evidence_bank)
                    orchestrator.update_session(session.session_id, progress=progress)
                    continue

                # Scrape the top results concurrently. Fast mode skips scraping entirely.
                scrape_tasks = []
                urls_to_scrape = [
                    r["url"]
                    for r in results[:settings["scrape_limit"]]
                    if r.get("url")
                ]
                for url in urls_to_scrape:
                    scrape_tasks.append(asyncio.to_thread(scrape_page, url))

                scraped_pages = await asyncio.gather(*scrape_tasks, return_exceptions=True)

                # Extract claims from each scraped page
                for page in scraped_pages:
                    if isinstance(page, Exception):
                        self.log(session.session_id, f"Scrape error: {page}")
                        continue
                    if not page.get("success") or not page.get("markdown"):
                        continue

                    self.log(
                        session.session_id,
                        f"Extracting claims from: {page['url'][:60]}..."
                    )

                    if settings["llm_extract"]:
                        claims = await extract_claims(
                            page["markdown"],
                            page["url"],
                            session.topic,
                            model=session.model
                        )
                    else:
                        claims = []

                    for claim in claims:
                        orchestrator.add_evidence(
                            session.session_id,
                            claim=claim["claim"],
                            source_url=page["url"],
                            confidence=claim.get("confidence", "medium")
                        )
                        self.log(
                            session.session_id,
                            f"  -> Claim: {claim['claim'][:80]}..."
                        )

                # Update progress
                progress = session.progress
                progress["phase_1"]["iterations"] = i + 1
                progress["phase_1"]["evidence_count"] = len(session.evidence_bank)
                orchestrator.update_session(
                    session.session_id,
                    progress=progress
                )

            progress = session.progress
            progress["phase_1"]["status"] = "completed"
            orchestrator.update_session(session.session_id, progress=progress)

            self.log(session.session_id, f"Phase 1 complete. Evidence: {len(session.evidence_bank)}")
            if not session.evidence_bank:
                orchestrator.add_error(
                    session.session_id,
                    "No evidence was collected. Web search returned no usable results, or all sources were blocked."
                )
                return False
            return True

        except Exception as e:
            orchestrator.add_error(session.session_id, f"Phase1: {str(e)}")
            return False


class Phase2Agent(BaseAgent):
    """Verifier - Cross-references sources and scores confidence."""

    def __init__(self):
        super().__init__("Phase2Agent (Verifier)")

    async def execute(self, session: ResearchSession) -> bool:
        """Execute verification pass."""
        try:
            if not session.verify:
                self.log(session.session_id, "Verification disabled, skipping")
                progress = session.progress
                progress["phase_2"]["status"] = "skipped"
                orchestrator.update_session(session.session_id, progress=progress)
                return True

            settings = get_mode_settings(session)
            if settings["verify_claims"] == 0:
                self.log(session.session_id, "Verification skipped for fast mode")
                progress = session.progress
                progress["phase_2"]["status"] = "skipped"
                orchestrator.update_session(session.session_id, progress=progress)
                return True

            self.log(session.session_id, "Starting source verification")
            orchestrator.update_session(
                session.session_id,
                status="verifying",
                phase="phase_2"
            )

            evidence = list(session.evidence_bank)[:settings["verify_claims"]]
            for i, claim in enumerate(evidence):
                self.log(session.session_id, f"Verifying claim {i+1}/{len(evidence)}")

                # Search for corroboration
                search_results = await asyncio.to_thread(
                    search_web,
                    claim["claim"][:100],
                    max_results=3
                )

                support_count = 0
                contradict_count = 0

                for result in search_results[:settings["verify_sources"]]:
                    if result.get("url") == claim.get("source_url"):
                        continue

                    page = await asyncio.to_thread(scrape_page, result["url"])
                    if not page.get("success") or not page.get("markdown"):
                        continue

                    verdict = await verify_claim(
                        claim["claim"],
                        page["markdown"],
                        model=session.model
                    )
                    if verdict == "supports":
                        support_count += 1
                    elif verdict == "contradicts":
                        contradict_count += 1

                # Update confidence
                new_confidence = claim["confidence"]
                if contradict_count > 0:
                    new_confidence = "low"
                elif support_count >= 2:
                    new_confidence = "high"
                elif support_count >= 1:
                    new_confidence = "medium"
                else:
                    new_confidence = "low"

                claim["confidence"] = new_confidence

                progress = session.progress
                progress["phase_2"]["claims_verified"] = i + 1
                orchestrator.update_session(
                    session.session_id,
                    progress=progress,
                    evidence_bank=session.evidence_bank
                )

                await asyncio.sleep(0.1)

            progress = session.progress
            progress["phase_2"]["status"] = "completed"
            orchestrator.update_session(session.session_id, progress=progress)

            self.log(session.session_id, "Phase 2 complete")
            return True

        except Exception as e:
            orchestrator.add_error(session.session_id, f"Phase2: {str(e)}")
            return False


class Phase3Agent(BaseAgent):
    """Reporter - Generates human-readable markdown report via LLM."""

    def __init__(self):
        super().__init__("Phase3Agent (Reporter)")

    async def execute(self, session: ResearchSession) -> bool:
        """Generate final markdown report."""
        try:
            self.log(session.session_id, "Starting report generation")
            orchestrator.update_session(
                session.session_id,
                status="generating",
                phase="phase_3"
            )

            # Use LLM to synthesize a human-readable report
            report = await synthesize_report(
                session.topic,
                session.evidence_bank,
                model=session.model,
                use_llm=get_mode_settings(session)["llm_report"]
            )

            if not report.strip():
                raise ValueError("Report generation produced no content")

            # Save report
            timestamp = session.created_at.replace(":", "-").split(".")[0]
            topic_slug = "".join(
                c if c.isalnum() or c in "-_" else "_"
                for c in session.topic.lower().replace(" ", "_")
            )[:30]
            report_path = f"reports/{topic_slug}_{timestamp}.md"

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)

            self.log(session.session_id, f"Report saved to {report_path}")

            progress = session.progress
            progress["phase_3"]["status"] = "completed"
            progress["phase_3"]["report_path"] = report_path
            orchestrator.update_session(
                session.session_id,
                progress=progress
            )

            return True

        except Exception as e:
            orchestrator.add_error(session.session_id, f"Phase3: {str(e)}")
            return False


class Phase4Agent(BaseAgent):
    """Polish - Finalizes session."""

    def __init__(self):
        super().__init__("Phase4Agent (Polish)")

    async def execute(self, session: ResearchSession) -> bool:
        """Finalize session."""
        try:
            self.log(session.session_id, "Finalizing session")

            progress = session.progress
            progress["phase_4"]["status"] = "completed"
            orchestrator.update_session(
                session.session_id,
                status="completed",
                phase="phase_4",
                progress=progress
            )

            self.log(session.session_id, "Research complete!")
            return True

        except Exception as e:
            orchestrator.add_error(session.session_id, f"Phase4: {str(e)}")
            return False


async def run_research_swarm(session_id: str):
    """Execute all phases sequentially."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    agents = [
        Phase1Agent(),
        Phase2Agent(),
        Phase3Agent(),
        Phase4Agent()
    ]

    for agent in agents:
        success = await agent.execute(session)
        if not success:
            orchestrator.update_session(session_id, status="failed")
            return False

    return True
