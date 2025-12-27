# Case Analysis System - MVP

AI-powered legal case document analysis system with full provenance tracking.

## Architecture

Event Sourcing + CQRS architecture for auditability and scalability.
See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture and implementation plan.

## Technology Stack

**Backend:**
- Python 3.11 + FastAPI
- PostgreSQL (with pgvector)
- Redis + Celery
- MinIO (S3-compatible storage)

**Frontend:**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- TanStack Query

**AI:**
- Anthropic Claude 3.5 Sonnet
- OpenAI Embeddings

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Poetry (Python dependency management)

### Setup

1. **Clone and navigate to project:**
```bash
cd case-analysis-system/v1
```

2. **Backend Setup:**
```bash
cd backend

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and OPENAI_API_KEY
```

3. **Frontend Setup:**
```bash
cd frontend

# Install dependencies
npm install
```

4. **Start all services:**
```bash
cd backend
docker-compose up -d
```

5. **Run database migrations:**
```bash
poetry run alembic upgrade head
```

6. **Start backend API (in new terminal):**
```bash
cd backend
poetry run uvicorn app.main:app --reload
```

7. **Start frontend (in new terminal):**
```bash
cd frontend
npm run dev
```

### Access the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **MinIO Console:** http://localhost:9001 (minioadmin / minioadmin)

## Project Structure

```
v1/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
└── ARCHITECTURE.md   # Detailed architecture plan
```

## Development Workflow

Phase 1 (Current): Foundation setup ✅
- Cases list UI
- Create/view cases
- Basic infrastructure

Phase 2-10: See [ARCHITECTURE.md](ARCHITECTURE.md) for full implementation phases.

## Core Features (When Complete)

- 📄 **Document Analysis** - AI-powered extraction with citations
- 📊 **Case Summary** - Multi-document synthesis
- 📅 **Timeline** - Chronological event tracking
- ⚠️ **Conflict Detection** - Auto-detect contradictions
- 💬 **Chat** - RAG-based Q&A with grounded responses
- 🔍 **Provenance** - Every fact traces to exact source

## License

Private project
