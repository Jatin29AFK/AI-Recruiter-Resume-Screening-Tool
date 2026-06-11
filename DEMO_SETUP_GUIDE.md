# Email Intake Demo Setup (No IT Approval Needed)

## Overview
This guide will help you create a **fully working demo** of the email intake feature using a free Gmail account. You can show this to IT to prove the concept works before they provision the real shared mailbox.

**Total setup time:** 15 minutes  
**Requirements:** A Gmail account (create a new one just for testing)

## Production Automation Architecture

This is the production flow you should show IT after the demo is working:

1. Recruiter sends or forwards a resume from Outlook.
2. Exchange or Outlook rules copy the email into a shared intake mailbox.
3. Power Automate triggers when a new message arrives in that shared mailbox.
4. Power Automate reads the attachment, converts it to base64, and posts it to the backend.
5. The backend validates, stores, and scores the resume.
6. The Email Intake screen updates automatically.

**Recommended production control point:** one shared mailbox such as `resumes@company.com`.

---

## Part 1: Create Demo Gmail Account (5 minutes)

### Step 1: Create Gmail Account
1. Go to https://accounts.google.com/signup
2. Create account: `your-company-resumes@gmail.com` (or any name)
3. Set password and save it

### Step 2: Enable IMAP Access
1. Sign in to the Gmail account
2. Click **Settings** (gear icon) → **See all settings**
3. Click **Forwarding and POP/IMAP** tab
4. Find **IMAP access** section
5. Select **Enable IMAP**
6. Click **Save Changes**

### Step 3: Create App Password (Important - Gmail blocks normal passwords)
1. Go to https://myaccount.google.com/apppasswords
2. You may need to enable 2-Step Verification first:
   - Go to https://myaccount.google.com/security
   - Turn on **2-Step Verification** (follow prompts)
3. After 2-Step is enabled, go back to App passwords
4. Click **Select app** → Choose **Mail**
5. Click **Select device** → Choose **Other (Custom name)**
6. Type: "Resume Screening App"
7. Click **Generate**
8. **COPY THE 16-CHARACTER PASSWORD** (looks like: `abcd efgh ijkl mnop`)
9. Save this password securely

## Part 0: Explain the Production Path (for IT)

When you present the demo, explain that Gmail is only for the proof-of-concept. The real system uses a shared mailbox and Power Automate.

**Production handoff steps:**
1. IT creates the shared mailbox.
2. Recruiters send or forward resumes there, or use one Outlook button.
3. Power Automate watches the mailbox.
4. Power Automate posts each attachment to `/ingest/upload-base64`.
5. The app processes the resume and shows it in Email Intake.

---

## Part 2: Configure Backend (3 minutes)

### Step 1: Add IMAP Settings to .env
1. Open `backend/.env` file
2. Add these lines (use your Gmail details):

```env
# Email Intake - IMAP Polling (Demo)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your-company-resumes@gmail.com
IMAP_PASSWORD=abcd efgh ijkl mnop
IMAP_MAILBOX=INBOX
IMAP_POLL_INTERVAL=60
```

**Replace:**
- `IMAP_USER` → your Gmail address
- `IMAP_PASSWORD` → the 16-char app password (keep the spaces)

### Step 2: Restart Backend
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Look for this in terminal:**
```
INFO: IMAP poller started — host=imap.gmail.com user=your-company-resumes@gmail.com
INFO: IMAP: 0 unseen messages found
```

If you see this → IMAP is working! ✅

If you see errors:
- `Authentication failed` → Wrong password (check app password)
- `IMAP not enabled` → Go back to Gmail settings, enable IMAP

---

## Part 3: Start IMAP Polling (2 minutes)

The IMAP poller needs to be started. Add this to your backend startup:

### Option A: Auto-start on server startup (Recommended)

Edit `backend/app/main.py` to start IMAP on startup:

```python
from contextlib import asynccontextmanager
from app.services.email_ingest import start_imap_poller, stop_imap_poller

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_imap_poller()
    yield
    # Shutdown
    stop_imap_poller()

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Hybrid AI Resume–Job Matcher backend",
    lifespan=lifespan,  # Add this
)
```

