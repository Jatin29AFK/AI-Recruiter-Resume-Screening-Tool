# AI Resume Matcher Architecture

## 1. Purpose

This application is a recruiter-facing resume screening system with two main operating modes:

1. Standard screening: upload one or many resumes and compare them against a job description.
2. Intake-first screening: collect resumes from email or direct upload, store them safely, and analyze them immediately or later against a selected job.

At a high level, the system is a React frontend talking to a FastAPI backend. The backend performs parsing, resume detection, JD extraction, scoring, recruiter-oriented analysis, optional LLM explanation/tailoring, and lightweight JSON-file persistence.

---

## 2. System Context

```text
Recruiter / Hiring Team
        |
        v
React + Vite Frontend
        |
        v
FastAPI Backend
        |
        +--> Resume/JD analysis services
        +--> Tailoring + LLM explanation services
        +--> Email intake services
        +--> JSON data stores
        +--> Uploaded file storage
        |
        +--> Optional external systems
              - Outlook / Power Automate
              - IMAP mailbox
              - Gemini API
```

---

## 3. Primary User Journeys

### A. Batch recruiter screening

1. Recruiter uploads many resumes and provides a JD.
2. Frontend calls `POST /matcher/batch-upload`.
3. Backend parses each resume, validates it is really a resume, analyzes it against the JD, and groups candidates into `Shortlist`, `Review`, and `Reject`.
4. Recruiter works inside the dashboard to inspect candidates, adjust priorities, save notes, and update candidate stage.

### B. Single resume deep analysis

1. User uploads one resume and one JD.
2. Frontend calls `POST /matcher/upload`.
3. Backend returns a detailed analysis payload including skills, missing gaps, evidence, ATS audit, recommendation, explanation, and resume preview id.

### C. Resume tailoring

1. User analyzes a resume first.
2. Frontend calls `POST /matcher/tailor-resume`.
3. Backend builds a tailoring plan, generates a draft, validates the draft, then re-scores the tailored output against the same JD.

### D. Email intake

1. Resume arrives through Power Automate, IMAP polling, or direct upload in the intake panel.
2. Backend validates, hashes, deduplicates, classifies, stores, and optionally analyzes the file.
3. Recruiter later opens the intake panel, selects a saved target job, and bulk-analyzes pending resumes if needed.

---

## 4. Frontend Architecture

### 4.1 Frontend stack

- Framework: React
- Build tool: Vite
- API layer: `frontend/src/services/api.js`
- Main shell: `frontend/src/App.jsx`

### 4.2 Frontend structure

The frontend is a single-page application with state lifted mostly into `App.jsx`. It renders different recruiter workflows through composable panels.

Key UI areas:

- `UploadForm.jsx`
  - Multi-resume upload
  - JD text input
  - Saved job selection
  - Client-side and server-assisted resume validation

- `RecruiterDashboard.jsx`
  - Candidate list and bucket view
  - Recruiter scoring controls
  - Candidate detail panel launch
  - Candidate stage/status updates

- `IngestPanel.jsx`
  - Intake-specific upload flow
  - Polling view of ingested files
  - Saved target job selection for all new incoming resumes
  - Analyze-now / analyze-all behavior for pending records

- Deep-dive panels
  - ATS audit
  - Evidence and keyword coverage
  - Recommendation panel
  - LLM explanation panel
  - Tailored resume comparison/output panels

### 4.3 Frontend responsibilities

- Gather file and JD inputs.
- Call backend APIs with timeouts and friendly error handling.
- Maintain analysis, tailoring, comparison, and ingest UI state.
- Apply client-side UX rules like drag/drop, duplicate file prevention, and pre-validation.
- Pass the shared intake secret in `X-Ingest-Secret` for intake operations.

### 4.4 Frontend limitations

- No dedicated state manager like Redux or Zustand; state is local/component-based.
- No server-side rendering; all recruiter interactions are client-side after app load.
- Secrets for intake are present in frontend env for browser requests, which is acceptable only for internal/trusted deployments and should be revisited for stronger production security.

---

## 5. Backend Architecture

### 5.1 Backend stack

- Framework: FastAPI
- App entrypoint: `backend/app/main.py`
- Data validation: Pydantic models in `backend/app/models/schemas.py`
- Persistence: JSON files under `backend/data/`
- File storage: `uploads/` and `uploads/ingest/`

### 5.2 API route modules

