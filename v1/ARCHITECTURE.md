# Case Analysis System - MVP Implementation Plan

## 1. CORE ARCHITECTURAL PRINCIPLES

### Event Sourcing + CQRS (Simplified)

**Why This Architecture:**
- **Audit Trail:** Every action stored as immutable event (critical for legal)
- **Provenance:** Every fact/conclusion traces to exact source location
- **History:** Can reconstruct any state at any time
- **Future-Proof:** Easy to add features without rewrites

**How It Works:**
```
User Action → Command → Event (stored) → Update Read Models → UI Updates
```

**Key Principle:** Write = Events (append-only), Read = Optimized views for queries

---

## 2. TECHNOLOGY STACK

### Backend
- **Python 3.11+** - Best AI ecosystem
- **FastAPI** - Modern async API framework
- **PostgreSQL 15+** - Database (events + read models)
- **Pgvector** - Vector search extension
- **Redis** - Cache + task queue broker
- **Celery** - Background job processing
- **LangChain** - AI orchestration framework

### AI
- **Claude 3.5 Sonnet** - Document analysis & chat
- **OpenAI Embeddings** - text-embedding-3-small (for RAG)

### Frontend
- **React 18 + TypeScript** - Type-safe UI
- **Vite** - Build tool
- **shadcn/ui** - Component library
- **Tailwind CSS** - Styling
- **TanStack Query** - Server state management
- **react-pdf** - PDF viewer

### Storage & Infrastructure
- **MinIO or S3** - Document storage
- **Docker Compose** - Local development & deployment

---

## 3. DATA MODEL (ESSENTIAL TABLES)

### Event Store
```sql
events (
    event_id, aggregate_type, aggregate_id, event_type,
    event_data JSONB, metadata JSONB, created_at, sequence_number
)
```

### Read Models
```sql
cases (case_id, title, case_number, status, metadata, timestamps)

documents (document_id, case_id, filename, file_path, status, timestamps)

facts (
    fact_id, case_id, document_id, content, fact_type,
    source_page, source_paragraph, source_text,
    confidence, extracted_by, ai_model_version, timestamps
)

entities (entity_id, document_id, entity_type, entity_value, source_location, confidence)

timeline_events (event_id, case_id, document_id, event_date, description, source_fact_id)

document_chunks (chunk_id, document_id, content, page_number, embedding VECTOR(1536))

chat_sessions (session_id, case_id, created_at)

chat_messages (message_id, session_id, role, content, citations JSONB)

edit_history (edit_id, entity_type, entity_id, old_value, new_value, edited_by, reason)
```

**Key Design:** Every extracted fact has `source_page`, `source_paragraph`, `source_text` for provenance.

---

## 4. IMPLEMENTATION PHASES

### PHASE 1: Foundation (Week 1-2)

**Setup:**
- Backend: FastAPI project with Poetry
- Frontend: React + TypeScript with Vite
- Docker Compose: PostgreSQL, Redis, MinIO, API, Frontend
- Database: Create schema with Alembic migrations
- Event sourcing framework (basic)

**Deliverable:** `docker-compose up` runs everything, basic API works

---

### PHASE 2: Core UI (Week 2)

**Build 2 Screens:**

**Screen 1: Cases List (`/`)**
- Table of cases
- "New Case" button
- Click row → Navigate to case dashboard

**Screen 2: Case Dashboard (`/cases/:caseId`)**
- Case header (title, number, metadata)
- **6 Module Cards (Grid):**
  1. Documents
  2. Case Summary
  3. Chat
  4. Timeline
  5. Conflicts
  6. Settings

**API Endpoints:**
- `POST /cases`
- `GET /cases`
- `GET /cases/{id}`

**Deliverable:** Working case management UI with module navigation structure

---

### PHASE 3: Documents Module (Week 3-6)

**Most important module - build completely:**

**Week 3: Upload & Storage**
- Upload UI (drag & drop)
- Store in MinIO/S3
- Document list in sidebar
- API: `POST /cases/{id}/documents/upload`

**Week 4: Text Extraction**
- PDF extraction (pdfplumber)
- DOCX extraction (python-docx)
- Track positions (page, paragraph)
- Chunking for embeddings
- Celery background processing
- Status tracking: uploading → processing → analyzed
- API: `GET /documents/{id}/status`

