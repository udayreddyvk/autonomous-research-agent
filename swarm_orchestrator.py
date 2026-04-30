"""
Swarm Orchestrator - Manages sequential execution of research phases with specialized agents.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

from config import Config


@dataclass
class ResearchSession:
    """Active research session state."""
    session_id: str
    topic: str
    depth: int
    verify: bool
    model: str
    status: str  # planning, executing, verifying, generating, completed, failed
    phase: str   # phase_1, phase_2, phase_3, phase_4
    progress: Dict[str, Any]  # phase-specific progress
    evidence_bank: List[Dict]
    errors: List[Dict]
    created_at: str
    updated_at: str


class SwarmOrchestrator:
    """Coordinates agent swarms through research phases."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.database_path
        self.sessions: Dict[str, ResearchSession] = {}
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(Config.report_path).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_sessions()

    def _init_db(self):
        """Initialize SQLite database for evidence bank."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                topic TEXT,
                depth INTEGER,
                verify BOOLEAN,
                model TEXT,
                status TEXT,
                phase TEXT,
                progress TEXT,
                evidence_bank TEXT,
                errors TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                session_id TEXT,
                claim TEXT,
                source_url TEXT,
                confidence TEXT,
                verified BOOLEAN,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                verification_id TEXT PRIMARY KEY,
                claim_id TEXT,
                source_url TEXT,
                verdict TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def create_session(
        self,
        topic: str,
        depth: int = 3,
        verify: bool = True,
        model: str = "deepseek/deepseek-v4-pro",
        mode: str = "balanced"
    ) -> str:
        """Create new research session."""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        session = ResearchSession(
            session_id=session_id,
            topic=topic,
            depth=depth,
            verify=verify,
            model=model,
            status="planning",
            phase="phase_1",
            progress={
                "phase_1": {"status": "pending", "iterations": 0},
                "phase_2": {"status": "pending", "claims_verified": 0},
                "phase_3": {"status": "pending"},
                "phase_4": {"status": "pending"},
                "settings": {"mode": mode}
            },
            evidence_bank=[],
            errors=[],
            created_at=now,
            updated_at=now
        )

        self.sessions[session_id] = session
        self._save_session(session)
        return session_id

    def update_session(self, session_id: str, **kwargs):
        """Update session state."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        for key, value in kwargs.items():
            if hasattr(session, key):
                # Deep copy mutable values to ensure setattr actually replaces the reference
                if isinstance(value, (dict, list)):
                    value = json.loads(json.dumps(value))
                setattr(session, key, value)

        session.updated_at = datetime.now().isoformat()
        self._save_session(session)

    def add_evidence(
        self,
        session_id: str,
        claim: str,
        source_url: str,
        confidence: str = "medium"
    ) -> str:
        """Add claim to evidence bank."""
        claim_id = str(uuid.uuid4())[:12]
        now = datetime.now().isoformat()

        session = self.sessions[session_id]
        session.evidence_bank.append({
            "claim_id": claim_id,
            "claim": claim,
            "source_url": source_url,
            "confidence": confidence,
            "created_at": now
        })

        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (claim_id, session_id, claim, source_url, confidence, 0, now))
        conn.commit()
        conn.close()

        self.update_session(session_id, evidence_bank=session.evidence_bank)
        return claim_id

    def add_error(self, session_id: str, error: str):
        """Log error in session."""
        session = self.sessions[session_id]
        session.errors.append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.update_session(session_id, errors=session.errors)

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Retrieve session by ID."""
        return self.sessions.get(session_id)

    def find_completed_session(
        self,
        topic: str,
        mode: str,
        model: str
    ) -> Optional[ResearchSession]:
        """Return the newest completed matching session for instant repeat reads."""
        normalized_topic = topic.strip().lower()
        matches = []
        for session in self.sessions.values():
            settings = session.progress.get("settings", {})
            report_path = session.progress.get("phase_3", {}).get("report_path")
            if (
                session.status == "completed"
                and session.topic.strip().lower() == normalized_topic
                and settings.get("mode") == mode
                and session.model == model
                and report_path
                and Path(report_path).exists()
            ):
                matches.append(session)

        if not matches:
            return None
        return sorted(matches, key=lambda item: item.updated_at, reverse=True)[0]

    def _load_sessions(self):
        """Load persisted sessions from SQLite on startup."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, topic, depth, verify, model, status, phase,
                   progress, evidence_bank, errors, created_at, updated_at
            FROM sessions
        """)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            (
                session_id,
                topic,
                depth,
                verify,
                model,
                status,
                phase,
                progress,
                evidence_bank,
                errors,
                created_at,
                updated_at,
            ) = row
            self.sessions[session_id] = ResearchSession(
                session_id=session_id,
                topic=topic,
                depth=depth,
                verify=bool(verify),
                model=model,
                status=status,
                phase=phase,
                progress=json.loads(progress or "{}"),
                evidence_bank=json.loads(evidence_bank or "[]"),
                errors=json.loads(errors or "[]"),
                created_at=created_at,
                updated_at=updated_at,
            )

    def _save_session(self, session: ResearchSession):
        """Persist session to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.topic,
            session.depth,
            session.verify,
            session.model,
            session.status,
            session.phase,
            json.dumps(session.progress),
            json.dumps(session.evidence_bank),
            json.dumps(session.errors),
            session.created_at,
            session.updated_at
        ))
        conn.commit()
        conn.close()


# Global orchestrator instance
orchestrator = SwarmOrchestrator()