- `matcher.py`
  - Main screening APIs
  - Resume preview/download
  - Batch analysis
  - Candidate status tracking

- `jobs.py`
  - CRUD for saved job descriptions

- `notes.py`
  - CRUD for recruiter notes

- `ingest.py`
  - Email/direct intake APIs
  - Target job selection for intake
  - Ingest job listing, re-analysis, deletion

### 5.3 Backend startup lifecycle

FastAPI starts with a lifespan hook that:

1. Loads environment variables.
2. Starts the optional IMAP poller if IMAP settings exist.
3. Stops the poller on shutdown.

This makes intake polling part of backend runtime rather than a separate worker process.

---

## 6. Core Analysis Engine

The core business value of the app lives in `backend/app/services/analyzer.py`.

### 6.1 Analysis pipeline

For a resume + JD pair, the backend performs roughly this pipeline:

```text
Resume file
  -> text extraction
  -> resume/non-resume detection
  -> section parsing
  -> text cleaning + lemmatization
  -> domain detection
  -> resume skill extraction
  -> JD parsing
  -> exact/fuzzy/semantic matching
  -> evidence validation
  -> experience estimation
  -> scoring
  -> ATS audit
  -> keyword coverage
  -> shortlist simulation
  -> recommendation engine
  -> optional LLM explanation
```

### 6.2 Main service groups

- Parsing and normalization
  - `parser.py`
  - `preprocess.py`
  - `section_parser.py`
  - `resume_structurer.py`

- Resume and JD understanding
  - `resume_detector.py`
  - `jd_parser.py`
  - `domain_detector.py`
  - `extractor.py`

- Matching and scoring
  - `matcher_engine.py`
  - `experience_estimator.py`
  - `evidence_validator.py`
  - `scorer.py`
  - `decision_policy.py`

- Recruiter-facing interpretation
  - `recommendation_engine.py`
  - `shortlist_simulator.py`
  - `ats_auditor.py`
  - `keyword_coverage.py`
  - `career_analyzer.py`
  - `cert_coverage_analyzer.py`
  - `non_negotiable_evaluator.py`

- Tailoring
  - `tailor_service.py`
  - `tailor_planner.py`
  - `tailor_validator.py`
  - `llm/resume_tailor_llm.py`

### 6.3 Output shape

The analysis response is intentionally rich, not just a score. It includes:

- raw and structured resume data
- JD requirements
- matched and missing skills
- critical gaps
- experience estimate and fit
- evidence strength
- ATS audit results
- keyword coverage
- recruiter recommendation
- shortlist simulation
- optional LLM explanation
- optional certification coverage

This supports both automated ranking and human review.

---

## 7. LLM Architecture

LLM use is supportive, not foundational.

### 7.1 Current provider strategy

- Provider selector: `backend/app/services/llm/llm_service.py`
- Supported providers:
  - `mock`
  - `gemini`

### 7.2 LLM usage points

- Explanation generation for analysis results
- Resume tailoring draft generation

### 7.3 Reliability model

- Core analysis can run without a live LLM.
- If explanation generation fails, the system falls back to mock behavior.
- This keeps screening usable even if Gemini is unavailable.

---

## 8. Data and Storage Architecture

### 8.1 File storage

- `uploads/`
  - Main uploaded resumes used in direct screening flows

- `backend/uploads/ingest/` logically represented by `INGEST_UPLOAD_DIR`
  - Intake-specific stored files

Stored filenames are UUID-prefixed to avoid collisions and reduce trust in user-provided names.

### 8.2 JSON persistence

The app currently uses file-based persistence instead of a database.

Main files:

- `backend/data/jobs.json`
  - Saved job descriptions

- `backend/data/recruiter_notes.json`
  - Candidate notes

- `backend/data/candidate_statuses.json`
  - Hiring stage/status history

- `backend/data/ingest_jobs.json`
  - Intake records and intake analysis payloads

- `backend/data/ingest_settings.json`
  - Active target job id for intake

### 8.3 Persistence characteristics

- Writes are atomic or near-atomic through temp-file replacement.
- In-process threading locks protect concurrent writes.
- Storage is simple and easy to demo, but not ideal for multi-instance deployment.

### 8.4 Consequences of current storage design

Pros:

- Very easy local setup
- No database dependency
- Easy to inspect and debug data

Tradeoffs:

- No relational consistency guarantees
- Weak concurrency story across multiple backend instances
- Large analysis payloads can make JSON files grow quickly
- Search/filter/reporting capabilities are limited

