# Quick Start Guide

## 🚀 Get Running in 2 Minutes

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up API Keys (Optional for Testing)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:
```env
KIMI_API_URL=https://openrouter.ai/api/v1
KIMI_API_KEY=sk-or-v1-your_key_here
KIMI_MODEL=deepseek/deepseek-v4-pro
```

**Note**: Can skip this for simulation mode (mock data)

### Step 3: Start the Server
```bash
python start.py
```

Or directly:
```bash
python -m uvicorn backend:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: Open Dashboard
Browser will open automatically to:
```
http://localhost:8000
```

---

## 📝 How to Use

### Basic Research
1. **Enter a topic**: "Latest developments in quantum computing"
2. **Adjust settings** (optional):
   - **Depth**: 3-5 for quick research, 7-10 for thorough
   - **Verify**: Enable to cross-reference sources
   - **Model**: DeepSeek V4 Pro for depth, DeepSeek V4 Flash for speed
3. **Click "Start Research"**
4. **Watch progress** in real-time
5. **Download report** when complete

### Example Topics to Try
- "Impact of AI on software engineering jobs 2026"
- "Latest cancer treatment breakthroughs"
- "Most promising renewable energy technologies"
- "Remote work productivity trends"
- "Blockchain adoption in enterprise"

---

## 🏗️ System Architecture

```
┌─────────────────────────┐
│   Web Dashboard         │
│  (index.html)           │
└────────────┬────────────┘
             │
       FastAPI Backend
       (backend.py)
             │
    ┌────────┴────────┐
    │                 │
Phase1Agent      Phase2Agent
(Search)         (Verify)
    │                 │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │                 │
Phase3Agent      Phase4Agent
(Report)         (Polish)
```

### Key Files

| File | Purpose |
|------|---------|
| `backend.py` | FastAPI server & REST API |
| `swarm_orchestrator.py` | Agent coordination & state |
| `phase_agents.py` | 4 specialized agents |
| `ui/index.html` | Web dashboard |
| `config.py` | Configuration loading |
| `start.py` | Startup script |

---

## 📊 What Each Agent Does

### Phase 1: Planning & Execution
- Breaks topic into sub-questions
- Searches for information
- Collects raw evidence
- **Status**: `executing`

### Phase 2: Verification
- Checks claims against multiple sources
- Scores confidence (high/medium/low)
- Flags conflicts
- **Status**: `verifying`

### Phase 3: Report Generation
- Synthesizes findings
- Creates markdown with citations
- Formats bibliography
- **Status**: `generating`

### Phase 4: Finalization
- Wraps up session
- Prepares for display
- **Status**: `completed`

---

## 🔌 API Endpoints

### Start Research
```bash
curl -X POST http://localhost:8000/api/research/start \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI and jobs",
    "depth": 3,
    "verify": true,
    "model": "deepseek/deepseek-v4-pro"
  }'
```

Response:
```json
{
  "session_id": "a1b2c3d4",
  "message": "Started research session..."
}
```

### Get Status
```bash
curl http://localhost:8000/api/research/a1b2c3d4
```

### Get Evidence
```bash
curl http://localhost:8000/api/research/a1b2c3d4/evidence
```

### Get Report
```bash
curl http://localhost:8000/api/research/a1b2c3d4/report-text
```

---

## 📈 Real-Time Progress

The dashboard updates every 2 seconds with:
- **Current phase** (Planning, Executing, Verifying, etc.)
- **Evidence count** (how many claims collected)
- **Phase progress** (visual progress bars)
- **Errors** (if any)

---

## 💾 Output Files

### Reports
```
reports/
├── ai_and_job_displacement_2026-04-28T10-30-00.md
└── quantum_computing_2026-04-28T11-45-30.md
```

Markdown format with:
- Executive summary
- Key findings by sub-question
- Inline citations [^1]
- Bibliography

### Database
```
logs/
└── research.db (SQLite)
   ├── sessions table
   ├── claims table
   └── verifications table
```

---

## 🐛 Troubleshooting

### "Port 8000 already in use"
```bash
# Kill process on port 8000
# macOS/Linux:
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Then try a different port:
```bash
python -m uvicorn backend:app --port 8001
```

### "Module not found" errors
```bash
pip install --upgrade -r requirements.txt
```

### API key errors
- Ensure `.env` is in project root
- Check `KIMI_API_KEY` is valid
- Remove `.env` to run in simulation mode

### Dashboard not updating
- Check browser console for JavaScript errors
- Try refreshing the page
- Check backend is still running

---

## 🔧 Customization

### Change Default Parameters
Edit `config.py`:
```python
DEFAULT_DEPTH = 5
DEFAULT_VERIFY = True
KIMI_MODEL = "deepseek/deepseek-v4-pro"
```

### Modify Report Template
Edit `Phase3Agent._build_report()` in `phase_agents.py`

### Add New Search Tool
1. Create function in `tools.py`
2. Add schema to Phase1Agent
3. Update ReAct loop

### Change Agent Behavior
Edit individual agents in `phase_agents.py`:
```python
class Phase1Agent(BaseAgent):
    async def execute(self, session):
        # Your custom logic here
```

---

## 📚 Learn More

- **Architecture details**: See `ARCHITECTURE.md`
- **Full plan**: See `MVP_PLAN.md`
- **API docs**: http://localhost:8000/docs
- **Contributing**: See `README.md`

---

## ⚡ Performance Tips

1. **For quick testing**: Use `depth=1-3`, `model=deepseek/deepseek-v4-flash`
2. **For thorough research**: Use `depth=3-5`, `model=deepseek/deepseek-v4-pro`
3. **Enable verification** only when accuracy is critical
4. **Disable browser DevTools** for better performance

---

## 📞 Support

If you encounter issues:

1. Check logs: `tail -f logs/research.db`
2. Review phase output in dashboard
3. Check `.env` configuration
4. Ensure internet connection (for DuckDuckGo)
5. Verify Python 3.8+ installed: `python --version`

---

## 🎯 Next Steps

1. ✅ Run a test search
2. ✅ Review generated report
3. ✅ Modify phase agents for your needs
4. ✅ Add custom tools
5. ✅ Deploy to production

Happy researching! 🚀