Then restart backend.

### Option B: Manual start (for testing)

Add a test endpoint to start the poller:

```python
# In backend/app/routes/ingest.py, add:

@router.post("/start-imap")
def start_imap_polling(x_ingest_secret: Optional[str] = Header(None)):
    _check_secret(x_ingest_secret)
    from app.services.email_ingest import start_imap_poller
    start_imap_poller()
    return {"status": "IMAP poller started"}
```

Then call it once:
```bash
curl -X POST http://127.0.0.1:8000/ingest/start-imap \
  -H "X-Ingest-Secret: your-secret"
```

---

## Part 4: Test the Complete Flow (5 minutes)

### Step 1: Send Test Email
1. From your **personal email** (not the demo Gmail):
   - Send email to `your-company-resumes@gmail.com`
   - **Subject:** "Software Engineer Resume"
   - **Attach:** Any PDF resume you have

2. Wait 60-90 seconds (IMAP polls every 60s)

### Step 2: Check Backend Logs
Look at the terminal where backend is running. You should see:

```
INFO: IMAP: 1 unseen messages found
INFO: IMAP: processing attachment John_Doe.pdf from yourname@gmail.com
INFO: Resume accepted: John_Doe.pdf
```

### Step 3: Check Frontend UI
1. Open app: `http://localhost:5173`
2. Click **📥 Email Intake** button
3. You should see the resume in the table:
   - Filename: `John_Doe.pdf`
   - Status: **→ Pending JD** (green/blue)
   - Source: `imap`
   - Submitted by: `yourname@gmail.com`

**Success!** ✅ The email → IMAP → backend → UI flow is working!

### Step 4: Score the Resume
1. In the table, click **Analyze** button next to the resume
2. Paste any job description
3. Click **Run Analysis →**
4. Wait a few seconds
5. Score appears in the table!

---

## Part 5: Record Demo for IT (What to Show)

### Create a Quick Video/Screenshot Walkthrough

**Scene 1: Show the Email**
- Screenshot of Gmail inbox showing the test email with resume attachment
- Caption: "Recruiter forwards resume to shared mailbox"

**Scene 2: Show Backend Processing**
- Screenshot of terminal logs showing:
  ```
  INFO: IMAP: processing attachment resume.pdf from recruiter@company.com
  ```
- Caption: "System automatically detects and validates resume"

**Scene 3: Show UI Table**
- Screenshot of Email Intake panel with the resume listed
- Caption: "Resume appears in screening dashboard automatically"

**Scene 4: Show Scoring**
- Screenshot of clicking Analyze button
- Screenshot of pasting JD
- Screenshot of final score
- Caption: "Recruiter scores resume against job description"

**Scene 5: Show Security**
- Screenshot of `.env` file showing `INGEST_SECRET` and `IMAP_PASSWORD`
- Caption: "All credentials stored securely, authenticated access only"

### Talking Points for IT Demo

**"Here's what we built..."**

1. **Zero external access:** "We use IMAP — a standard email protocol. No third-party apps access our mail server directly."

2. **Standard Microsoft tools:** "In production, this will use Power Automate (already approved) or Exchange IMAP. Same security controls as your current email gateway."

3. **Shared mailbox approach:** "We only need access to ONE shared mailbox (resumes@company.com), not individual recruiter mailboxes. This limits exposure."

4. **Authenticated endpoints:** "Every API call requires a secret header. Unauthorized requests are blocked."

5. **Resume validation:** "The system automatically rejects non-resume files (invoices, receipts, etc.) so the database stays clean."

6. **Audit trail:** "We preserve original email headers (from, message-id, date) for compliance."

7. **Works with existing tools:** "Recruiters can use Outlook Quick Steps (1-click forward) or Power Automate buttons — no new tools to learn."

### Exact production message for IT

"The demo proves the flow. In production, the recruiter does not upload files into the app. Outlook or Exchange copies the resume email into a shared mailbox, Power Automate watches that mailbox, and Power Automate sends the attachment to our backend automatically."

