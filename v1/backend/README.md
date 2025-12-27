# Case Analysis System - Backend

FastAPI-based backend for legal case document analysis.

## Setup

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Poetry (for dependency management)

### Installation

1. Install dependencies:
```bash
cd backend
poetry install
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. Start services:
```bash
docker-compose up -d
```

4. Run database migrations:
```bash
poetry run alembic upgrade head
```

5. Start API (development):
```bash
poetry run uvicorn app.main:app --reload
```

API will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

## Project Structure

```
backend/
├── app/
│   ├── api/          # API endpoints
│   ├── domain/       # Business logic, commands, events
│   ├── db/           # Database models
│   ├── services/     # AI service, document processor (later)
│   └── config.py     # Configuration
├── alembic/          # Database migrations
├── tests/            # Tests
└── docker-compose.yml
```

## Development

- API documentation: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO Console: http://localhost:9001 (admin/minioadmin)
