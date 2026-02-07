# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mu2 Cognitive OS is a FERPA-compliant, local-only adaptive learning platform with a "Focus Mode" for accessibility. It's a Turborepo monorepo with a Next.js frontend and FastAPI/LangGraph backend.

**Critical FERPA Compliance**: This project handles educational data and must:
- NEVER include analytics, telemetry, or cloud services
- Keep ALL data on localhost only
- Run `./pre-boot.sh` before any development to verify no telemetry is present

## Common Commands

### Pre-boot Check (REQUIRED before development)
```bash
./pre-boot.sh          # Scan for and block telemetry code
```

### Development
```bash
# Install dependencies
npm install            # Root dependencies
cd apps/web && npm install
cd packages/brain && pip install -e .

# Start services
docker-compose up -d   # Postgres with pgvector + apache_age

# Frontend (Next.js 15)
cd apps/web && npm run dev     # http://localhost:3000

# Backend (FastAPI)
cd packages/brain && uvicorn src.main:app --reload  # http://localhost:8000
```

### Build, Test, Lint (Turborepo)
```bash
npm run build          # Build all workspaces
npm run test           # Run all tests
npm run lint           # Lint all workspaces
npm run format         # Format with Prettier
```

### Backend-specific
```bash
cd packages/brain
pytest tests/ -v                               # Run Python tests
pytest tests/test_hallucination.py -v          # Grounding tests
pytest tests/test_ferpa_compliance.py -v       # FERPA tests
./tests/run_grounding_tests.sh                 # Full compliance suite
```

### Database
```bash
# Postgres runs on port 54322 (mapped from container 5432)
psql -h localhost -p 54322 -U postgres -d postgres

# Initialize/seed data
psql -h localhost -p 54322 -U postgres -d postgres -f seed_data.sql
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/002_knowledge_vault.sql
```

## Architecture

### Monorepo Structure
```
apps/web/          # Next.js 15 App Router (React 19)
packages/brain/    # FastAPI + LangGraph state machine
supabase/          # Database migrations (pgvector + apache_age)
```

### Morning Circle State Machine (LangGraph)

The core backend is a LangGraph state machine in `packages/brain/src/graph/morning_circle.py`:

**Flow**: Input → Sentiment Analysis → Context Router → Retrieval → Output

1. **sentiment**: Analyzes user sentiment (currently heuristic-based)
2. **route**: Classifies query as "fact" (specific) or "concept" (abstract)
3. **retrieve**: Routes to vector store retrieval (`retrieval_nodes.py`)
4. **suggest_mode**: Suggests focus vs standard mode
5. **generate**: Creates response using retrieved context

State is defined in `src/core/state.py` (`MorningCircleState` TypedDict).

### Vector Store Architecture

**Two implementations exist** (check which is active):

1. **SQLiteVectorStore** (`sqlite_vector_store.py`) - Lightweight, uses Ollama embeddings locally
2. **SimpleVectorStore** (`simple_vector_store.py`) - Even simpler, in-memory

The Router Engine (`router_engine.py`) provides a LlamaIndex-based router between vector (facts) and graph (concepts) retrieval, but **V2 API endpoints are currently disabled** in `main.py` (lines 177-319) due to Postgres dependencies.

### Frontend Architecture

- **Next.js 15** with App Router (not Pages Router)
- **Focus Mode**: High-contrast black/white/yellow theme for accessibility (WCAG 2.1 AA)
- Components use a custom mode provider (`components/providers/mode-provider.tsx`)
- Tailwind config defines both `focus-*` and `standard-*` color palettes
- TypeScript path alias: `@/*` maps to `apps/web/*`

### Database

Postgres 15 with extensions:
- **pgvector**: For vector similarity search
- **apache_age**: For knowledge graph relationships

Migrations in `supabase/migrations/`:
- `001_initial_schema.sql`
- `002_knowledge_vault.sql`
- `seed_graph.sql`

## Configuration

### Environment Variables

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL`: Postgres connection (port 54322)
- `LLM_PROVIDER`: "ollama" (local only)
- `LLM_MODEL`: "gemma3:1b" (small model for resource-constrained systems)
- `LLM_BASE_URL`: "http://localhost:11434" (Ollama)

### Python Backend

Configuration in `packages/brain/src/core/config.py`:
- Uses `pydantic-settings` for env var loading
- Default embedding model: `nomic-embed-text` (768 dimensions)
- CORS restricted to localhost origins only

### Frontend

- `next.config.js` has NO analytics (instrumentation: false)
- `tsconfig.json` has strict mode enabled and `@/*` path alias
- Tailwind colors defined in `tailwind.config.ts`

## Key Files by Feature

| Feature | Files |
|---------|-------|
| LangGraph state machine | `packages/brain/src/graph/morning_circle.py`, `src/core/state.py` |
| Vector retrieval | `packages/brain/src/graph/retrieval_nodes.py`, `src/services/sqlite_vector_store.py` |
| API endpoints | `packages/brain/src/main.py` |
| Router engine (disabled V2) | `packages/brain/src/services/router_engine.py` |
| Graph store | `packages/brain/src/services/graph_store.py` |
| Focus mode UI | `apps/web/components/focus-mode-toggle.tsx`, `components/providers/mode-provider.tsx` |
| Chat interface | `apps/web/components/chat-interface.tsx` |
| Textbook viewer | `apps/web/components/textbook-viewer.tsx` |

## Testing & Compliance

### Grounding/Anti-Hallucination Tests
- The system must refuse to answer about fake topics (e.g., "Martian War of 1812")
- Run: `pytest tests/test_hallucination.py -v`

### FERPA Compliance Tests
- No PII in logs or responses
- Local-only processing (no external APIs)
- Run: `pytest tests/test_ferpa_compliance.py -v`

### Full Test Suite
```bash
./packages/brain/tests/run_grounding_tests.sh
```

This runs integration tests against the live API at `http://localhost:8000`.

## Important Notes

1. **No Cloud Services**: All LLM calls go through local Ollama (`http://localhost:11434`)
2. **CORS Locked to Localhost**: Check `src/core/config.py` - `allowed_origins` is localhost only
3. **V2 API Disabled**: Router engine endpoints are commented out in `main.py` due to Postgres dependencies
4. **Pre-boot Script**: Always run `./pre-boot.sh` before development to ensure FERPA compliance
5. **Node Version**: Requires Node >= 18.0.0
6. **Python Version**: Requires Python >= 3.11