---

## 9. API Surface by Domain

### 9.1 Screening APIs

- `POST /matcher/upload`
- `POST /matcher/batch-upload`
- `POST /matcher/compare-jds`
- `POST /matcher/tailor-resume`
- `POST /matcher/validate-resume-file`
- `POST /matcher/extract-jd-from-url`
- `GET /matcher/resume/{serve_id}`
- `GET /matcher/resume/{serve_id}/preview`

### 9.2 Intake APIs

- `POST /ingest/upload`
- `POST /ingest/upload-base64`
- `POST /ingest/batch-upload`
- `GET /ingest/jobs`
- `GET /ingest/jobs/{ingest_id}`
- `GET /ingest/target-job`
- `PUT /ingest/target-job`
- `POST /ingest/analyze/{ingest_id}`
- `DELETE /ingest/jobs/{ingest_id}`

### 9.3 Recruiter workflow APIs

- `POST /jobs/`
- `GET /jobs/`
- `GET /jobs/{job_id}`
- `PUT /jobs/{job_id}`
- `DELETE /jobs/{job_id}`
- `POST /jobs/{job_id}/clone`

- `POST /notes/`
- `GET /notes/candidate/{candidate_id}`
- `PUT /notes/{note_id}`
- `DELETE /notes/{note_id}`

- `POST /matcher/candidate/status`
- `GET /matcher/candidate/{candidate_id}/status`
- `POST /matcher/candidate/statuses`

---

## 10. Email Intake Architecture

This is the most distinctive subsystem in the app.

### 10.1 Design goal

Accept resumes from enterprise email workflows without requiring Microsoft Graph API, while keeping recruiter operations simple.

### 10.2 Intake entry channels

The intake subsystem supports three channels:

1. Power Automate webhook
   - Standard multipart upload to `POST /ingest/upload`
   - JSON base64 upload to `POST /ingest/upload-base64`

2. IMAP polling
   - Background poller logs into a mailbox, checks unseen messages, extracts attachments, and passes them into the same `process_file()` path

3. Direct browser upload
   - Recruiter uses the intake panel in the web app

All three converge into the same backend service: `backend/app/services/email_ingest.py`.

### 10.3 Intake processing pipeline

```text
Attachment or uploaded file
  -> extension validation
  -> save to intake storage
  -> SHA-256 hash
  -> duplicate check
  -> resume text extraction
  -> resume-vs-non-resume detection
  -> optional immediate analysis using target job or supplied JD
  -> persist ingest record
  -> expose through intake UI
```

### 10.4 Intake record lifecycle

Each intake record receives an `ingest_id` and is stored with:

- file identity
- source channel
- recruiter/sender metadata
- status
- rejection reason if any
- file hash
- saved analysis result if performed
- linked target job id
- created timestamp

### 10.5 Intake statuses

- `accepted`
  - File is valid and stored, but not yet analyzed against a JD

- `analyzed`
  - File was scored successfully against a JD

- `rejected`
  - File type or content failed validation

- `error`
  - Parse, storage, or analysis execution failed

### 10.6 Target job model

Email intake introduces a useful operational abstraction: an active target job.

- Stored in `backend/data/ingest_settings.json`
- Selected through `GET/PUT /ingest/target-job`
- Used by new intake files when no explicit JD is passed
- Allows incoming resumes to be auto-scored for the current open role

This is the bridge between passive intake and active screening.

### 10.7 Deduplication model

- File bytes are hashed with SHA-256 after storage.
- Existing intake jobs are scanned for the same hash.
- Duplicate uploads are skipped and linked back to the original record.

This works well for exact duplicate documents, though it does not catch semantically identical files with different formatting.

### 10.8 Authentication model

All intake routes require:

```text
X-Ingest-Secret: <shared-secret>
```

The backend checks this against `INGEST_SECRET`.

This is simple and practical for internal automation, but it is a shared-secret model rather than user-level authentication.

### 10.9 IMAP poller runtime model

The IMAP poller:

- starts during FastAPI app startup
- runs in a background thread
- polls mailbox at configured intervals
- fetches unseen messages
- extracts eligible attachments
- feeds them into `process_file()`

Important architectural implication:

- intake polling is coupled to API server lifetime
- if you scale to multiple backend instances, you risk duplicate polling unless you isolate the poller into one worker or move it into a dedicated service

### 10.10 Intake UI behavior

