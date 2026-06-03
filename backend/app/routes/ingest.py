"""
ingest.py — Routes for resume intake via Power Automate / IMAP / direct upload.

Endpoints
---------
POST /ingest/upload          Receive one resume (Power Automate webhook, SFTP relay, etc.)
POST /ingest/batch-upload    Receive multiple resumes in one request
GET  /ingest/jobs            List all ingested files (most recent first)
GET  /ingest/jobs/{id}       Detail for one ingest job
POST /ingest/analyze/{id}    Run / re-run analysis against a JD for an already-ingested file
DELETE /ingest/jobs/{id}     Remove an ingest job record (and its file)

Authentication
--------------
All routes require the header  X-Ingest-Secret: <value>
matching the env var  INGEST_SECRET  (set a long random string in .env).
If INGEST_SECRET is not set the endpoint returns 503 (not configured).
"""

import os
import logging
import base64
from typing import List, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.services.email_ingest import process_file, get_all_jobs, get_job
from app.services.jd_guardrails import validate_job_description_input
from app.services.analyzer import analyze_resume_against_jd

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["Email Ingest"])


class IngestBase64Request(BaseModel):
    filename: str
    content_base64: str
    recruiter_email: str = ""
    message_id: str = ""
    subject: str = ""
    job_description: str = ""
    job_id: str = ""


# ── Auth helper ──────────────────────────────────────────────────────────────
def _check_secret(x_ingest_secret: Optional[str]) -> None:
    secret = os.getenv("INGEST_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Ingest endpoint is not configured (INGEST_SECRET env var missing).",
        )
    if not x_ingest_secret or x_ingest_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ingest-Secret header.")


# ── Single file upload (Power Automate / webhook) ────────────────────────────
@router.post("/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    job_description: str = Form(""),
    job_id: str = Form(""),
    recruiter_email: str = Form(""),
    message_id: str = Form(""),
    subject: str = Form(""),
    x_ingest_secret: Optional[str] = Header(None),
):
    """
    Receive one resume file (PDF or DOCX).

    This is the webhook URL you paste into Power Automate.
    Power Automate should POST multipart/form-data with:
      - file              : the attachment
      - recruiter_email   : the original sender's email (optional)
      - message_id        : Outlook message ID for deduplication (optional)
      - subject           : email subject (optional, used to detect job title)
      - job_description   : if you want immediate analysis (optional)
      - job_id            : saved job ID to link to (optional)
    Header: X-Ingest-Secret: <your secret>
    """
    _check_secret(x_ingest_secret)

    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a valid filename.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file received.")

    metadata = {
        "message_id": message_id,
        "subject": subject,
        "source_type": "webhook",
    }

    result = process_file(
        file_bytes=file_bytes,
        original_filename=file.filename,
        source="webhook",
        recruiter_email=recruiter_email,
        job_description=job_description,
        job_id=job_id,
        metadata=metadata,
    )

    status_code = 200
    if result.get("status") == "rejected":
        status_code = 422
    elif result.get("status") == "error":
        status_code = 500

    return JSONResponse(content=result, status_code=status_code)


@router.post("/upload-base64")
async def ingest_upload_base64(
    payload: IngestBase64Request,
    x_ingest_secret: Optional[str] = Header(None),
):
    """
    Power Automate-friendly endpoint.

    Instead of multipart/form-data, send JSON with base64 content:

    {
      "filename": "John_Doe.pdf",
      "content_base64": "<base64>",
      "recruiter_email": "hr@company.com",
      "message_id": "<internetMessageId>",
      "subject": "Candidate resume",
      "job_description": "(optional)",
      "job_id": "(optional)"
    }

    Header: X-Ingest-Secret: <your secret>
    """
    _check_secret(x_ingest_secret)

    if not payload.filename:
        raise HTTPException(status_code=400, detail="filename is required")
    if not payload.content_base64:
        raise HTTPException(status_code=400, detail="content_base64 is required")

    try:
        file_bytes = base64.b64decode(payload.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="content_base64 is not valid base64")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Decoded file content is empty")

    max_bytes = int(os.getenv("INGEST_MAX_BYTES", "15000000"))
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {max_bytes} bytes")

    metadata = {
        "message_id": payload.message_id,
        "subject": payload.subject,
        "source_type": "webhook_base64",
    }

    result = process_file(
        file_bytes=file_bytes,
        original_filename=payload.filename,
        source="webhook_base64",
        recruiter_email=payload.recruiter_email,
        job_description=payload.job_description,
        job_id=payload.job_id,
        metadata=metadata,
    )

    status_code = 200
    if result.get("status") == "rejected":
        status_code = 422
    elif result.get("status") == "error":
        status_code = 500

    return JSONResponse(content=result, status_code=status_code)


