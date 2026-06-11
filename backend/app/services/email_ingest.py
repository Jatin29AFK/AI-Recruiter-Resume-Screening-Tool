"""
email_ingest.py
===============
Core ingestion logic shared by:
  - POST /ingest/upload  (Power Automate webhook / direct upload)
  - IMAP poller          (optional background thread)

Flow for every ingested file
------------------------------
1. Validate file type
2. Compute SHA-256 to detect duplicates
3. Save to uploads/ingest/
4. Run extract_resume_text  →  evaluate_resume_document
5. Persist IngestJob record (pending / rejected / accepted)
6. If a job_description is supplied immediately:  run full analysis
7. Return IngestJob dict

IMAP poller (optional, separate thread)
-----------------------------------------
Start with  start_imap_poller()  from the FastAPI lifespan or a management command.
It reads IMAP_* env vars, polls every POLL_INTERVAL_SECONDS,
downloads attachments from unseen messages, and processes them via process_file().
"""

import os
import uuid
import hashlib
import json
import logging
import threading
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Storage ──────────────────────────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
INGEST_UPLOAD_DIR = _BASE_DIR / "uploads" / "ingest"
INGEST_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = _BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
INGEST_JOBS_FILE = DATA_DIR / "ingest_jobs.json"
INGEST_SETTINGS_FILE = DATA_DIR / "ingest_settings.json"

_LOCK = threading.Lock()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

# ── IngestJob schema ─────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_jobs_store() -> dict:
    return {"jobs": {}}


def _load_jobs() -> dict:
    if not INGEST_JOBS_FILE.exists():
        return _empty_jobs_store()
    try:
        with open(INGEST_JOBS_FILE, "r") as f:
            data = json.load(f)
            if "jobs" not in data:
                data["jobs"] = {}
            return data
    except (json.JSONDecodeError, OSError):
        return _empty_jobs_store()


def _save_jobs(store: dict) -> None:
    tmp = INGEST_JOBS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(store, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, INGEST_JOBS_FILE)


def _empty_settings_store() -> dict:
    return {"active_job_id": ""}


def _load_settings() -> dict:
    if not INGEST_SETTINGS_FILE.exists():
        return _empty_settings_store()
    try:
        with open(INGEST_SETTINGS_FILE, "r") as f:
            data = json.load(f)
            if "active_job_id" not in data:
                data["active_job_id"] = ""
            return data
    except (json.JSONDecodeError, OSError):
        return _empty_settings_store()


def _save_settings(store: dict) -> None:
    tmp = INGEST_SETTINGS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(store, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, INGEST_SETTINGS_FILE)


def get_active_job_id() -> str:
    store = _load_settings()
    active_job_id = store.get("active_job_id")
    return active_job_id if isinstance(active_job_id, str) else ""


def set_active_job_id(job_id: str) -> str:
    normalized_job_id = (job_id or "").strip()
    with _LOCK:
        store = _load_settings()
        store["active_job_id"] = normalized_job_id
        _save_settings(store)
    return normalized_job_id


def get_active_job():
    active_job_id = get_active_job_id()
    if not active_job_id:
        return None

    from app.routes.jobs import load_job_by_id

    active_job = load_job_by_id(active_job_id)
    if active_job is None:
        set_active_job_id("")
    return active_job


def _upsert_job(job: dict) -> None:
    with _LOCK:
        store = _load_jobs()
        store["jobs"][job["ingest_id"]] = job
        _save_jobs(store)


def get_all_jobs(limit: int = 200) -> list:
    store = _load_jobs()
    jobs = list(store["jobs"].values())
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs[:limit]


def get_job(ingest_id: str) -> Optional[dict]:
    store = _load_jobs()
    return store["jobs"].get(ingest_id)


# ── File processing ───────────────────────────────────────────────────────────
def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_duplicate(file_hash: str) -> Optional[str]:
    """Return existing ingest_id if the same file was already ingested."""
    store = _load_jobs()
    for ingest_id, job in store["jobs"].items():
        if job.get("file_hash") == file_hash:
            return ingest_id
    return None


