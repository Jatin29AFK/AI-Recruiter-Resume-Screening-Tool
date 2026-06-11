# Email Intake Demo - Quick Start (15 Minutes)

## Step-by-Step Setup

## Production Automation You Will Show IT

The working demo proves the pipeline. For production, use this exact chain:

1. Recruiter sends or forwards a resume from Outlook.
2. Outlook or Exchange copies that message to a shared intake mailbox.
3. Power Automate watches the shared mailbox and triggers on new mail.
4. Power Automate downloads the attachment, converts it to base64, and posts it to the backend.
5. The backend validates, stores, and scores the resume.
6. The app shows the resume instantly in Email Intake.

**Best practice:** use a shared mailbox like `resumes@company.com` as the one control point IT can approve.

### 1️⃣ Create Free Gmail Account (3 min)
1. Go to https://accounts.google.com/signup
2. Create: `your-company-resumes@gmail.com`
3. Enable **2-Step Verification**: https://myaccount.google.com/security
4. Generate **App Password**: https://myaccount.google.com/apppasswords
   - Select: **Mail** → **Other (Custom)** → "Resume App"
   - **SAVE THE 16-CHAR PASSWORD** (looks like: `abcd efgh ijkl mnop`)
5. Enable **IMAP**:
   - Gmail Settings → **Forwarding and POP/IMAP** → **Enable IMAP**

### 2️⃣ Configure Backend (2 min)
Edit `backend/.env`:

```env
# Generate secret if not already set:
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"
INGEST_SECRET=your-secret-here

# Add Gmail IMAP settings:
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your-company-resumes@gmail.com
IMAP_PASSWORD=abcd efgh ijkl mnop
IMAP_MAILBOX=INBOX
IMAP_POLL_INTERVAL=60
```

**Replace:**
- `IMAP_USER` with your Gmail address
- `IMAP_PASSWORD` with the 16-char app password

### 3️⃣ Start Backend (1 min)
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Look for:**
```
INFO: IMAP poller started — host=imap.gmail.com user=your-company-resumes@gmail.com
INFO: IMAP: 0 unseen messages found
```

✅ If you see this → IMAP is working!

### 4️⃣ Configure Frontend (1 min)
Edit `frontend/.env.local`:

```env
VITE_INGEST_SECRET=your-secret-here
```

**Must match** `INGEST_SECRET` from backend `.env`

Start frontend:
```bash
cd frontend
npm run dev
```

### 5️⃣ Test Complete Flow (5 min)

**Send Test Email:**
1. From your **personal email** (Gmail, Outlook, etc.)
2. Send to: `your-company-resumes@gmail.com`
3. Subject: "Software Engineer Resume"
4. Attach: Any PDF resume

**Wait 60-90 seconds** for IMAP to poll.

**Check Backend Logs:**
```
INFO: IMAP: 1 unseen messages found
INFO: IMAP: processing attachment John_Doe.pdf from yourname@gmail.com
INFO: Resume accepted: John_Doe.pdf
```

**Check Frontend:**
1. Open: http://localhost:5173
2. Click **📥 Email Intake** button
3. See resume in table with status **→ Pending JD**
4. Click **Analyze** → paste job description → get score

**✅ IT'S WORKING!** Email → Auto-process → Score

### 6️⃣ Record for IT Team (3 min)

**Take screenshots:**
1. Gmail inbox with email + attachment
2. Backend terminal showing "IMAP: processing attachment..."
3. Frontend showing resume in Email Intake panel
4. Resume being scored with final result

**Video (1 minute):**
- Screen record: send email → wait → show backend logs → show UI → click analyze → score appears

## Exact Production Steps for IT Approval

Use these steps when you explain how this becomes fully automatic in the company environment:

1. **Create one shared mailbox**
   - Example: `resumes@company.com`
   - IT grants access to the service account or Power Automate connection.

2. **Create an Outlook rule or mailbox button**
   - Recruiters send resumes normally or click one Outlook action named `Send to Screening`.
   - The rule copies the message into the shared intake mailbox.

3. **Build the Power Automate flow**
   - Trigger: `When a new email arrives in a shared mailbox (V3)`.
   - Filter: only messages with attachments and/or resume keywords if IT wants tighter control.
   - Action: `Get attachment content` for each file.

4. **Call the backend**
   - Send a `POST` request to `/ingest/upload-base64`.
   - Include headers: `Content-Type: application/json` and `X-Ingest-Secret`.
   - Send JSON fields: `filename`, `content_base64`, `recruiter_email`, `message_id`, `subject`.

5. **Show the result in the app**
   - The backend stores the resume.
   - Email Intake refreshes and shows the new record.
   - Recruiters can analyze it against a job description immediately.

6. **Keep manual upload as fallback only**
   - The drag-drop box stays available for testing and exceptions.
   - Production uses the mailbox automation path.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Authentication failed" | Regenerate app password at https://myaccount.google.com/apppasswords |
| "IMAP: 0 unseen messages" | Mark email as **Unread** in Gmail, wait 60s |
| No logs appear | Check `.env` file has correct IMAP settings, restart backend |
| Resume rejected | Use a text-based PDF resume (not scanned image) |

---

## What to Tell IT

**"Here's our working prototype..."**

✅ Uses standard IMAP (same protocol as Outlook/Exchange)  
✅ Shared mailbox approach (1 inbox, not individual accounts)  
✅ Authenticated API (secret header required)  
✅ Auto-validates resumes (rejects invoices/receipts)  
✅ Works with Power Automate (org-approved tool)  
✅ Full audit trail (email headers preserved)  

**"How automation works:"**
- Outlook or Exchange routes mail into a shared mailbox
- Power Automate watches that mailbox
- Power Automate sends resume files to our backend automatically
- Our app processes and displays the result without manual upload

**"We need:"**
- Shared mailbox: `resumes@company.com`
- IMAP access (or Power Automate connector)
- Read permissions for service account

**Estimated time savings:** 10+ minutes per resume × 50 resumes/week = **8+ hours/week**

---

## Full Details
See [DEMO_SETUP_GUIDE.md](./DEMO_SETUP_GUIDE.md) for complete instructions, troubleshooting, and IT presentation script.
