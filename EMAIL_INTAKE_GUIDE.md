# Email Intake Integration Guide

## Overview
The Email Intake feature allows recruiters to submit resumes directly from their Outlook inbox via:
- **Power Automate** (one-click button or auto-forward)
- **Outlook Quick Step** (manual forward)
- **Direct upload** via the web UI

All methods use the same backend processing pipeline and are enterprise-safe (no Microsoft Graph API required).

---

## Quick Setup (5 minutes)

### 1. Backend Configuration

Add to `backend/.env`:
```env
# Required — generate a long random string (min 32 chars)
INGEST_SECRET=your-secret-here-change-this-value

# Optional — IMAP auto-polling (for shared mailbox monitoring)
IMAP_HOST=outlook.office365.com
IMAP_PORT=993
IMAP_USER=resumes@yourcompany.com
IMAP_PASSWORD=service-account-password
IMAP_MAILBOX=INBOX
IMAP_POLL_INTERVAL=120
```

**Generate secret:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Frontend Configuration

Add to `frontend/.env` or `frontend/.env.local`:
```env
VITE_INGEST_SECRET=<same-value-as-backend-INGEST_SECRET>
```

### 3. Restart Servers
```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm run dev
```

---

## Usage Options

### Option 1: Power Automate (Recommended)

**Best for:** Teams, scalability, enterprise compliance

**Setup:**
1. Import `backend/power_automate_flow_template.json` into Power Automate
2. Set parameters:
   - `INGEST_WEBHOOK_URL`: `https://your-backend.com/ingest/upload`
   - `INGEST_SECRET`: (same as .env)
   - `SHARED_MAILBOX`: `resumes@yourcompany.com`
3. Authorize Outlook connector
4. Enable Flow

**Recruiter experience:**
- Auto mode: BCC/forward to `resumes@...` → automatic processing
- Button mode: Select email → Power Automate → "Send to Screening" → confirm

---

### Option 2: Outlook Quick Step (Fastest)

**Best for:** Immediate rollout, no IT approvals needed

**Setup (1 minute per recruiter):**
1. Outlook Desktop → Home → Quick Steps → Create New
2. Action: Forward to `resumes@yourcompany.com`
3. Name: "Send to Screening"
4. Optional: Add keyboard shortcut (Ctrl+Shift+1)

**Recruiter experience:**
- Select email with resume → click Quick Step

---

### Option 3: Direct Upload via Web UI

**Best for:** Ad-hoc uploads, testing

**Usage:**
1. Click "📥 Email Intake" button in app header
2. Drag-drop PDF/DOCX files or click to browse
3. Files are validated and ingested immediately
4. Click "Analyze" to score against a JD

---

## Workflow

### Automatic Processing
```
Email arrives → Power Automate/IMAP detects attachment
                ↓
         POST /ingest/upload (with X-Ingest-Secret header)
                ↓
         Backend validates file type & content
                ↓
         Resume detector classifies (resume vs invoice/itinerary)
                ↓
         [ACCEPT] → Store file + metadata
         [REJECT] → Log reason, skip storage
                ↓
         If JD provided → run full analysis immediately
         If no JD → mark as "pending" (recruiter scores later)
                ↓
         Persist to data/ingest_jobs.json
                ↓
         Recruiter views in UI → clicks "Analyze" → pastes JD → scores candidate
```

### Security Features
- **Header auth:** `X-Ingest-Secret` required on all requests
- **Deduplication:** SHA-256 hash prevents duplicate ingests
- **Resume validation:** Rejects invoices, receipts, booking confirmations
- **File quarantine:** Non-resume docs are flagged, not stored
- **Audit trail:** Original email headers (From, Message-ID, Date) preserved
- **Encrypted storage:** Files saved to `uploads/ingest/` with UUID prefix

---

## API Reference

All routes require header: `X-Ingest-Secret: <your-secret>`

### `POST /ingest/upload`
Upload one resume (Power Automate webhook target)

