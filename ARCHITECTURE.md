# Swarm Architecture & Agent Coordination

## Overview

The Autonomous Research Agent implements a **sequential agent swarm** architecture where specialized agents execute different research phases in order. Each agent is autonomous but coordinated through a central orchestrator.

## Swarm Model

### Sequential Execution

```
User Submit Topic
        ↓
    ┌───────────────────────────────────────────┐
    │ Phase 1: Planner & Executor Agent        │
    │ - Decompose topic into sub-questions      │
    │ - Execute ReAct planning loop             │
    │ - Gather initial evidence                 │
    │ Status: planning → executing              │
    └───────────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │ Phase 2: Verifier Agent                   │
    │ - Cross-reference claims                  │
    │ - Score confidence (high/medium/low)      │
    │ - Detect conflicts                        │
    │ Status: verifying                         │
    └───────────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │ Phase 3: Reporter Agent                   │
    │ - Synthesize findings                     │
    │ - Generate markdown report                │
    │ - Create inline citations                 │
    │ Status: generating                        │
    └───────────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────────┐
    │ Phase 4: Polish Agent                     │
    │ - Finalize session                        │
    │ - Prepare for UI display                  │
    │ Status: completed                         │
    └───────────────────────────────────────────┘
        ↓
    Report Ready for User
```

## Component Interactions

### 1. Web UI ↔ Backend

```
User Interface (index.html)
    ↓
    ├─ POST /api/research/start
    │  └─ Creates new session
    │  └─ Triggers run_research_swarm() in background
    │
    ├─ GET /api/research/{session_id}
    │  └─ Polls current session status
    │  └─ Returns phase progress
    │
    ├─ GET /api/research/{session_id}/evidence
    │  └─ Retrieves evidence bank
    │  └─ Updates evidence display
    │
    └─ GET /api/research/{session_id}/report-text
       └─ Downloads final report
       └─ Displays markdown
```

### 2. Backend ↔ Orchestrator

```
FastAPI Backend (backend.py)
    ↓
SwarmOrchestrator (swarm_orchestrator.py)
    ├─ create_session()
    │  └─ ResearchSession object
    │
    ├─ add_evidence()
    │  └─ Appends to evidence_bank
    │  └─ Persists to SQLite
    │
    ├─ update_session()
    │  └─ Updates phase/status
    │  └─ Saves to DB
    │
    └─ get_session()
       └─ Retrieves session state
```

### 3. Orchestrator ↔ Phase Agents

```
SwarmOrchestrator.sessions
    ↓
Phase1Agent.execute()
    └─ Reads: session.topic, session.depth
    └─ Writes: orchestrator.add_evidence()
    └─ Updates: orchestrator.update_session()
    ↓
Phase2Agent.execute()
    └─ Reads: session.evidence_bank, session.verify
    └─ Modifies: confidence scores
    ↓
Phase3Agent.execute()
    └─ Reads: session.evidence_bank
    └─ Writes: reports/{topic}_{timestamp}.md
    └─ Updates: session.progress["phase_3"]["report_path"]
    ↓
Phase4Agent.execute()
    └─ Finalizes: session.status = "completed"
```

## Data Flow

### Evidence Bank Structure

```python
evidence_bank = [
    {
        "claim_id": "abc123def456",
        "claim": "AI will replace 25% of software jobs by 2030",
        "source_url": "https://example.com/article1",
        "confidence": "high",  # high / medium / low
        "created_at": "2026-04-28T10:30:00"
    },
    ...
]
```

### SQLite Schema

```sql
-- Session metadata
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    topic TEXT,
    depth INTEGER,
    verify BOOLEAN,
    model TEXT,
    status TEXT,  -- planning, executing, verifying, generating, completed, failed
    phase TEXT,   -- phase_1, phase_2, phase_3, phase_4
    progress TEXT,  -- JSON
    evidence_bank TEXT,  -- JSON
    errors TEXT,  -- JSON
    created_at TEXT,
    updated_at TEXT
);

-- Individual claims
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    session_id TEXT,
    claim TEXT,
    source_url TEXT,
    confidence TEXT,
    verified BOOLEAN,
    created_at TEXT
);

-- Cross-reference results
CREATE TABLE verifications (
    verification_id TEXT PRIMARY KEY,
    claim_id TEXT,
    source_url TEXT,
    verdict TEXT,  -- supports / contradicts / unrelated
    created_at TEXT
);
```

## Agent Lifecycle

### Execution Flow

```python
async def run_research_swarm(session_id: str):
    session = orchestrator.get_session(session_id)
    
    # Sequential execution
    for agent in [Phase1Agent(), Phase2Agent(), Phase3Agent(), Phase4Agent()]:
        success = await agent.execute(session)
        
        if not success:
            orchestrator.update_session(session_id, status="failed")
            return False
    
    return True  # All phases completed
```

### Error Handling

Each agent:
1. Wraps execution in try/except
2. Calls `orchestrator.add_error()` on failure
3. Returns False if phase fails
4. Swarm stops immediately