The frontend `IngestPanel.jsx` acts like an operational queue:

- shows recent intake jobs
- refreshes automatically on an interval
- lets recruiters set/clear the target job
- uploads files directly
- allows analyze-all for pending candidates
- reuses the regular candidate detail view for analyzed intake records

This is a nice example of the system treating intake as a feeder into the same downstream review experience.

### 10.11 Email intake sequence flows

#### Flow A: immediate scoring

```text
Outlook/Power Automate
  -> /ingest/upload
  -> process_file()
  -> resolve active target job
  -> analyze_resume_against_jd()
  -> persist analyzed job
  -> recruiter sees scored candidate in intake UI
```

#### Flow B: store now, score later

```text
Email or direct upload
  -> /ingest/upload
  -> process_file()
  -> accepted status only
  -> recruiter later selects job and clicks analyze
  -> /ingest/analyze/{id}
  -> persist analyzed result
```

#### Flow C: background mailbox sweep

```text
IMAP poller thread
  -> unseen mailbox messages
  -> attachment extraction
  -> process_file()
  -> same persistence and analysis behavior as webhook uploads
```

### 10.12 Operational strengths

- No Graph API dependency
- One shared ingestion pipeline across channels
- Clear audit trail fields
- Easy to demo and operate
- Immediate or deferred analysis supported

### 10.13 Operational risks

- Shared secret is coarse-grained
- Browser-side possession of intake secret is not ideal
- File-backed storage will become fragile at higher intake volumes
- IMAP polling inside the API process is hard to scale horizontally
- Deduplication is exact-file only
- Large stored analysis payloads may bloat `ingest_jobs.json`

---

## 11. Cross-Cutting Concerns

### 11.1 Security

Current protections:

- file extension checks
- resume-vs-non-resume classification
- safe filename generation
- path traversal guards on file serving
- intake shared-secret header
- CORS allowlist support

Areas to improve later:

- real authentication and role-based access
- signed upload or service-to-service auth for intake
- encrypted secrets management
- antivirus/malware scanning for uploads
- rate limiting and request audit logging

### 11.2 Observability

Current observability is mostly log-based plus persisted JSON state.

Gaps:

- no metrics backend
- no structured tracing
- no job retry queue
- no admin monitoring dashboard

### 11.3 Scalability

The architecture is best suited today for:

- local use
- demo environments
- low-to-moderate internal team usage

To scale further, the biggest architectural migration would be:

1. move JSON stores to a database
2. move IMAP polling and heavy analysis into background workers
3. separate object storage from local disk
4. add authentication and event logging

---

## 12. Suggested Future Architecture Evolution

### Phase 1: production-hardening

- Replace JSON stores with Postgres
- Replace local file storage with S3/GCS/Azure Blob
- Move IMAP poller to a dedicated worker
- Add proper auth for recruiters and automation clients

### Phase 2: workflow scaling

- Add queue-backed analysis jobs
- Add retry/dead-letter handling for bad files
- Store normalized candidate/job entities
- Add analytics for funnel conversion and screening quality

### Phase 3: intelligence scaling

- Improve deduplication beyond exact hash
- Add entity extraction for employer, title, tenure, education normalization
- Add feedback loops from recruiter decisions back into ranking models

---

## 13. Recommended Deep-Dive Topics for Later

If we want to go deeper next, the best follow-up documents would be:

1. Email Intake Deep Dive
   - exact Power Automate payload contracts
   - IMAP polling state machine
   - duplicate handling and audit semantics
   - security redesign options

2. Analysis Engine Deep Dive
   - scoring math
   - rule ordering
   - domain-specific extraction behavior
   - recruiter recommendation logic

3. Data Model Deep Dive
   - how to migrate from JSON files to a relational schema

4. Deployment Architecture
   - local, single-server, and production target topologies

---

## 14. Summary

This app is architected as a recruiter workflow platform rather than just a resume parser. Its strongest pattern is a shared analysis core reused across:

- single resume review
- batch screening
- resume tailoring
- email/direct intake

The current design is pragmatic and product-oriented:

- React frontend for recruiter workflows
- FastAPI backend for orchestration and analysis
- modular service layer for screening logic
- JSON/disk persistence for simplicity
- a distinctive email intake subsystem that can ingest first and score later

The next major architectural decision point will be whether the app remains a powerful internal tool or evolves into a production multi-user platform. That choice mainly affects storage, authentication, background processing, and intake security.