**Week 5: AI Analysis**
- Claude integration
- Pydantic schemas: DocumentSummary, ExtractedFact, Entity, TimelineEvent
- Prompt engineering for citations
- Store: facts, entities, timeline_events
- Generate embeddings (OpenAI)
- Store chunks with vectors (pgvector)
- API: `GET /documents/{id}/analysis`, `GET /documents/{id}/facts`

**Week 6: Document Viewer UI**
- Split screen: PDF (60%) + Analysis Panel (40%)
- PDF rendering (react-pdf)
- Analysis tabs: Summary, Facts, Timeline, Entities
- Click fact → Highlight in PDF
- Edit fact modal
- Add fact manually
- Citation linking

**Deliverable:** Complete document workflow from upload to viewing/editing with full AI analysis

---

### PHASE 4: Case Summary Module (Week 7)

**Features:**
- Synthesize all document summaries into case summary
- Stats: # docs, # facts, # entities
- "Regenerate Summary" button
- API: `GET /cases/{id}/summary`, `POST /cases/{id}/summary/regenerate`

**Deliverable:** Case-level overview combining all documents

---

### PHASE 5: Timeline Module (Week 7)

**Features:**
- Merged timeline from all documents (sorted by date)
- Each event: date, description, source link, citation
- Filter by document, date range
- Click citation → Jump to PDF location
- API: `GET /cases/{id}/timeline`

**Deliverable:** Chronological view across entire case

---

### PHASE 6: Conflicts Module (Week 8)

**Features:**
- Detect conflicts:
  - Same event, different dates
  - Contradictory facts
  - Entity mismatches
- List view with side-by-side comparison
- Link to source locations
- "Mark as Reviewed" button
- API: `GET /cases/{id}/conflicts`, `POST /cases/{id}/conflicts/{id}/resolve`

**Deliverable:** Automated conflict detection with review UI

---

### PHASE 7: Chat Module (Week 8-9)

**Week 8: Backend (RAG Pipeline)**
- Similarity search (pgvector)
- Retrieval: Question → Embed → Search top 10 chunks → Build context
- Claude with strict grounding prompt
- WebSocket for real-time streaming
- Store chat history
- API: `WS /cases/{id}/chat`, `GET /cases/{id}/chat/history`

**Week 9: Frontend (Chat UI)**
- Chat interface (messages + input)
- Streaming responses
- Citation links (clickable → open PDF)
- Handle "I don't know" gracefully
- Multi-turn conversation support

**Deliverable:** Working RAG chat with grounded responses and citations

---

### PHASE 8: Polish (Week 10)

**Features:**
- Edit case metadata
- Delete case
- Reprocess document
- View edit history
- Basic authentication (JWT)
- Loading states everywhere
- Error handling
- Responsive design (basic)

**Deliverable:** Production-ready MVP

---

### PHASE 9: Testing (Week 11-12)

- Unit tests (business logic)
- Integration tests (API endpoints)
- E2E tests (user workflows)
- Bug fixes
- Basic documentation

**Deliverable:** Tested, deployable MVP

---

## 5. CORE IMPLEMENTATION PATTERNS

### Pattern 1: Provenance Chain

Every extracted fact MUST have:
```python
@dataclass
class ExtractedFact:
    fact_id: UUID
    content: str
    source_page: int
    source_paragraph: int
    source_text: str        # Exact quote
    confidence: float
    extracted_by: str       # 'ai' or 'user'
    ai_model_version: str   # e.g., 'claude-3-5-sonnet-20241022'
```

### Pattern 2: Event-Driven Processing

```python
# User uploads document
→ Event: DocumentUploaded
→ Trigger: Extract text (Celery task)
→ Event: TextExtracted
→ Trigger: Generate embeddings
→ Event: EmbeddingsGenerated
→ Trigger: AI analysis
→ Event: FactExtracted (for each fact)
→ Event: AnalysisCompleted
→ Update read models
```

### Pattern 3: Citation Validation

Before storing AI-extracted fact:
```python
def validate_citation(fact, document):
    # Check that page/paragraph actually exists
    # Verify source_text is in document
    # If invalid → flag for human review
    if not citation_exists:
        fact.requires_human_review = True
        fact.confidence = 0.0
```

