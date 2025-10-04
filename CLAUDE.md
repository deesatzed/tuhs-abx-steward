# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TUHS Antibiotic Steward v2.0 is a dual-stack clinical decision support system for antibiotic recommendations. The project combines:
- **Node.js/Express** backend with OpenRouter integration, PostgreSQL/pgvector knowledge base, and streaming SSE responses
- **Python/FastAPI** backend with Agno AI agents, dynamic TUHS guideline loading from `ABXguideInp.json`, and evidence search coordination
- **Alpine.js** reactive frontend with Tailwind CSS/DaisyUI styling

Both backends serve the same clinical purpose but use different AI frameworks. The Node.js stack uses OpenRouter's API with custom tools and prompt engineering, while the Python stack uses Agno agents with specialized infection-type routing.

## Build and Development Commands

### Node.js Stack
```bash
# Install dependencies
npm install

# Start Express server (port 3000)
npm start

# Development with hot reload
npm run dev

# Run tests with coverage
npm test

# Lint code
npm run lint

# Database setup
npm run setup:db
npm run load:knowledge
```

### Python Stack
```bash
# Create and activate virtual environment
python3 -m venv venv_agno
source venv_agno/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements_agno.txt

# Start FastAPI server (port 8080)
python fastapi_server.py

# Run pytest tests
pytest -v
pytest tests/test_simple_agents.py -v  # Specific test file
```

## Architecture Overview

### Node.js Stack (`server.js`)
- **Entry Point**: `server.js` - Express server with SSE streaming
- **Core Modules**: All reusable logic in `lib/`
  - `lib/agentService.js` - OpenRouter agent orchestration and streaming
  - `lib/clinicalTools.js` - Clinical tools for drug interactions, renal dosing, allergy checks
  - `lib/knowledgeBase.js` - PostgreSQL/pgvector RAG retrieval
  - `lib/modelRouter.js` - Dynamic model selection (ward/ICU/complex cases)
  - `lib/promptBuilder.js` - Request sanitization and prompt construction
  - `lib/auditLogger.js` - Audit trail generation
- **Database Scripts**: `scripts/setup-database.js`, `scripts/load-knowledge.js`
- **Tests**: `tests/*.test.js` - Uses Node.js native test runner with c8 coverage (target: 85%+)
- **Frontend**: `public/` - Static assets served by Express

### Python Stack (`fastapi_server.py`)
- **Entry Point**: `fastapi_server.py` - FastAPI server with async request handling
- **Core Components**:
  - `agno_bridge_v2.py` - Agno agent bridge with TUHS guideline loader
  - `evidence_coordinator_full.py` - Evidence search coordinator (IDSA/CDC/WHO/PubMed)
  - `tuhs_multi_agent_system.py` - Multi-agent orchestration system
  - `amm_model.py` - AMM model for evidence evaluation
  - `evidence_agents.py` - Specialized evidence search agents
- **Frontend**: `alpine_frontend.html`, `clean_frontend.html` - Served by FastAPI
- **Guidelines**: `ABXguideInp.json` (64KB) - TUHS institutional antibiotic guidelines loaded dynamically into agent instructions
- **Tests**: `tests/test_*.py` - Pytest with coverage reporting (see `pytest.ini`)

### Guideline Loading Pattern (Python Stack)
The Python stack uses `TUHSGuidelineLoader` class to parse `ABXguideInp.json` and inject institutional guidelines directly into Agno agent instructions. Each infection type (Pneumonia, UTI, SSTI, Meningitis, etc.) gets a specialized agent loaded with 40-1900 lines of TUHS-specific protocols including drug names, doses, routes, allergy decision trees, and de-escalation criteria.

### Dual Backend Strategy
- **Node.js**: Production-ready with streaming, pgvector RAG, OpenRouter model routing, and comprehensive tooling
- **Python**: Agno-based multi-agent system with dynamic guideline loading and manual evidence search
- Both share clinical purpose but differ in AI orchestration approach
- Frontends are separate (Express serves `public/`, FastAPI serves HTML files)

## Common Development Tasks

### Adding New Clinical Tools (Node.js)
1. Add tool definition to `lib/clinicalTools.js` following the `toolDefinitions` array pattern
2. Implement tool function in the same file
3. Update tests in `tests/clinicalTools.test.js`
4. Tools are automatically available to the agent via `lib/agentService.js`

### Adding New Infection Agent (Python)
1. Add infection category to `InfectionCategory` class in `agno_bridge_v2.py`
2. Ensure corresponding entry exists in `ABXguideInp.json`
3. `TUHSGuidelineLoader.build_agent_instructions()` will automatically parse JSON and create agent instructions
4. Agent is dynamically created in `_create_agents()` method

### Database Operations
Node.js stack uses PostgreSQL with pgvector extension for RAG:
- Connection via `DATABASE_URL` environment variable
- Schema creation: `npm run setup:db`
- Knowledge loading: `npm run load:knowledge` (chunks `ABXguideInp.json` into embeddings)
- Queries use hybrid search (semantic + keyword) with configurable weights

### Testing Requirements
Per user's global CLAUDE.md:
- All testing must achieve 100% coverage unless explicitly waived
- Test failures require action plans to address gaps
- No mock, placeholders, simulation, or cached responses without explicit approval
- Each step must be validated before proceeding

