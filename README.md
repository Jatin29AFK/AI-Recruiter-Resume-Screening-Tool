# AI Resume Matcher — Email Intake Feature

## What's New

✨ **Email-based resume intake** is now available! Recruiters can:
- Forward resumes from Outlook directly to the screening system
- Use a one-click Power Automate button
- Upload files via drag-and-drop in the web UI

All methods work without Microsoft Graph API and are enterprise-compliant.

---

## Quick Start

### 1. Configure Backend
```bash
cd backend

# Copy example and edit
cp .env.example .env

# Generate a secret
python3 -c "import secrets; print('INGEST_SECRET=' + secrets.token_urlsafe(32))"

# Add the printed value to .env
# INGEST_SECRET=<your-generated-secret>
```

### 2. Configure Frontend
```bash
cd frontend

# Copy example and edit
cp .env.example .env.local

# Add same secret as backend
# VITE_INGEST_SECRET=<same-value-as-backend>
```

### 3. Start Servers
```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 4. Test It
```bash
# Use the test script
cd backend
export INGEST_SECRET='your-secret-from-env'
python3 test_ingest.py path/to/sample-resume.pdf

# Or use the web UI
# Open http://localhost:5173
# Click "📥 Email Intake" button
# Drag-drop a resume file
```

---

## Features

### For Recruiters
- **One-click submission** via Outlook Quick Step or Power Automate button
- **Automatic validation** — invoices and non-resume files are rejected
- **Batch processing** — upload multiple resumes at once
- **Pending queue** — ingest now, score later when you have the JD
- **Status tracking** — see which resumes are analyzed, pending, or rejected
- **Deduplication** — same file won't be processed twice

### For IT/Admins
- **No Graph API** — uses standard Outlook connectors and IMAP
- **Enterprise-safe** — all traffic authenticated via shared secret
- **Audit trail** — original email headers and sender preserved
- **IMAP auto-polling** — optional background thread for shared mailbox
- **Flexible deployment** — webhook (push) or IMAP (pull) modes

---

## Documentation

📘 **[Full Setup Guide](./EMAIL_INTAKE_GUIDE.md)** — Step-by-step instructions for:
- Power Automate Flow setup
- Outlook Quick Step configuration
- IMAP polling setup
- Troubleshooting

🏗️ **[Architecture Guide](./ARCHITECTURE.md)** — End-to-end application architecture covering:
- frontend and backend structure
- analysis pipeline
- persistence model
- email intake design

📄 **[Power Automate Template](./backend/power_automate_flow_template.json)** — Ready-to-import Flow

🧪 **[Test Script](./backend/test_ingest.py)** — Verify your setup works

---

## Architecture

```
Recruiter's Outlook
        ↓
Power Automate / IMAP / Direct Upload
        ↓
POST /ingest/upload (X-Ingest-Secret header)
        ↓
Backend validates → Resume detector → Storage
        ↓
data/ingest_jobs.json (metadata)
uploads/ingest/ (files)
        ↓
Frontend UI → "📥 Email Intake" panel
        ↓
Recruiter clicks "Analyze" → pastes JD → scores candidate
```

**Security:**
- Header-based authentication (`X-Ingest-Secret`)
- SHA-256 file deduplication
- Resume content validation (blocks invoices, receipts, etc.)
- Encrypted file storage with UUID prefixes

---

## API Endpoints

All require header: `X-Ingest-Secret: <your-secret>`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ingest/upload` | POST | Upload one resume (webhook target) |
| `/ingest/batch-upload` | POST | Upload multiple resumes |
| `/ingest/jobs` | GET | List ingested files |
| `/ingest/jobs/{id}` | GET | Get one ingest job detail |
| `/ingest/analyze/{id}` | POST | Score a resume against a JD |
| `/ingest/jobs/{id}` | DELETE | Remove an ingest record |

---

## Troubleshooting

### "Invalid or missing X-Ingest-Secret header"
→ Set `INGEST_SECRET` in `backend/.env` and `VITE_INGEST_SECRET` in `frontend/.env.local`

### Power Automate returns 401
→ Verify `INGEST_SECRET` parameter in Flow matches backend .env

### Files rejected as "not a resume"
→ Check rejection reason in UI table — detector blocks invoices, receipts, itineraries

### IMAP not working
→ Check credentials and logs; ensure service account has mailbox access

---

## Support

For detailed setup, see [EMAIL_INTAKE_GUIDE.md](./EMAIL_INTAKE_GUIDE.md)

For issues:
1. Check backend terminal for errors
2. Check browser console (F12 → Console)
3. Run test script: `python3 backend/test_ingest.py sample.pdf`
4. Verify .env files have matching `INGEST_SECRET` values
