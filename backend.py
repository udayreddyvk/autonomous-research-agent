"""
FastAPI backend for research agent swarm.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
from pathlib import Path

from swarm_orchestrator import orchestrator
from phase_agents import run_research_swarm
from config import Config
from tools import build_instant_report


app = FastAPI(title="Autonomous Research Agent \u2014 Sci-Fi Edition")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    """Request to start research."""
    topic: str
    depth: int = Field(default=3, ge=1, le=5)
    verify: bool = True
    model: str = Config.kimi_model
    mode: str = Field(default="balanced", pattern="^(fast|balanced|deep)$")


class SessionResponse(BaseModel):
    """Session state response."""
    session_id: str
    topic: str
    status: str
    phase: str
    progress: dict
    evidence_count: int
    evidence_bank: list
    errors: list


@app.post("/api/research/start")
async def start_research(request: ResearchRequest):
    """Start a new research session."""
    cached_session = orchestrator.find_completed_session(
        topic=request.topic,
        mode=request.mode,
        model=request.model
    )
    if cached_session:
        return {
            "session_id": cached_session.session_id,
            "message": f"Loaded cached research session on '{request.topic}'",
            "cache_hit": True
        }

    session_id = orchestrator.create_session(
        topic=request.topic,
        depth=request.depth,
        verify=request.verify,
        model=request.model,
        mode=request.mode
    )
    _write_instant_report(session_id, request.topic, request.mode)

    # Run swarm in background
    asyncio.create_task(run_research_swarm(session_id))

    return {
        "session_id": session_id,
        "message": f"Started research session on '{request.topic}'",
        "cache_hit": False
    }


@app.get("/api/research/{session_id}")
async def get_session_status(session_id: str):
    """Get current session status."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "topic": session.topic,
        "status": session.status,
        "phase": session.phase,
        "progress": session.progress,
        "evidence_count": len(session.evidence_bank),
        "evidence_bank": session.evidence_bank,
        "errors": [e["error"] for e in session.errors]
    }


@app.get("/api/research/{session_id}/evidence")
async def get_evidence(session_id: str):
    """Get evidence bank for session."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "evidence": list(session.evidence_bank),
        "count": len(session.evidence_bank)
    }


@app.get("/api/research/{session_id}/report")
async def get_report(session_id: str):
    """Get generated report."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    report_path = session.progress.get("phase_3", {}).get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report not generated")

    return FileResponse(report_path, media_type="text/markdown")


@app.get("/api/research/{session_id}/report-text")
async def get_report_text(session_id: str):
    """Get report as text."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    report_path = session.progress.get("phase_3", {}).get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report not generated")

    with open(report_path, "r", encoding="utf-8") as f:
        return {"content": f.read()}


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    sessions = []
    for session_id, session in orchestrator.sessions.items():
        sessions.append({
            "session_id": session_id,
            "topic": session.topic,
            "status": session.status,
            "phase": session.phase,
            "created_at": session.created_at
        })
    return {"sessions": sessions}


@app.get("/api/health")
async def health_check():
    """Return non-secret runtime configuration for troubleshooting."""
    return {
        "status": "ok",
        "api_base_url": Config.kimi_api_url,
        "model": Config.kimi_model,
        "api_key_configured": bool(Config.kimi_api_key),
        "firecrawl_configured": bool(Config.firecrawl_api_key),
    }


@app.get("/")
async def root():
    """Serve main dashboard."""
    return FileResponse("ui/index.html")


# Serve static files
ui_path = Path("ui")
if ui_path.exists():
    app.mount("/static", StaticFiles(directory="ui"), name="static")


def _write_instant_report(session_id: str, topic: str, mode: str):
    """Attach a readable draft immediately so the UI never starts blank."""
    session = orchestrator.get_session(session_id)
    if not session:
        return

    report_dir = Path(Config.report_path)
    report_dir.mkdir(parents=True, exist_ok=True)
    topic_slug = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in topic.lower().replace(" ", "_")
    )[:30] or "research"
    report_path = report_dir / f"{topic_slug}_{session.created_at.replace(':', '-').split('.')[0]}_instant.md"
    report_path.write_text(build_instant_report(topic, mode), encoding="utf-8")

    progress = session.progress
    progress["phase_3"]["status"] = "draft"
    progress["phase_3"]["report_path"] = str(report_path)
    progress["phase_3"]["instant"] = True
    orchestrator.update_session(session_id, progress=progress)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.server_host, port=Config.server_port)