def process_file(
    file_bytes: bytes,
    original_filename: str,
    source: str = "webhook",
    recruiter_email: str = "",
    job_description: str = "",
    job_id: str = "",
    metadata: dict = None,
) -> dict:
    """
    Ingest one file.  Returns an IngestJob dict.

    Parameters
    ----------
    file_bytes          : raw bytes of the attachment
    original_filename   : original name (used for extension check and display)
    source              : 'webhook', 'imap', 'manual'
    recruiter_email     : who forwarded/uploaded (for audit)
    job_description     : if provided, run full analysis immediately
    job_id              : if provided, link to a saved job
    metadata            : extra dict (email headers, message-id, etc.)
    """
    from app.services.parser import extract_resume_text
    from app.services.resume_detector import evaluate_resume_document

    ingest_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower()

    # ── Validate extension ───────────────────────────────────────────────────
    if ext not in ALLOWED_EXTENSIONS:
        job = _make_job(
            ingest_id=ingest_id,
            filename=original_filename,
            source=source,
            recruiter_email=recruiter_email,
            status="rejected",
            rejection_reason=f"Unsupported file type: {ext}. Only PDF and DOCX are accepted.",
            metadata=metadata,
        )
        _upsert_job(job)
        return job

    # ── Save to disk ──────────────────────────────────────────────────────────
    safe_name = f"{ingest_id}_{original_filename}"
    dest = INGEST_UPLOAD_DIR / safe_name
    try:
        dest.write_bytes(file_bytes)
    except OSError as e:
        job = _make_job(
            ingest_id=ingest_id,
            filename=original_filename,
            source=source,
            recruiter_email=recruiter_email,
            status="error",
            rejection_reason=f"Storage error: {e}",
            metadata=metadata,
        )
        _upsert_job(job)
        return job

    # ── Deduplicate ───────────────────────────────────────────────────────────
    fhash = _file_hash(dest)
    existing_id = _is_duplicate(fhash)
    if existing_id:
        dest.unlink(missing_ok=True)
        existing = get_job(existing_id)
        logger.info("Duplicate ingest skipped: %s → %s", original_filename, existing_id)
        existing = dict(existing)
        existing["_duplicate_of"] = existing_id
        existing["_duplicate_filename"] = original_filename
        return existing

    # ── Parse + detect ────────────────────────────────────────────────────────
    try:
        resume_text = extract_resume_text(str(dest), original_filename)
        detection = evaluate_resume_document(text=resume_text, filename=original_filename)
    except Exception as e:
        logger.exception("Parse error for %s", original_filename)
        job = _make_job(
            ingest_id=ingest_id,
            filename=original_filename,
            serve_id=safe_name,
            file_hash=fhash,
            source=source,
            recruiter_email=recruiter_email,
            status="error",
            rejection_reason=f"File could not be parsed: {e}",
            metadata=metadata,
        )
        _upsert_job(job)
        return job

    if detection.get("final_label") == "reject":
        job = _make_job(
            ingest_id=ingest_id,
            filename=original_filename,
            serve_id=safe_name,
            file_hash=fhash,
            source=source,
            recruiter_email=recruiter_email,
            status="rejected",
            rejection_reason=detection.get("warning_message") or "Not a valid resume document.",
            metadata=metadata,
        )
        _upsert_job(job)
        return job

    # ── Immediate analysis (if JD provided) ──────────────────────────────────
    resolved_job_description = (job_description or "").strip()
    resolved_job_id = (job_id or "").strip()
    active_job = None

    if not resolved_job_description:
        active_job = get_active_job()
        if active_job and getattr(active_job, "description", "").strip():
            resolved_job_description = active_job.description.strip()
            resolved_job_id = getattr(active_job, "job_id", "") or resolved_job_id

    analysis_result = None
    if resolved_job_description:
        try:
            from app.services.jd_guardrails import validate_job_description_input
            from app.services.analyzer import analyze_resume_against_jd
            from app.routes.jobs import load_job_by_id
            validated_jd = validate_job_description_input(resolved_job_description)
            saved_job = load_job_by_id(resolved_job_id) if resolved_job_id else None
            analysis_result = analyze_resume_against_jd(
                file_path=str(dest),
                filename=original_filename,
                job_description=validated_jd,
                include_llm_explanation=False,
            )
            analysis_result["resume_serve_id"] = safe_name
        except Exception as e:
            logger.exception("Analysis failed during ingest for %s", original_filename)
            analysis_result = {"error": str(e)}

    job = _make_job(
        ingest_id=ingest_id,
        filename=original_filename,
        serve_id=safe_name,
        file_hash=fhash,
        source=source,
        recruiter_email=recruiter_email,
        status="analyzed" if analysis_result and "error" not in analysis_result else "accepted",
        detection=detection,
        analysis=analysis_result,
        job_id=resolved_job_id,
        metadata=metadata,
    )
    _upsert_job(job)
    return job