### Error Handling
Per user's global CLAUDE.md:
- Keep error log paired with mitigation strategy
- If error occurs 3+ times, reflect on 5-7 possible sources, distill to 1-2 most likely, add logs to validate assumptions before implementing code fix

## Environment Configuration

### Required Environment Variables (Node.js)
```bash
OPENROUTER_API_KEY=sk-or-v1-xxx
DATABASE_URL=postgresql://user:password@localhost:5435/antibiotic_db
DEFAULT_MODEL=google/gemini-2.5-flash-lite-preview-09-2025
FALLBACK_MODEL=x-ai/grok-4-fast
ICU_MODEL=x-ai/grok-4-fast
```

### Required Environment Variables (Python)
```bash
OPENROUTER_API_KEY=sk-or-v1-xxx
# Python stack does not use DATABASE_URL - loads guidelines directly from JSON
```

See `.env.example` for all configuration options.

## API Endpoints

### Node.js Stack (port 3000)
- `GET /api/health` - Health check with database status
- `POST /api/recommendation` - Streaming recommendation (SSE)
- Static files served from `public/`

### Python Stack (port 8080)
- `GET /` - Alpine.js frontend
- `GET /health` - Health check
- `POST /api/recommendation` - Generate recommendation
- `GET /api/docs` - Swagger UI documentation
- `GET /api/models` - List available AI models
- `GET /api/infection-types` - List supported infection types

## Deployment

### Node.js Production
```bash
# With PM2 (recommended)
pm2 start ecosystem.config.js

# Direct with clustering
node server.js
```

### Python Production
```bash
# With multiple workers
uvicorn fastapi_server:app --host 0.0.0.0 --port 8080 --workers 4

# Or with Gunicorn
gunicorn fastapi_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
```

### Fly.io Deployment
Project includes `fly.toml` and `Dockerfile` for Python stack deployment. See `DEPLOYMENT_GUIDE.md` for comprehensive production deployment steps including Nginx reverse proxy, SSL certificates, and PM2 process management.

## Code Style

### Node.js/JavaScript
- ECMAScript modules (`import`/`export`)
- 2-space indentation, single quotes, trailing commas
- ESLint configuration in `.eslintrc.cjs`
- Pure helper functions with verb-noun naming (`buildPromptVariables`)
- Service modules with noun-based naming (`agentService`)

### Python
- PEP 8 style
- Type hints with `typing` module
- Async/await patterns for I/O operations
- Class-based organization for agents and coordinators

## Key Files to Understand

### Node.js Critical Path
1. `server.js` - Main Express app with SSE streaming
2. `lib/agentService.js` - OpenRouter agent orchestration (11 specialized agents)
3. `lib/clinicalTools.js` - Clinical decision support tools
4. `lib/knowledgeBase.js` - RAG retrieval from pgvector

### Python Critical Path
1. `fastapi_server.py` - FastAPI app with CORS and lazy bridge initialization
2. `agno_bridge_v2.py` - Loads `ABXguideInp.json` and creates infection-specific Agno agents
3. `evidence_coordinator_full.py` - Coordinates evidence search across IDSA/CDC/WHO/PubMed
4. `ABXguideInp.json` - Source of truth for TUHS institutional guidelines

## Important Constraints

From user's global CLAUDE.md:
- **NEVER use mock, placeholders, simulation, cached responses, or demo** without explicit permission
- **No time estimates in build steps**
- **Build checklists required** - changes outside checklist need approval
- **100% test coverage** expected unless waived
- Errors occurring 3+ times require systematic debugging (reflect on sources, add logs, validate assumptions)

## Audit Logging

Both stacks implement comprehensive audit logging:

### Python Stack
- **Module**: `audit_logger.py`
- **Location**: `logs/audit-YYYY-MM-DD.log`
- **View logs**: `/Users/o2satz/miniforge3/envs/abx13/bin/python scripts/view_audit_logs.py`
- **API endpoint**: `GET /api/audit/summary?date=YYYY-MM-DD`

### Node.js Stack
- **Module**: `lib/auditLogger.js`
- **Location**: `logs/audit-YYYY-MM-DD.log`
- **View logs**: `cat logs/audit-$(date +%Y-%m-%d).log | jq '.'`

### What's Logged
- Request ID and timestamp
- Patient data (de-identified, API keys redacted)
- Infection category determined
- Confidence scores (TUHS and final)
- Response time
- Error messages (if any)

See [AUDIT_LOGGING.md](AUDIT_LOGGING.md) for complete documentation.

## Troubleshooting

### Port Already in Use (Node.js)
```bash
lsof -ti :3000 | xargs kill -9
```

### Port Already in Use (Python)
```bash
lsof -ti :8080 | xargs kill -9
```

### Import Errors (Python)
```bash
source venv_agno/bin/activate
pip install -r requirements_agno.txt
```

### Database Connection Issues
- Verify PostgreSQL is running: `psql -d antibiotic_db -c "SELECT version();"`
- Check `DATABASE_URL` in `.env`
- Ensure pgvector extension is installed

### API Key Issues
```bash
# Verify .env file has key set
grep OPENROUTER_API_KEY .env
```

## Git Workflow

- Main branch: `main`
- Write imperative commit messages <60 chars (e.g., "Switch to Responses API")
- Pull requests need problem statement, testing commands, and rendered Markdown evidence for UI changes
- Never commit `.env` file (see `.gitignore`)