---

## Troubleshooting Demo Issues

### "IMAP: 0 unseen messages found" (even after sending email)
**Causes:**
- Email was marked as read (open it in Gmail and mark as unread)
- Polling interval hasn't elapsed yet (wait 60s)
- Email went to Spam (check Gmail spam folder)

**Fix:**
1. Mark email as **Unread** in Gmail
2. Wait for next poll cycle
3. Check backend logs

### "Authentication failed"
**Causes:**
- Wrong app password
- IMAP not enabled
- 2-Step Verification not turned on

**Fix:**
1. Regenerate app password (https://myaccount.google.com/apppasswords)
2. Double-check IMAP is enabled in Gmail settings
3. Verify 2-Step Verification is ON

### Resume rejected as "not a resume"
**Good!** This proves the detector works.

**To fix for demo:**
- Use a real resume PDF (not a scanned image)
- Make sure the file has text (not just images)
- Try a different resume file

### IMAP poller not starting
**Check:**
1. Did you add the lifespan hook to main.py?
2. Did you restart the backend?
3. Check terminal for "IMAP poller started" message

**Manual start:**
```bash
curl -X POST http://127.0.0.1:8000/ingest/start-imap \
  -H "X-Ingest-Secret: your-secret"
```

---

## Quick Demo Script (1 Minute Walkthrough)

Use this script when showing IT:

**[OPEN GMAIL]**  
"Here's our demo shared mailbox. I'll forward a resume to it..."  
**[Send email with resume attachment]**

**[OPEN TERMINAL - show backend logs]**  
"The system polls the mailbox every 60 seconds using standard IMAP..."  
**[Wait, show logs: "IMAP: processing attachment..."]**

**[OPEN FRONTEND - click Email Intake]**  
"The resume appears automatically in the screening dashboard..."  
**[Point to table showing the resume]**

**[CLICK ANALYZE]**  
"Our recruiter pastes the job description..."  
**[Paste JD, click Run Analysis]**

**[SHOW SCORE]**  
"And gets an instant screening score. The resume is now ready for decision."

**[CONCLUSION]**  
"This saves our team 10+ minutes per resume. We need a shared mailbox (`resumes@company.com`) to roll this out to all recruiters."

---

## After Demo: What to Send IT

### Email Template:

**Subject:** Email Intake Demo - Shared Mailbox Request

Hi [IT Team],

Thank you for your time. As discussed, I've prepared a working demo of our resume screening automation.

**Demo recording:** [link to video/screenshots]

**What it does:**
- Recruiters forward resumes to a shared mailbox
- System automatically validates (rejects invoices/receipts)
- Resumes appear in screening dashboard instantly
- Recruiters score against job descriptions on-demand

**Technical details:**
- Uses standard IMAP protocol (same as Outlook/Gmail)
- Authenticated API calls only (secret header required)
- Audit trail preserved (email headers, sender, timestamp)
- Works with Power Automate (approved org tool)

**Next step:**
Please provision shared mailbox: `resumes@company.com`  
Grant access to: [your account / service account]

I'm happy to schedule a technical review or provide architecture diagrams if needed.

Thanks,  
[Your Name]

---

## Cleanup After Demo

To stop the demo setup:

```bash
# Stop backend
# Press Ctrl+C in terminal

# Delete test emails from Gmail
# (or just leave the demo account as-is)

# Comment out IMAP settings in .env
# IMAP_HOST=imap.gmail.com
# IMAP_USER=...
# (etc.)
```

When IT provisions the real shared mailbox, you'll update the same IMAP settings with the company credentials.

---

## Summary Checklist

- [ ] Created demo Gmail account
- [ ] Enabled IMAP in Gmail settings
- [ ] Generated app password
- [ ] Added IMAP settings to backend/.env
- [ ] Started IMAP poller
- [ ] Sent test email with resume
- [ ] Verified resume appears in UI
- [ ] Scored resume against JD
- [ ] Recorded demo screenshots/video
- [ ] Drafted email to IT with demo proof

**You're ready to show IT!** 🎉