def _make_job(
    ingest_id: str,
    filename: str,
    source: str = "webhook",
    recruiter_email: str = "",
    status: str = "accepted",
    serve_id: str = "",
    file_hash: str = "",
    rejection_reason: str = "",
    detection: dict = None,
    analysis: dict = None,
    job_id: str = "",
    metadata: dict = None,
) -> dict:
    return {
        "ingest_id": ingest_id,
        "filename": filename,
        "serve_id": serve_id,
        "file_hash": file_hash,
        "source": source,
        "recruiter_email": recruiter_email,
        "status": status,
        "rejection_reason": rejection_reason,
        "detection": detection or {},
        "analysis": analysis,
        "job_id": job_id,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }


# ── IMAP poller (optional) ────────────────────────────────────────────────────
_IMAP_THREAD: threading.Thread | None = None
_IMAP_STOP = threading.Event()


def _get_poll_interval_seconds() -> int:
    try:
        return max(5, int(os.getenv("IMAP_POLL_INTERVAL", "15")))
    except (TypeError, ValueError):
        return 15


def _imap_poll_loop():
    """
    Background loop: connect to IMAP, fetch unseen messages,
    extract PDF/DOCX attachments, run process_file() on each.
    Runs until _IMAP_STOP is set.
    """
    import imaplib
    import email as email_lib
    from email.header import decode_header

    host = os.getenv("IMAP_HOST", "")
    port = int(os.getenv("IMAP_PORT", "993"))
    user = os.getenv("IMAP_USER", "")
    password = os.getenv("IMAP_PASSWORD", "")
    mailbox = os.getenv("IMAP_MAILBOX", "INBOX")

    if not host or not user or not password:
        logger.warning("IMAP poller: IMAP_HOST / IMAP_USER / IMAP_PASSWORD not set. Poller exiting.")
        return

    logger.info("IMAP poller started — host=%s user=%s mailbox=%s", host, user, mailbox)

    while not _IMAP_STOP.is_set():
        try:
            with imaplib.IMAP4_SSL(host, port) as conn:
                conn.login(user, password)
                conn.select(mailbox, readonly=False)
                _, data = conn.search(None, "UNSEEN")
                msg_ids = data[0].split() if data[0] else []

                logger.info("IMAP: %d unseen messages found", len(msg_ids))

                for mid in msg_ids:
                    if _IMAP_STOP.is_set():
                        break
                    _, msg_data = conn.fetch(mid, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    # Decode sender
                    from_raw = msg.get("From", "")
                    message_id = msg.get("Message-ID", "")
                    subject_raw = msg.get("Subject", "")
                    parts_decoded = decode_header(subject_raw)
                    subject = "".join(
                        (b.decode(enc or "utf-8") if isinstance(b, bytes) else b)
                        for b, enc in parts_decoded
                    )

                    email_metadata = {
                        "from": from_raw,
                        "message_id": message_id,
                        "subject": subject,
                        "date": msg.get("Date", ""),
                    }

                    attachments_found = 0
                    for part in msg.walk():
                        cd = part.get_content_disposition() or ""
                        if "attachment" not in cd and "inline" not in cd:
                            continue
                        part_filename = part.get_filename() or ""
                        ext = Path(part_filename).suffix.lower()
                        if ext not in ALLOWED_EXTENSIONS:
                            continue
                        payload = part.get_payload(decode=True)
                        if not payload:
                            continue

                        logger.info("IMAP: processing attachment %s from %s", part_filename, from_raw)
                        process_file(
                            file_bytes=payload,
                            original_filename=part_filename,
                            source="imap",
                            recruiter_email=from_raw,
                            metadata=email_metadata,
                        )
                        attachments_found += 1

                    if attachments_found == 0:
                        logger.info("IMAP: message %s had no resume attachments", message_id)

                    # Mark as seen after processing
                    conn.store(mid, "+FLAGS", "\\Seen")

        except Exception as e:
            logger.exception("IMAP poll error: %s", e)

        _IMAP_STOP.wait(_get_poll_interval_seconds())

    logger.info("IMAP poller stopped.")


def start_imap_poller() -> None:
    """Start the background IMAP polling thread (idempotent)."""
    global _IMAP_THREAD
    if _IMAP_THREAD and _IMAP_THREAD.is_alive():
        return
    _IMAP_STOP.clear()
    _IMAP_THREAD = threading.Thread(target=_imap_poll_loop, daemon=True, name="imap-poller")
    _IMAP_THREAD.start()
    logger.info("IMAP poller thread started.")


def stop_imap_poller() -> None:
    """Signal the IMAP polling thread to stop."""
    _IMAP_STOP.set()
    if _IMAP_THREAD:
        _IMAP_THREAD.join(timeout=10)
    logger.info("IMAP poller stopped.")