**Form fields:**
- `file` (required): PDF or DOCX
- `recruiter_email`: sender email (optional)
- `message_id`: Outlook message ID (optional, for dedup)
- `subject`: email subject (optional)
- `job_description`: JD text for immediate analysis (optional)
- `job_id`: saved job ID (optional)

**Response:**
```json
{
  "ingest_id": "uuid",
  "filename": "John_Doe_Resume.pdf",
  "status": "analyzed|accepted|rejected|error",
  "serve_id": "uuid_filename.pdf",
  "analysis": { ... },
  "rejection_reason": "..."
}
```

### `GET /ingest/jobs?limit=100`
List ingested files (most recent first)

### `POST /ingest/analyze/{ingest_id}`
Run or re-run analysis for a previously-ingested file
- Form: `job_description` (required), `job_id` (optional)

### `DELETE /ingest/jobs/{ingest_id}`
Remove ingest record and file

---

## Troubleshooting

### "Invalid or missing X-Ingest-Secret header"
- Verify `INGEST_SECRET` is set identically in backend `.env` and frontend `.env`
- Restart both servers after changing .env

### "Ingest endpoint is not configured"
- Backend `.env` is missing `INGEST_SECRET`
- Add it and restart backend

### Power Automate Flow fails with 401
- Check `INGEST_SECRET` parameter in Flow matches backend
- Verify webhook URL includes `/ingest/upload`

### Files marked as "rejected — not a resume"
- Check if the file is actually a resume (not invoice, receipt, itinerary)
- View rejection reason in the UI table
- Test with a known-good resume PDF

### IMAP poller not working
- Check credentials: `IMAP_USER`, `IMAP_PASSWORD`
- Verify `IMAP_HOST` and port (993 for SSL)
- Check backend logs for "IMAP poller started"
- Ensure service account has read access to the mailbox

---

## Architecture Notes

**No Microsoft Graph API used:**
- Power Automate uses standard Outlook connector (V2)
- IMAP poller uses direct IMAP4 SSL protocol
- All auth happens via service account credentials or shared secrets

**Data flow:**
```
Power Automate / IMAP → Webhook → Backend Validator → Resume Detector
                                         ↓
                              uploads/ingest/ (file storage)
                                         ↓
                              data/ingest_jobs.json (metadata)
                                         ↓
                              Frontend UI (table view + analyze modal)
```

**Deduplication:**
- Files are hashed (SHA-256) on arrival
- Duplicate hash → skip storage, return existing `ingest_id`
- Message-ID also tracked for audit (optional)

**Scalability:**
- Single-file uploads: synchronous (fast)
- Batch uploads: process sequentially (up to 50 files)
- IMAP polling: configurable interval (default 120s)
- For high volume: use Power Automate push (no polling overhead)

---

## Recruiter Quick Reference

**To submit a resume:**
1. Forward email to `resumes@yourcompany.com`, OR
2. Select email → Power Automate button → "Send to Screening", OR
3. Go to web app → 📥 Email Intake → drag-drop file

**To score a resume:**
1. Open web app → 📥 Email Intake
2. Find resume in table (status: "→ Pending JD")
3. Click "Analyze"
4. Paste job description
5. Click "Run Analysis →"
6. View results in normal screening dashboard

**Statuses:**
- **✓ Analyzed** — scored against a JD, ready for decision
- **→ Pending JD** — valid resume, waiting for JD to score
- **✗ Rejected** — not a resume (see reason in table)
- **! Error** — parsing failed (contact support)

---

## Support

For issues or questions:
1. Check backend logs: `backend/` terminal output
2. Check frontend console: browser DevTools → Console
3. Verify .env values are set correctly
4. Test with a simple curl:
```bash
curl -X POST https://your-backend.com/ingest/upload \
  -H "X-Ingest-Secret: your-secret" \
  -F "file=@sample.pdf"
```

Expected: HTTP 200 with JSON `{ "ingest_id": "...", "status": "accepted", ... }`