Example:
```python
try:
    self.log(session.session_id, "Starting...")
    # Do work
    return True
except Exception as e:
    orchestrator.add_error(session.session_id, f"Phase1: {str(e)}")
    return False
```

## Scaling Patterns

### Current: Sequential Phases
- ✅ Simple coordination
- ✅ Predictable resource usage
- ✅ Natural dependency order
- ❌ Slower (phases wait for previous to finish)

### Future: Parallel Within Phase
```python
# Multiple Phase1 agents searching simultaneously
agents = [
    Phase1SearchAgent(query1),
    Phase1SearchAgent(query2),
    Phase1SearchAgent(query3),
]
results = await asyncio.gather(*[agent.execute(session) for agent in agents])
```

### Future: Dynamic Depth
```python
# Adaptive research based on evidence quality
while session.progress["phase_1"]["evidence_count"] < MIN_EVIDENCE:
    await Phase1Agent().execute(session)
    session = orchestrator.get_session(session_id)
```

## State Management

### Session Lifecycle

```
[NEW] ──create_session()──>
    ↓
[PLANNING] ──Phase1.execute()──>
    ↓
[EXECUTING] ──Phase1.complete()──>
    ↓
[VERIFYING] ──Phase2.execute()──>
    ↓
[GENERATING] ──Phase3.execute()──>
    ↓
[COMPLETED] ──Phase4.execute()──>
    ↓
[READY FOR UI]
    
    OR
    
[FAILED] ──error in any phase──>
```

### Progress Tracking

Each phase has progress metadata:
```python
progress = {
    "phase_1": {
        "status": "executing",  # pending, executing, completed, failed
        "iterations": 5,        # how many search loops
        "evidence_count": 12    # claims gathered
    },
    "phase_2": {
        "status": "pending",
        "claims_verified": 0,
        "conflicts_found": 0
    },
    "phase_3": {
        "status": "pending",
        "report_path": "reports/..."
    },
    "phase_4": {
        "status": "pending"
    }
}
```

## Coordination Mechanisms

### 1. Shared State (Orchestrator)
All agents read/write through SwarmOrchestrator:
- Consistent evidence bank
- Atomic session updates
- Centralized error logging

### 2. Event-Based Updates
UI polls session status:
```javascript
setInterval(() => {
    fetch(`/api/research/${sessionId}`)
        .then(r => r.json())
        .then(session => updateUI(session))
}, 2000);
```

### 3. Database Persistence
Every update to orchestrator persists to SQLite:
```python
def update_session(self, session_id: str, **kwargs):
    # Update in-memory
    session = self.sessions[session_id]
    # Persist to DB
    self._save_session(session)
```

## Performance Characteristics

### Current Implementation
- **Latency per phase**: ~5-30 seconds (simulated)
- **Total research time**: Phase1(30s) + Phase2(20s) + Phase3(10s) + Phase4(5s) = ~65s
- **Memory**: ~10-50MB per active session
- **Database size**: ~100KB per 100 claims

### Optimization Opportunities
1. **Parallel searches**: Run 3-5 Phase1 agents concurrently
2. **Incremental verification**: Start Phase2 while Phase1 still gathering evidence
3. **Report generation**: Start Phase3 while Phase2 verifies
4. **Caching**: Avoid re-searching common topics

## Extending the Swarm

### Add a New Phase Agent

1. Create class inheriting from `BaseAgent`
2. Implement `async def execute(session)` 
3. Add to agents list in `run_research_swarm()`

```python
class Phase5Agent(BaseAgent):
    async def execute(self, session: ResearchSession) -> bool:
        self.log(session.session_id, "Starting Phase 5...")
        # Your logic
        orchestrator.update_session(session_id, phase="phase_5")
        return True
```

### Add a New Tool

1. Define tool in `tools.py`
2. Add schema to Phase1Agent
3. Implement execution logic
4. Call from ReAct loop

```python
async def search_web(query: str, num_results: int = 5):
    """Search DuckDuckGo for results."""
    results = await ddg_search(query, max_results=num_results)
    return [{"title": r.title, "url": r.href, "snippet": r.description} for r in results]
```

## Monitoring & Observability

### Logging Endpoints
- **Session logs**: `GET /api/sessions`
- **Evidence**: `GET /api/research/{id}/evidence`
- **Progress**: `GET /api/research/{id}` (real-time)
- **Errors**: In session.errors array

### Database Queries
```sql
-- Find all sessions
SELECT * FROM sessions ORDER BY created_at DESC;

-- Get evidence for a session
SELECT * FROM claims WHERE session_id = ?;

-- Find conflicting claims
SELECT c1.claim, c2.claim FROM claims c1, claims c2
WHERE c1.session_id = c2.session_id AND c1.claim_id != c2.claim_id
AND v1.verdict = 'contradicts';
```

## Best Practices

1. **Always use orchestrator**: Don't bypass for local state
2. **Log progress**: Call `self.log()` frequently for debugging
3. **Handle errors gracefully**: Return False, don't raise
4. **Respect session config**: Check `session.depth`, `session.verify`
5. **Update progress**: Set `progress[phase]["status"]` frequently
6. **Persist evidence**: Use `orchestrator.add_evidence()` not local storage