### Pattern 4: Grounded Chat (RAG)

```python
def chat(question, case_id):
    # 1. Retrieve context
    chunks = vector_search(embed(question), case_id=case_id, k=10)

    # 2. Build prompt
    prompt = f"""Answer based ONLY on context below.
    Include citation numbers. If not in context, say 'I don't have information.'

    Context: {chunks}
    Question: {question}"""

    # 3. LLM with temperature=0
    response = claude(prompt, temperature=0)

    # 4. Log as event
    store_event(ChatInteraction(...))

    return response
```

---

## 6. KEY PRINCIPLES TO MAINTAIN

✅ **Strict Provenance** - Every fact links to exact source
✅ **Determinism** - Same input → Same output (temperature=0, version locking)
✅ **AI as Assistant** - Never authoritative, always verifiable
✅ **Audit Trail** - Every change tracked as event
✅ **Manual Override** - User can always edit/correct AI
✅ **No Hallucination** - RAG ensures answers grounded in documents

---

## 7. PROJECT STRUCTURE

```
project-root/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── domain/       # Aggregates, commands, events
│   │   ├── events/       # Event store
│   │   ├── db/           # SQLAlchemy models, migrations
│   │   ├── services/     # AI service, document processor
│   │   └── config.py
│   ├── tests/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── pyproject.toml    # Poetry dependencies
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/        # Cases list, case dashboard, modules
│   │   ├── components/   # Reusable UI components
│   │   ├── api/          # API client
│   │   ├── types/        # TypeScript interfaces
│   │   ├── hooks/        # Custom React hooks
│   │   └── App.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── README.md
```

---

## 8. MODULE SUMMARY

| Module | What It Does | Key Features |
|--------|-------------|--------------|
| **Documents** | Individual doc analysis | Upload, extract text, AI analysis, viewer, editing |
| **Case Summary** | Multi-doc synthesis | Consolidated summary, stats, cross-doc facts |
| **Timeline** | Chronological view | Merged events from all docs, filterable |
| **Conflicts** | Detect contradictions | Auto-detect, side-by-side comparison |
| **Chat** | Interactive Q&A | RAG-based, grounded in docs, citations |
| **Settings** | Case management | Edit metadata, reprocess, audit log |

---

## 9. DEVELOPMENT WORKFLOW

### Start with Foundation
1. Set up Docker Compose
2. Create database schema
3. Build basic event store
4. Create case CRUD API
5. Build cases list UI

### Then Build Modules One-by-One
- Focus on **Documents** first (most complex, most valuable)
- Then add other modules incrementally
- Each module = standalone feature

### Key Rule
**Don't build everything at once.** Complete one module fully before starting the next. This keeps progress visible and testable.

---

## 10. WHAT MAKES THIS ARCHITECTURE GOOD FOR YOUR CASE

**For Legal Domain:**
- Full audit trail (every change tracked)
- Provenance (every fact → exact source)
- Reproducibility (event replay)
- Manual override (AI assists, human decides)

**For Future Scale:**
- Event sourcing = easy to add features (just add new events)
- CQRS = read/write scale independently
- Modular = can extract microservices later
- Same core architecture works at any scale

**For MVP Speed:**
- Monolithic API (simple deployment)
- Single database (PostgreSQL does everything)
- No microservices complexity
- Start coding immediately

---

## 11. IMPLEMENTATION PHASES (DETAILED)

### PHASE 1: Foundation (Week 1-2)
**Goal:** Infrastructure running locally

**Tasks:**
- Initialize backend (Poetry, FastAPI, Docker)
- Initialize frontend (Vite, React, TypeScript)
- Docker Compose (PostgreSQL + pgvector, Redis, MinIO)
- Database schema (events, cases tables)
- Basic event store (append events, read events)
- API: Create case, list cases, get case
- UI: Cases list, create case modal

**Done When:** Can create and list cases via web UI

---

### PHASE 2: Documents Module - Upload & Processing (Week 3-4)

**Tasks:**
- Document upload API endpoint
- File storage (MinIO/S3)
- PDF text extraction (pdfplumber)
- DOCX extraction (python-docx)
- Position tracking (page, paragraph)
- Document chunking (preserve metadata)
- Celery tasks (async processing)
- Embedding generation (OpenAI API)
- Store chunks with vectors (pgvector)
- Document list UI (in case dashboard)
- Upload UI (drag & drop)
- Status indicators

