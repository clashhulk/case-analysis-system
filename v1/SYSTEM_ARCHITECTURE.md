# Legal Case Analysis System - Architecture & Logic

**Version**: 1.0 (MVP)
**Date**: December 2025
**Status**: Active Development

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Data Flow](#data-flow)
4. [Storage Architecture](#storage-architecture)
5. [API Endpoints](#api-endpoints)
6. [State Machine](#state-machine)
7. [Cost Model](#cost-model)
8. [Database Schema](#database-schema)
9. [Component Details](#component-details)
10. [Deployment Info](#deployment-info)

---

## 🎯 System Overview

### Purpose
AI-powered legal document analysis system that:
- Uploads and stores legal case documents (PDF, DOCX, images)
- Extracts text using OCR and document parsers
- Analyzes documents with Claude 3.5 Haiku (summarization, classification)
- Extracts entities with GPT-4 (people, dates, locations, case numbers)
- Tracks costs and maintains audit trails
- Provides web UI for document management

### Tech Stack

```
Frontend:     React + TypeScript + Vite
Backend:      FastAPI + Python 3.11
Database:     PostgreSQL + pgvector
File Storage: MinIO (S3-compatible)
Cache:        Redis
AI APIs:      Anthropic Claude, OpenAI GPT-4
Task Queue:   Celery (optional)
```

### Key Statistics
- **Daily Budget**: $10.00 USD
- **Estimated Capacity**: 770-2000 documents/day
- **Max Document Size**: 50MB
- **Max Text Length**: 100,000 characters
- **Analysis Time**: 20-30 seconds per document
- **Cost per Document**: $0.005-$0.013

---

## 🏗️ Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                            │
│                    http://localhost:5173                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │ Upload Form  │  │ Case Manager │  │ Document Analyzer    │    │
│  └──────────────┘  └──────────────┘  └──────────────────────┘    │
└────────────┬───────────────────────────────────────────────────────┘
             │ REST API
             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                                │
│                   http://localhost:8000                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │ Case Routes  │  │ Document     │  │ Analysis Routes      │    │
│  │              │  │ Routes       │  │                      │    │
│  │ GET/POST     │  │              │  │ POST /analyze        │    │
│  │ /cases       │  │ POST /upload │  │ GET  /analysis       │    │
│  └──────────────┘  └──────────────┘  └──────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Services Layer                                 │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ • S3Service (File operations)                               │ │
│  │ • TextExtractionService (PDF/DOCX/OCR parsing)             │ │
│  │ • AIService (Claude + GPT-4 orchestration)                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Background Processing                          │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ • Download file from S3                                     │ │
│  │ • Extract text (quality scoring)                            │ │
│  │ • Run AI analysis (Claude + GPT-4 in parallel)             │ │
│  │ • Save results to PostgreSQL                                │ │
│  │ • Emit audit events                                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└──┬─────────────────────┬──────────────────────┬──────────────────┘
   │                     │                      │
   │ Files              │ Analysis Results     │ Events
   ▼                    ▼                      ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ MinIO (S3)   │  │ PostgreSQL    │  │ PostgreSQL   │
│              │  │ documents.    │  │ events table │
│ case-docs/   │  │ document_     │  │              │
│  ├─ doc1.pdf │  │ metadata      │  │ Audit trail  │
│  ├─ doc2.doc │  │ (JSONB)       │  │              │
│  └─ img.jpg  │  │              │  │ • Started    │
│              │  │ • extraction  │  │ • Extracted  │
│              │  │ • analysis    │  │ • Analyzed   │
│              │  │ • entities    │  │ • Failed     │
│              │  │ • processing  │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 📊 Data Flow

### Upload & Processing Flow

```
Step 1: USER UPLOADS DOCUMENT
┌─────────────────────┐
│ React Upload Form   │
└──────────┬──────────┘
           │ POST /documents
           ▼
┌─────────────────────────────────────────┐
│ 1. Validate file (type, size)           │
│ 2. Store in PostgreSQL (status=uploaded)│
│ 3. Upload to MinIO S3                   │
│ 4. Return document_id to frontend       │
└──────────┬──────────────────────────────┘
           │
           ▼ (File persisted)

Step 2: USER CLICKS "ANALYZE"
┌────────────────────────────────────────────────────────┐
│ POST /documents/{id}/analyze (force_reanalyze=false)  │
└──────────┬──────────────────────────────────────────┬──┘
           │ Sync Response                    │ Background Task
           │ (202 Accepted)                   │ (Async)
           ▼                                  ▼
    Return job_id          ┌──────────────────────────┐
                           │ BACKGROUND PROCESSING:   │
                           │                          │
                           │ 1. Download from MinIO   │
                           │ 2. Extract text          │
                           │    ├─ PDF → pdfplumber  │
                           │    ├─ DOCX → python-docx│
                           │    └─ IMG → Tesseract   │
                           │ 3. Quality score text    │
                           │ 4. Send to Claude        │
                           │    ├─ Summary           │
                           │    ├─ Classification    │
                           │    ├─ Key points        │
                           │    └─ Confidence        │
                           │ 5. Send to GPT-4        │
                           │    ├─ People            │
                           │    ├─ Dates             │
                           │    ├─ Locations         │
                           │    └─ Case numbers      │
                           │ 6. Calculate total cost │
                           │ 7. UPDATE PostgreSQL:   │
                           │    ├─ status=complete   │
                           │    └─ metadata=results  │
                           │ 8. Emit events          │
                           └──────────────────────────┘

Step 3: FRONTEND POLLS FOR RESULTS
┌──────────────────────────────────┐
│ GET /documents/{id}/analysis     │
│ (every 3 seconds)                │
└──────────┬───────────────────────┘
           │
           ▼ (status=analysis_complete)
┌──────────────────────────────────┐
│ Display results to user           │
│ ├─ Summary                        │
│ ├─ Classification                 │
│ ├─ Key Points                     │
│ ├─ Entities                       │
│ ├─ Cost                           │
│ └─ Processing Time                │
└──────────────────────────────────┘
```

---

## 💾 Storage Architecture

### Layer 1: File Storage (MinIO S3)
```
bucket: case-documents
├── {case-id}/
│   ├── {document-id}.pdf
│   ├── {document-id}.docx
│   └── {document-id}.jpg
│
Properties:
├─ Size: 1-50MB per file
├─ Retention: Permanent (until deleted)
├─ Access: Pre-signed URLs (1 hour expiry)
└─ Endpoint: http://localhost:9000
```

### Layer 2: Metadata (PostgreSQL - JSONB)
```
Table: documents
┌──────────────────────────────────────────────────────────┐
│ document_id (UUID)                                       │
│ case_id (UUID)                                           │
│ filename (TEXT)                                          │
│ original_filename (TEXT)                                 │
│ file_type (TEXT) → pdf, docx, jpg                       │
│ file_size (INTEGER)                                      │
│ s3_key (TEXT) → case-id/document-id.pdf                │
│ s3_bucket (TEXT)                                         │
│ status (TEXT) → uploaded | processing | analysis_       │
│               complete | extraction_failed | poor_quality│
│ document_metadata (JSONB) ◄─────────────────────────────┐
│ created_at (TIMESTAMP)                                   │
│ updated_at (TIMESTAMP)                                   │
└──────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │ JSONB Structure:                │
                    │                                 │
                    │ {                               │
                    │   "analysis": {                 │
                    │     "extraction": {             │
                    │       "text": "...",            │
                    │       "text_length": 5234,      │
                    │       "quality_score": 0.95,    │
                    │       "extraction_method":      │
                    │         "pdfplumber",           │
                    │       "extracted_at": "..."     │
                    │     },                          │
                    │     "analysis": {               │
                    │       "summary": "...",         │
                    │       "classification":         │
                    │         "Chargesheet",          │
                    │       "confidence": 0.92,       │
                    │       "key_points": [...],      │
                    │       "model": "claude-3-5-...  │
                    │     },                          │
                    │     "entities": {               │
                    │       "people": [{              │
                    │         "name": "John Doe",     │
                    │         "role": "Accused",      │
                    │         "confidence": 0.9       │
                    │       }],                       │
                    │       "dates": [...],           │
                    │       "locations": [...],       │
                    │       "case_numbers": [...],    │
                    │       "model": "gpt-4-turbo-..." │
                    │     },                          │
                    │     "processing": {             │
                    │       "started_at": "...",      │
                    │       "completed_at": "...",    │
                    │       "duration_ms": 25000,     │
                    │       "total_cost_usd": 0.0045  │
                    │     }                           │
                    │   }                             │
                    │ }                               │
                    └─────────────────────────────────┘

Size: 50KB - 500KB per document
Index: GIN index on JSONB for fast queries
```

### Layer 3: Audit Log (PostgreSQL)
```
Table: events
┌──────────────────────────────────────────────────────────┐
│ event_id (UUID)                                          │
│ aggregate_id (UUID) → document_id                        │
│ event_type (TEXT)                                        │
│   • DocumentUploaded                                     │
│   • DocumentAnalysisStarted                              │
│   • DocumentTextExtracted                                │
│   • DocumentAnalyzed                                     │
│   • DocumentAnalysisFailed                               │
│ event_data (JSONB)                                       │
│ metadata (JSONB) → cost_breakdown, models                │
│ occurred_at (TIMESTAMP)                                  │
│ created_at (TIMESTAMP)                                   │
└──────────────────────────────────────────────────────────┘

Size: ~1KB per event
Purpose: Audit trail, debugging, compliance, analytics
```

### Layer 4: Cache (Redis) - Future
```
redis://localhost:6379
├─ Session data
├─ Celery task queue
└─ Rate limiting counters
```

---

## 🔌 API Endpoints

### Case Management
```
GET    /api/v1/cases/                      List all cases
GET    /api/v1/cases/{case_id}             Get case details
POST   /api/v1/cases/                      Create case
PATCH  /api/v1/cases/{case_id}             Update case
DELETE /api/v1/cases/{case_id}             Delete case
```

### Document Management
```
GET    /api/v1/cases/{case_id}/documents/            List documents
POST   /api/v1/cases/{case_id}/documents/            Upload document
GET    /api/v1/cases/{case_id}/documents/{doc_id}    Get document
DELETE /api/v1/cases/{case_id}/documents/{doc_id}    Delete document
```

### AI Analysis
```
POST   /api/v1/cases/{case_id}/documents/{doc_id}/analyze
       Body: { "force_reanalyze": false }
       Response: 202 Accepted
       Purpose: Trigger background analysis

GET    /api/v1/cases/{case_id}/documents/{doc_id}/analysis
       Response: { status, extraction, analysis, entities, processing }
       Purpose: Poll for results (every 3 seconds)

POST   /api/v1/cases/{case_id}/documents/analyze-bulk
       Body: { "document_ids": [...], "force_reanalyze": false }
       Response: 202 Accepted
       Purpose: Bulk analysis

POST   /api/v1/cases/{case_id}/documents/estimate-cost
       Body: { "document_ids": [...] }
       Response: { total_documents, estimated_cost_usd, within_budget }
       Purpose: Cost estimation before analysis
```

---

## 🔄 State Machine

### Document Status Lifecycle

```
┌──────────────┐
│   uploaded   │ ◄─── Initial state after upload
└──────┬───────┘
       │ POST /analyze
       ▼
┌──────────────────┐
│   processing     │ ◄─── Background task running
└──────┬───────────┘
       │
       ├─────────────────────────────┐
       │ SUCCESS                     │ ERROR
       ▼                             ▼
┌─────────────────┐    ┌────────────────────────────┐
│ analysis_       │    │ • failed                   │
│ complete        │    │ • extraction_failed        │
└─────────────────┘    │ • poor_quality (score<0.5)│
       │               └────────────────────────────┘
       │                          │
       │                          │ User clicks "Retry"
       │                          ▼
       ▼                    (Back to processing)
   Display to user
   ├─ Summary
   ├─ Classification
   ├─ Entities
   ├─ Cost
   └─ Processing Time
```

### Status → UI Behavior Mapping

```
┌─────────────────┬──────────────────────────────────────────┐
│ Status          │ UI Display                               │
├─────────────────┼──────────────────────────────────────────┤
│ uploaded        │ "Analyze" button (purple)                │
│ processing      │ "Analyzing..." spinner (yellow)          │
│ analysis_       │ "View Analysis" button (blue)            │
│ complete        │ Results displayed                        │
│ failed          │ "Retry Analysis" button (orange)         │
│ extraction_     │ "Retry Analysis" button (orange)         │
│ failed          │                                          │
│ poor_quality    │ "Retry Analysis" button (orange)         │
│                 │ Quality score shown                      │
└─────────────────┴──────────────────────────────────────────┘
```

---

## 💰 Cost Model

### Pricing

```
┌──────────────────────────────────┬──────────────────┐
│ Model                            │ Pricing          │
├──────────────────────────────────┼──────────────────┤
│ Claude 3.5 Haiku (input)         │ $0.80 / 1M tokens│
│ Claude 3.5 Haiku (output)        │ $4.00 / 1M tokens│
│ GPT-4 Turbo (input)              │ $10.00 / 1M      │
│ GPT-4 Turbo (output)             │ $30.00 / 1M      │
└──────────────────────────────────┴──────────────────┘
```

### Budget Tracking

```
Daily Budget: $10.00 USD

Estimated Capacity:
├─ Avg cost per document: $0.005 (Claude) + $0.008 (GPT-4) = $0.013
├─ Min cost: $0.005 (Claude-only, short doc)
├─ Max cost: $0.015 (Both models, long doc)
└─ Daily volume: 667 - 2000 documents

Budget Control:
1. Check before each API call
2. Reject if daily_spent + estimated_cost > $10.00
3. Reset at midnight UTC
4. Track per-document cost
5. Display remaining budget in UI
```

### Cost Storage Location

```
In documents.document_metadata:
└─ analysis.processing.total_cost_usd → $0.0045

In events table:
└─ metadata.cost_breakdown
   ├─ claude: $0.0015
   └─ gpt4: $0.0030
```

---

## 🗄️ Database Schema

### PostgreSQL Tables

```sql
-- Cases Table
CREATE TABLE cases (
    case_id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    case_number VARCHAR(100) UNIQUE,
    status VARCHAR(20) DEFAULT 'draft',
    case_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Documents Table
CREATE TABLE documents (
    document_id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(case_id),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_type VARCHAR(50),
    file_size INTEGER,
    s3_key TEXT UNIQUE,
    s3_bucket VARCHAR(100),
    status VARCHAR(50) DEFAULT 'uploaded',
    document_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_case_id (case_id),
    INDEX idx_status (status),
    INDEX idx_metadata USING GIN (document_metadata)
);

-- Events Table (Audit)
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    metadata JSONB,
    occurred_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_aggregate_id (aggregate_id),
    INDEX idx_event_type (event_type),
    INDEX idx_occurred_at (occurred_at)
);

-- Users Table (Future)
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Embeddings Table (RAG - Future)
CREATE TABLE document_embeddings (
    embedding_id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(document_id),
    chunk_text TEXT,
    chunk_embedding vector(1536),
    chunk_index INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_document_id (document_id),
    INDEX idx_embedding USING ivfflat (chunk_embedding)
);
```

---

## 🔧 Component Details

### 1. TextExtractionService

**Purpose**: Extract text from documents

**Methods**:
```python
extract_text(file_path: str, file_type: str) -> dict
├─ Returns:
│  ├─ text: str
│  ├─ text_length: int
│  ├─ quality_score: float (0-1)
│  ├─ extraction_method: str (pdfplumber|python-docx|tesseract)
│  └─ extracted_at: ISO timestamp
```

**Supported Formats**:
- PDF → pdfplumber
- DOCX → python-docx
- DOC → python-docx
- JPG/PNG → Tesseract OCR
- TXT → Raw text

**Quality Scoring**:
```python
score = (valid_chars / total_chars) * (word_count > 10 ? 1 : 0.5)
├─ < 0.3 → poor_quality status
├─ 0.3-0.7 → acceptable
└─ > 0.7 → good
```

### 2. AIService

**Purpose**: Orchestrate Claude and GPT-4 analysis

**Mode**: STANDARD (hybrid) with FALLBACK capability

```
STANDARD MODE (OPENAI_ENABLED=true):
├─ Claude analysis (required)
│  ├─ Summary
│  ├─ Classification
│  ├─ Key points
│  └─ Confidence
└─ GPT-4 entities (optional)
   ├─ People
   ├─ Dates
   ├─ Locations
   └─ Case numbers

If GPT-4 fails:
└─ FALLBACK: Continue with Claude-only (no entities)

CLAUDE-ONLY MODE (OPENAI_ENABLED=false):
└─ Skip GPT-4 entirely
   └─ No entity extraction
   └─ Lower cost
```

**Configuration**:
```env
OPENAI_ENABLED=true          # Master switch
ANTHROPIC_API_KEY=...        # Required
OPENAI_API_KEY=...           # Required for hybrid
AI_MAX_RETRIES=3             # Retry attempts
AI_DAILY_BUDGET_USD=10.0     # Budget limit
```

### 3. S3Service

**Purpose**: Handle file operations with MinIO

**Methods**:
```python
upload_file(file_obj, s3_key, content_type) -> bool
download_file(s3_key, local_path) -> bool
delete_file(s3_key) -> bool
file_exists(s3_key) -> bool
get_file_url(s3_key, expiration=3600) -> str
```

---

## 🚀 Deployment Info

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5433/case_analysis

# Redis
REDIS_URL=redis://localhost:6379/0

# S3/MinIO
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=case-documents
S3_USE_SSL=false

# Celery (optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI Services
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
OPENAI_ENABLED=true

# AI Budget
AI_DAILY_BUDGET_USD=10.0
AI_MAX_RETRIES=3

# Text Extraction
TESSERACT_PATH=/usr/bin/tesseract
MAX_TEXT_LENGTH=100000

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### Docker Compose Services

```yaml
Services Running:
├─ postgres:15        (port 5433)
├─ redis:7-alpine     (port 6379)
├─ minio              (port 9000, 9001)
├─ backend (FastAPI)  (port 8000)
└─ frontend (React)   (port 5173)
```

### Running the System

```bash
# Terminal 1: Infrastructure
cd v1/backend
docker-compose up -d postgres redis minio

# Terminal 2: Backend
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Frontend
cd v1/frontend
npm install
npm run dev
```

---

## 📝 Database Queries

### Get Document with Analysis
```sql
SELECT
    d.document_id,
    d.filename,
    d.status,
    d.document_metadata->'analysis'->'analysis'->>'summary' as summary,
    d.document_metadata->'analysis'->'entities'->'people' as people,
    d.document_metadata->'analysis'->'processing'->>'total_cost_usd' as cost
FROM documents d
WHERE d.document_id = 'uuid-here';
```

### Get Case Analysis Summary
```sql
SELECT
    COUNT(*) as total_documents,
    SUM(CASE WHEN status='analysis_complete' THEN 1 ELSE 0 END) as analyzed,
    SUM(CASE WHEN status LIKE '%failed' THEN 1 ELSE 0 END) as failed,
    SUM((document_metadata->'analysis'->'processing'->>'total_cost_usd')::float) as total_cost
FROM documents
WHERE case_id = 'case-uuid';
```

### Get Audit Trail
```sql
SELECT event_type, event_data, occurred_at
FROM events
WHERE aggregate_id = 'document-uuid'
ORDER BY occurred_at;
```

---

## 🎯 Key Decisions

| Decision | Rationale |
|----------|-----------|
| JSONB Storage | Flexible schema, fast queries, no schema migration |
| Event Sourcing | Audit trail, debugging, compliance, analytics |
| Background Processing | Non-blocking, responsive UI |
| Hybrid AI (Claude + GPT-4) | Best of both: Claude for analysis, GPT-4 for entities |
| Daily Budget Limit | Cost control, MVP sustainability |
| Polling (vs WebSocket) | Simpler implementation, sufficient for MVP |
| PostgreSQL + MinIO | Industry standard, scalable, open-source |

---

## 📊 Monitoring & Analytics

### Key Metrics to Track

```
✓ Daily document count
✓ Average analysis time
✓ Daily AI cost
✓ Error rate by type
✓ Quality score distribution
✓ API response times
✓ Database size growth
✓ Cache hit ratio (future)
```

### Queries for Monitoring

```sql
-- Daily document count
SELECT DATE(created_at), COUNT(*)
FROM documents
GROUP BY DATE(created_at);

-- Analysis success rate
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM documents
GROUP BY status;

-- Average cost
SELECT
    AVG((document_metadata->'analysis'->'processing'->>'total_cost_usd')::float) as avg_cost,
    MAX((document_metadata->'analysis'->'processing'->>'total_cost_usd')::float) as max_cost,
    MIN((document_metadata->'analysis'->'processing'->>'total_cost_usd')::float) as min_cost
FROM documents
WHERE status='analysis_complete';
```

---

## 🔮 Future Enhancements

### Phase 2: RAG (Retrieval-Augmented Generation)
- [ ] Vector embeddings (pgvector)
- [ ] Semantic search across cases
- [ ] Cross-case document similarity
- [ ] Document chunking for long texts

### Phase 3: Advanced Analytics
- [ ] Dashboard with case insights
- [ ] Pattern detection across cases
- [ ] Trend analysis
- [ ] Report generation

### Phase 4: Scale & Production
- [ ] Kubernetes deployment
- [ ] Distributed caching (Redis Cluster)
- [ ] Database replication
- [ ] API rate limiting & auth
- [ ] Multi-tenant support

---

## 📞 Support & Documentation

**Architecture**: This document
**API Docs**: http://localhost:8000/docs (Swagger UI)
**Database**: See DATABASE_SCHEMA section
**Deployment**: See DEPLOYMENT_INFO section

---

**Last Updated**: December 31, 2025
**Maintained By**: Development Team
**Status**: ACTIVE - MVP Production
