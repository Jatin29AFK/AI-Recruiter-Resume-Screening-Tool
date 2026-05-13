"""
Inbound email CV parser.

Handles Mailgun-style inbound webhook payloads:
  - Validates HMAC-SHA256 webhook signatures
  - Extracts job_id from recipient address  (cvs-{job_id}@domain.com)
  - Filters attachments to .pdf / .docx only
  - Deduplicates by SHA-256 content hash
  - Saves files under uploads/inbound/{job_id}/
  - Persists metadata in data/inbound_queue.json

All state mutations are protected by a single threading.Lock so the
lightweight JSON store stays consistent under concurrent webhook requests.
"""

import hashlib
import hmac
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── Storage paths ────────────────────────────────────────────────────────────
INBOUND_DIR = os.path.join("uploads", "inbound")
QUEUE_PATH = os.path.join("data", "inbound_queue.json")

# ── Guards ───────────────────────────────────────────────────────────────────
_QUEUE_LOCK = threading.Lock()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB per file


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ext(filename: str) -> str:
    return os.path.splitext(filename.lower())[1]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_mailgun_signature(
    api_key: str,
    timestamp: str,
    token: str,
    signature: str,
) -> bool:
    """Return True if the Mailgun HMAC-SHA256 signature is valid.

    If api_key is empty (dev mode), skip verification and return True.
    """
    if not api_key:
        return True
    value = f"{timestamp}{token}".encode()
    expected = hmac.new(api_key.encode(), value, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def extract_job_id_from_recipient(recipient: str) -> Optional[str]:
    """Extract job_id from a recipient email address.

    Supported patterns:
      cvs-{job_id}@domain.com
      cvs+{job_id}@domain.com
      {job_id}@domain.com      (fallback – local part only)
    """
    local = recipient.split("@")[0].strip().lower()
    m = re.match(r"^(?:cvs[-+])?([a-zA-Z0-9_-]+)$", local)
    return m.group(1) if m else None


# ── Queue persistence ────────────────────────────────────────────────────────

def _load_queue() -> dict:
    if not os.path.exists(QUEUE_PATH):
        return {}
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_queue(data: dict) -> None:
    os.makedirs(os.path.dirname(QUEUE_PATH) or ".", exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ── Public queue API ─────────────────────────────────────────────────────────

def get_full_queue() -> dict:
    """Return the entire queue keyed by job_id."""
    with _QUEUE_LOCK:
        return _load_queue()


def get_queue_for_job(job_id: str) -> list[dict]:
    """Return all CV items for a specific job_id."""
    with _QUEUE_LOCK:
        return _load_queue().get(job_id, [])


def update_cv_status(
    job_id: str,
    cv_id: str,
    status: str,
    result: Optional[dict] = None,
) -> None:
    """Update the status (and optionally the screening result) of a single CV."""
    with _QUEUE_LOCK:
        q = _load_queue()
        for item in q.get(job_id, []):
            if item["cv_id"] == cv_id:
                item["status"] = status
                if result is not None:
                    item["screening_result"] = result
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                break
        _save_queue(q)


def get_queue_summary() -> list[dict]:
    """Return a per-job summary (job_id, counts by status)."""
    with _QUEUE_LOCK:
        q = _load_queue()

    summary = []
    for job_id, items in q.items():
        counts: dict[str, int] = {}
        for item in items:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        summary.append(
            {
                "job_id": job_id,
                "total": len(items),
                "pending": counts.get("pending", 0),
                "processing": counts.get("processing", 0),
                "done": counts.get("done", 0),
                "failed": counts.get("failed", 0),
            }
        )
    return summary


# ── Core ingestion ────────────────────────────────────────────────────────────

def save_inbound_attachments(
    recipient: str,
    sender: str,
    subject: str,
    message_id: str,
    attachments: list[tuple[str, bytes]],  # (filename, raw_bytes)
) -> tuple[Optional[str], list[dict]]:
    """Save valid CV attachments from one inbound email.

    Returns:
        (job_id, saved_items)  — job_id is None if the address could not be parsed
                                   or no valid attachments were found.
    """
    job_id = extract_job_id_from_recipient(recipient)
    if not job_id:
        return None, []

    dest_dir = os.path.join(INBOUND_DIR, job_id)
    os.makedirs(dest_dir, exist_ok=True)

    saved: list[dict] = []

    with _QUEUE_LOCK:
        q = _load_queue()
        existing_hashes = {
            item["content_hash"]
            for item in q.get(job_id, [])
        }

        for filename, content in attachments:
            # --- validate extension ---
            if _ext(filename) not in ALLOWED_EXTENSIONS:
                continue
            # --- validate size ---
            if len(content) > MAX_ATTACHMENT_BYTES:
                continue
            # --- dedup by content hash ---
            content_hash = _sha256(content)
            if content_hash in existing_hashes:
                continue

            safe_name = f"{uuid.uuid4()}_{os.path.basename(filename)}"
            file_path = os.path.join(dest_dir, safe_name)

            with open(file_path, "wb") as fh:
                fh.write(content)

            cv_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            item: dict = {
                "cv_id": cv_id,
                "job_id": job_id,
                "filename": filename,
                "saved_as": safe_name,
                "file_path": file_path,
                "sender": sender,
                "subject": subject,
                "message_id": message_id,
                "content_hash": content_hash,
                "status": "pending",
                "received_at": now,
                "updated_at": now,
                "screening_result": None,
            }

            if job_id not in q:
                q[job_id] = []
            q[job_id].append(item)
            existing_hashes.add(content_hash)
            saved.append(item)

        _save_queue(q)

    return job_id, saved