# ── Batch upload ─────────────────────────────────────────────────────────────
@router.post("/batch-upload")
async def ingest_batch_upload(
    files: List[UploadFile] = File(...),
    job_description: str = Form(""),
    job_id: str = Form(""),
    recruiter_email: str = Form(""),
    x_ingest_secret: Optional[str] = Header(None),
):
    """
    Receive multiple resume files in one request.
    Returns a list of IngestJob results (one per file).
    """
    _check_secret(x_ingest_secret)

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per batch.")

    results = []
    for f in files:
        if not f.filename:
            results.append({"filename": "", "status": "rejected", "rejection_reason": "Missing filename."})
            continue
        file_bytes = await f.read()
        if not file_bytes:
            results.append({"filename": f.filename, "status": "rejected", "rejection_reason": "Empty file."})
            continue
        job = process_file(
            file_bytes=file_bytes,
            original_filename=f.filename,
            source="webhook_batch",
            recruiter_email=recruiter_email,
            job_description=job_description,
            job_id=job_id,
            metadata={},
        )
        results.append(job)

    return {"count": len(results), "results": results}


# ── List ingested jobs ────────────────────────────────────────────────────────
@router.get("/jobs")
def list_ingest_jobs(
    limit: int = 100,
    x_ingest_secret: Optional[str] = Header(None),
):
    """Return most recent ingested files and their status."""
    _check_secret(x_ingest_secret)
    jobs = get_all_jobs(limit=limit)
    return {"count": len(jobs), "jobs": jobs}


# ── Single job detail ────────────────────────────────────────────────────────
@router.get("/jobs/{ingest_id}")
def get_ingest_job(
    ingest_id: str,
    x_ingest_secret: Optional[str] = Header(None),
):
    _check_secret(x_ingest_secret)
    job = get_job(ingest_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found.")
    return job


# ── Re-analyze against a JD ──────────────────────────────────────────────────
@router.post("/analyze/{ingest_id}")
def analyze_ingested_resume(
    ingest_id: str,
    job_description: str = Form(...),
    job_id: str = Form(""),
    x_ingest_secret: Optional[str] = Header(None),
):
    """
    Run (or re-run) analysis for an already-ingested resume against a JD.
    Useful when the recruiter selects a job after the file was ingested.
    """
    _check_secret(x_ingest_secret)

    job = get_job(ingest_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found.")

    if job.get("status") in ("rejected", "error"):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot analyze: ingest status is '{job['status']}'. "
                   f"Reason: {job.get('rejection_reason', 'unknown')}",
        )

    serve_id = job.get("serve_id", "")
    if not serve_id:
        raise HTTPException(status_code=404, detail="Stored file not found for this ingest job.")

    from app.services.email_ingest import INGEST_UPLOAD_DIR
    file_path = INGEST_UPLOAD_DIR / serve_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file missing from disk.")

    try:
        validated_jd = validate_job_description_input(job_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        from app.routes.jobs import load_job_by_id
        saved_job = load_job_by_id(job_id) if job_id else None
        analysis = analyze_resume_against_jd(
            file_path=str(file_path),
            filename=job.get("filename", serve_id),
            job_description=validated_jd,
            include_llm_explanation=False,
        )
        analysis["resume_serve_id"] = serve_id
        analysis["ingest_id"] = ingest_id

        # Persist updated analysis back to the job record
        from app.services.email_ingest import _upsert_job
        updated = dict(job)
        updated["analysis"] = analysis
        updated["status"] = "analyzed"
        updated["job_id"] = job_id
        _upsert_job(updated)

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Re-analysis failed for ingest_id=%s", ingest_id)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


# ── Delete a job record ───────────────────────────────────────────────────────
@router.delete("/jobs/{ingest_id}")
def delete_ingest_job(
    ingest_id: str,
    x_ingest_secret: Optional[str] = Header(None),
):
    _check_secret(x_ingest_secret)
    from app.services.email_ingest import _load_jobs, _save_jobs, INGEST_UPLOAD_DIR, _LOCK
    import threading

    with _LOCK:
        store = _load_jobs()
        job = store["jobs"].pop(ingest_id, None)
        if not job:
            raise HTTPException(status_code=404, detail="Ingest job not found.")
        _save_jobs(store)

    # Best-effort file deletion
    serve_id = job.get("serve_id", "")
    if serve_id:
        try:
            (INGEST_UPLOAD_DIR / serve_id).unlink(missing_ok=True)
        except Exception:
            pass

    return {"deleted": ingest_id}