**Done When:** Upload PDF → Extracted text with positions → Chunks embedded

---

### PHASE 3: Documents Module - AI Analysis (Week 5-6)

**Tasks:**
- Anthropic Claude integration
- Pydantic schemas: ExtractedFact, Entity, TimelineEvent, DocumentSummary
- Prompt engineering (extract facts with citations)
- Citation validation (check locations exist)
- Confidence scoring
- Store: facts, entities, timeline_events, document_analyses tables
- API endpoints: `/documents/{id}/analysis`, `/documents/{id}/facts`
- Events: DocumentAnalysisStarted, FactExtracted, AnalysisCompleted

**Done When:** Upload PDF → AI extracts facts with page/paragraph citations → Stored in DB

---

### PHASE 4: Documents Module - Viewer & Editing (Week 6)

**Tasks:**
- Document viewer page (split screen)
- PDF rendering (react-pdf)
- Analysis panel (tabs: Summary, Facts, Timeline, Entities)
- Click fact → Highlight location in PDF
- Edit fact modal (inline editing)
- Add fact manually
- Delete fact
- Reprocess document button
- Edit history tracking

**Done When:** Can view PDF, see AI analysis, edit facts, all changes tracked

---

### PHASE 5: Case Summary Module (Week 7)

**Tasks:**
- Synthesize multiple document summaries (AI)
- Case-level summary generation
- Stats aggregation (# docs, # facts, # entities)
- API: `/cases/{id}/summary`
- UI: Case summary page
- Regenerate button

**Done When:** Case dashboard shows summary combining all uploaded documents

---

### PHASE 6: Timeline Module (Week 7)

**Tasks:**
- Merge timelines from all documents
- Sort chronologically
- API: `/cases/{id}/timeline`
- UI: Timeline page (list view)
- Each event: date, description, source doc, citation link
- Filter by document, date range
- Click citation → Open PDF at location

**Done When:** See all events across case in chronological order

---

### PHASE 7: Conflicts Module (Week 8)

**Tasks:**
- Conflict detection logic:
  - Same event, different dates
  - Contradictory facts
  - Entity mismatches
- Store conflicts
- API: `/cases/{id}/conflicts`
- UI: Conflicts page
- Side-by-side comparison
- Mark as reviewed
- Resolution notes

**Done When:** System detects and displays contradictions across documents

---

### PHASE 8: Chat Module (Week 8-9)

**Week 8 - Backend:**
- RAG pipeline: embed question → similarity search (pgvector) → retrieve chunks
- Context building with citations
- Claude prompt (strict grounding)
- WebSocket endpoint for streaming
- Store chat history
- API: `WS /cases/{id}/chat`

**Week 9 - Frontend:**
- Chat UI (messages list + input)
- Streaming responses
- Citation rendering (clickable pills)
- Multi-turn conversation
- Chat history
- Switch case-level / document-level chat

**Done When:** Can ask questions, get grounded answers with citations

---

### PHASE 9: Settings & Polish (Week 10)

**Tasks:**
- Edit case metadata
- Archive/delete case
- Audit log viewer
- Loading states
- Error handling
- Empty states
- Basic JWT authentication
- Input validation
- Responsive design (basic)

**Done When:** MVP is polished and production-ready

---

### PHASE 10: Testing (Week 11-12)

**Tasks:**
- Unit tests (core logic)
- Integration tests (API)
- E2E tests (user flows)
- Load testing (basic)
- Bug fixes
- Documentation (setup guide, user guide)

**Done When:** Tested and documented MVP ready for users

---

## 12. SCREEN DETAILS

### Cases List Screen
- Header: App logo, search, user menu
- Main: Table (case number, title, # docs, status, last updated)
- Actions: New case button, search, filters
- Click row → Case dashboard

### Case Dashboard Screen
- Header: Case title, case number, dates, status
- Main: 6 module cards in grid (2x3)
- Each card shows: Icon, title, summary stat, "View" button
- Click card → Opens that module

### Documents Module Screens

**1. Document List (Sidebar)**
- List of documents with status icons
- Upload button at top
- Click doc → Opens viewer

**2. Document Viewer (Main Screen)**
- Left (60%): PDF with controls (zoom, page nav)
- Right (40%): Analysis panel (tabbed)
  - Summary tab
  - Facts tab (list with edit buttons)
  - Timeline tab
  - Entities tab (grouped by type)

**3. Edit Fact Modal**
- Fields: content, type, page, paragraph, confidence, notes
- Save/cancel buttons

### Case Summary Screen
- Case summary text (AI-generated)
- Stats cards: # docs, # facts, # entities, # conflicts
- Regenerate button
- Last updated timestamp

### Timeline Screen
- Vertical timeline (chronological)
- Each entry: date, description, source doc badge, citation link
- Filters: date range, document selector

### Conflicts Screen
- List of conflicts
- Each item: description, affected documents, side-by-side view
- Actions: view sources, mark reviewed, add notes

### Chat Screen
- Message list (scrollable)
- User messages (right, blue)
- AI messages (left, gray) with citation pills
- Input box (bottom)
- Sample questions (when empty)

---

## 13. AI INTEGRATION GUIDELINES

### For Document Analysis

**Prompt Structure:**
```
Extract facts from this legal document.

Requirements:
- Include exact page and paragraph number for EVERY fact
- Quote the exact text from document
- Provide confidence score (0.0-1.0)

Output JSON with schema:
{
  "facts": [
    {
      "content": "Contract signed on March 15, 2024",
      "page": 7,
      "paragraph": 3,
      "source_text": "...signed this 15th day of March 2024...",
      "confidence": 0.95
    }
  ]
}
```

**Critical:**
- **Temperature = 0** (deterministic)
- **Lock model version** (store in metadata)
- **Validate citations** (check page/paragraph exists)
- **Flag low confidence** (< 0.8 → human review)

### For Chat (RAG)

**Prompt Structure:**
```
Answer based ONLY on the context below from analyzed legal documents.
Include citation numbers [1], [2] for every claim.
If information is NOT in context, respond: "I don't have information about that in the analyzed documents."

Context:
[Retrieved chunks with source metadata]

Question: {user_question}
```

**Critical:**
- **Always retrieve first** (never answer from memory)
- **Include source metadata** in retrieved chunks
- **Validate citations** before returning
- **Log entire interaction** as event

---

## 14. DATABASE SCHEMA (CRITICAL FIELDS)

**Key Pattern:** Everything links back to source

```
facts table:
- fact_id (PK)
- case_id (FK) → Which case
- document_id (FK) → Which document
- content → The extracted fact
- source_page → Page number in PDF
- source_paragraph → Paragraph index
- source_text → Exact quote from document
- confidence → 0.0 to 1.0
- extracted_by → 'ai' or 'user'
- ai_model_version → e.g., 'claude-3-5-sonnet-20241022'
- created_at, updated_at
- created_by → user_id

Indexes:
- idx_facts_case (case_id)
- idx_facts_document (document_id)
```

**Same pattern** for entities, timeline_events.

**Chat messages:**
```
chat_messages:
- message_id, session_id, role ('user'/'assistant')
- content
- citations JSONB → [{"document_id": "...", "page": 5, "paragraph": 3}]
- created_at
```

---

## 15. NEXT STEPS TO START

1. **Create project folders** (backend/, frontend/)
2. **Backend:** `poetry init`, install FastAPI, create main.py
3. **Frontend:** `npm create vite@latest`, install dependencies
4. **Docker Compose:** PostgreSQL, Redis, MinIO services
5. **First endpoint:** `POST /cases` (create case)
6. **First UI:** Cases list page
7. **Test:** Create case via UI → See in database

Then proceed phase by phase as outlined above.

---

## SUMMARY

**Architecture:** Event Sourcing + CQRS (simplified for MVP)
**Stack:** Python + FastAPI + PostgreSQL + React + Vite
**AI:** Claude 3.5 Sonnet + OpenAI Embeddings
**Deployment:** Docker Compose
**Timeline:** 12 weeks
**Phases:** 10 clear phases, module-by-module

**Core Value:** Legal document analysis with full provenance, AI-assisted but human-controlled, auditable and deterministic.
