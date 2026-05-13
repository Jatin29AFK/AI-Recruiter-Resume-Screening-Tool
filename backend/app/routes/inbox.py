"""
Inbox routes for inbound email CV ingestion.

Four endpoints:
  POST /inbox/inbound        — Mailgun webhook (receives forwarded application emails)
  GET  /inbox/queue          — All jobs with inbound CV counts (summary)
  GET  /inbox/queue/{job_id} — All inbound CVs for a specific saved job
  POST /inbox/process/{job_id} — Run screening analysis on all pending CVs for a job
                                  Returns a BatchAnalysisResponse so the frontend
                                  can feed results directly into RecruiterDashboard.

Security:
  - Webhook signature validated via HMAC-SHA256 (Mailgun)
  - MAILGUN_WEBHOOK_SIGNING_KEY must be set in .env (leave empty to skip in dev)
  - All file-path operations are validated to prevent traversal
"""

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.models.schemas import BatchAnalysisResponse, CandidateSummary, ScreeningPolicy
from app.routes.jobs import load_job_by_id
from app.services.analyzer import analyze_resume_against_jd
from app.services.decision_policy import bucket_label, get_screening_policy
from app.services.inbound_parser import (
    extract_job_id_from_recipient,
    get_full_queue,
    get_queue_for_job,
    get_queue_summary,
    save_inbound_attachments,
    update_cv_status,
    verify_mailgun_signature,
)
from app.services.jd_guardrails import validate_job_description_input
from app.services.non_negotiable_evaluator import evaluate_non_negotiables
from app.services.parser import extract_resume_text, is_likely_resume_text

router = APIRouter(prefix="/inbox", tags=["Inbox"])
logger = logging.getLogger(__name__)

_SIGNING_KEY = os.getenv("MAILGUN_WEBHOOK_SIGNING_KEY", "")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_candidate_summary(
    idx: int,
    analysis: dict,
    filename: str,
    file_path: str,
    validated_jd: str,
    saved_job,
) -> CandidateSummary:
    """Build a CandidateSummary from a completed analysis dict.

    Mirrors the logic in /matcher/batch-upload so RecruiterDashboard
    gets the identical data shape it already knows how to render.
    """
    scores = analysis["scores"]
    ats_audit = analysis["ats_audit"]
    keyword_coverage = analysis["keyword_coverage"]
    shortlist_simulation = analysis["shortlist_simulation"]
    experience_estimate = analysis["experience_estimate"]
    experience_comparison = analysis["experience_comparison"]

    non_neg = evaluate_non_negotiables(
        analysis=analysis,
        job_description=validated_jd,
        saved_job=saved_job.model_dump() if saved_job else None,
    )

    overall = round(scores["overall_score"], 1)
    bucket = "Reject" if non_neg["hard_reject"] else bucket_label(overall)

    # Inbound files are already saved at file_path — reuse same path as serve_id
    serve_id = os.path.basename(file_path)

    return CandidateSummary(
        candidate_id=str(uuid.uuid4()),
        candidate_index=idx,
        filename=filename,
        overall_score=overall,
        fit_label=scores["fit_label"],
        ats_score=round(ats_audit["score"], 1),
        required_skill_score=round(scores["required_skill_score"], 1),
        skill_support_score=round(scores["skill_support_score"], 1),
        matched_skills=analysis["matched_skills"],
        missing_skills=analysis["missing_skills"],
        critical_missing_skills=analysis["critical_missing_skills"],
        estimated_experience_years=experience_estimate.get("estimated_years"),
        experience_meets_requirement=experience_comparison.get("meets_requirement"),
        shortlist_verdict=bucket,
        backend_verdict=bucket,
        shortlist_reasons=(
            non_neg["hard_reject_reasons"][:4]
            if non_neg["hard_reject_reasons"]
            else shortlist_simulation.get("reasons", [])[:4]
        ),
        ats_issues_count=len(ats_audit.get("issues", [])),
        keyword_strong_count=keyword_coverage.get("summary", {}).get("strong_count", 0),
        keyword_missing_count=keyword_coverage.get("summary", {}).get("missing_count", 0),
        recommendation=analysis.get("recommendation"),
        linkedin_url=analysis.get("structured_resume", {}).get("linkedin") or None,
        career_progression_score=round(scores.get("career_progression_score", 0.0), 1),
        achievements_score=round(scores.get("achievements_score", 0.0), 1),
        industry_fit_score=round(scores.get("industry_fit_score", 0.0), 1),
        leadership_signals=scores.get("leadership_signals", []),
        red_flags=scores.get("red_flags", []),
        language_quality=scores.get("language_quality", {}),
        over_tailoring_flag=scores.get("over_tailoring_flag", False),
        education_meets_requirement=analysis.get("education_fit", {}).get("meets_requirement"),
        non_negotiable_flags=analysis.get("non_negotiable_flags", []),
        seniority_level=analysis.get("seniority_level", "mid"),
        resume_text=analysis.get("raw_resume_text"),
        resume_serve_id=serve_id,
        evidence_summary={
            "strong_evidence_skills": analysis.get("evidence_summary", {}).get("strong_evidence_skills", []),
            "medium_evidence_skills": analysis.get("evidence_summary", {}).get("medium_evidence_skills", []),
            "weak_evidence_skills": analysis.get("evidence_summary", {}).get("weak_evidence_skills", []),
            "skill_support_score": analysis.get("evidence_summary", {}).get("skill_support_score", 0),
        },
        timeline_gaps=[
            *[f"Short tenure: {s}" for s in analysis.get("timeline_analysis", {}).get("short_tenure_flags", [])],
            *[
                f"Gap of {g['months']}mo between roles ({g['from']} – {g['to']})"
                for g in analysis.get("timeline_analysis", {}).get("gaps", [])
                if g["months"] >= 3
            ],
        ],
        ats_issues=[
            {
                "title": issue.get("title", ""),
                "severity": issue.get("severity", ""),
                "details": issue.get("details", ""),
                "recommendation": issue.get("recommendation", ""),
            }
            for issue in ats_audit.get("issues", [])
        ],
        keyword_coverage_items=[
            {
                "skill": item.get("skill", ""),
                "status": item.get("status", ""),
                "priority": item.get("priority", ""),
                "evidence_sections": item.get("evidence_sections", []),
                "supporting_lines": item.get("supporting_lines", []),
            }
            for item in keyword_coverage.get("items", [])
            if item.get("status") in ("strong", "missing")
        ],
        primary_coverage=round(scores.get("primary_coverage", 0), 1),
        primary_coverage_source=scores.get("primary_coverage_source", "required"),
        required_skills_count=int(scores.get("required_skills_count", 0)),
        required_skills_matched_count=int(scores.get("required_skills_matched_count", 0)),
        non_negotiable_verdict=non_neg["non_negotiable_verdict"],
        non_negotiable_reasons=non_neg["hard_reject_reasons"],
        review_flags=non_neg["review_flags"],
        cert_coverage=(
            analysis.get("cert_coverage")
            if non_neg.get("evaluated_rules", {}).get("mandatory_certifications")
            else None
        ),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/inbound")
async def receive_inbound_email(request: Request):
    """
    Mailgun inbound parse webhook.

    Mailgun sends a multipart/form-data POST with these fields (among others):
      recipient       — "To" address   →  cvs-{job_id}@yourdomain.com
      sender          — applicant's From address
      from            — display From string
      Subject         — email subject
      Message-Id      — RFC message-id
      attachment-count — integer
      attachment-1 … N — uploaded files (UploadFile-style multipart parts)
      timestamp / token / signature — Mailgun HMAC fields

    We accept any POST (with or without valid signature when no signing key is
    configured) so dev mode works out of the box.
    """
    try:
        form = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse multipart form data.")

    # ── Signature verification ────────────────────────────────────────────────
    timestamp = str(form.get("timestamp", ""))
    token = str(form.get("token", ""))
    signature = str(form.get("signature", ""))
    if _SIGNING_KEY and not verify_mailgun_signature(_SIGNING_KEY, timestamp, token, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    # ── Extract metadata ──────────────────────────────────────────────────────
    recipient = str(form.get("recipient", "") or form.get("To", "")).strip()
    sender = str(form.get("sender", "") or form.get("from", "")).strip()
    subject = str(form.get("subject", "") or form.get("Subject", "")).strip()
    message_id = str(form.get("Message-Id", "") or form.get("message-id", "")).strip()

    if not recipient:
        raise HTTPException(status_code=400, detail="recipient field is required.")

    job_id = extract_job_id_from_recipient(recipient)
    if not job_id:
        logger.warning("Could not extract job_id from recipient: %s", recipient)
        return {"status": "ignored", "reason": "Could not parse job_id from recipient address."}

    # ── Extract attachments ───────────────────────────────────────────────────
    try:
        attachment_count = int(str(form.get("attachment-count", "0")))
    except ValueError:
        attachment_count = 0

    attachments: list[tuple[str, bytes]] = []
    for i in range(1, attachment_count + 1):
        file_field = form.get(f"attachment-{i}")
        if file_field is None:
            continue
        # FastAPI wraps multipart file parts as UploadFile objects
        if hasattr(file_field, "read"):
            content = await file_field.read()
            filename = getattr(file_field, "filename", None) or f"attachment-{i}.pdf"
        elif isinstance(file_field, (bytes, bytearray)):
            content = bytes(file_field)
            filename = f"attachment-{i}.bin"
        else:
            continue
        attachments.append((filename, content))

    if not attachments:
        return {"status": "ok", "saved": 0, "message": "No attachments in this email."}

    # ── Save and deduplicate ──────────────────────────────────────────────────
    saved_job_id, saved_items = save_inbound_attachments(
        recipient=recipient,
        sender=sender,
        subject=subject,
        message_id=message_id,
        attachments=attachments,
    )

    logger.info(
        "Inbound email processed: job_id=%s sender=%s saved=%d",
        saved_job_id,
        sender,
        len(saved_items),
    )

    return {
        "status": "ok",
        "job_id": saved_job_id,
        "saved": len(saved_items),
        "skipped_duplicates": len(attachments) - len(saved_items),
    }


@router.get("/queue")
def list_inbound_summary():
    """Return a per-job count summary of inbound CVs (pending/done/failed)."""
    return {"jobs": get_queue_summary()}


@router.get("/queue/{job_id}")
def list_inbound_for_job(job_id: str):
    """Return all inbound CV items for a specific job_id."""
    items = get_queue_for_job(job_id)
    # Strip large fields (raw screening_result) from the list view for efficiency
    lightweight = [
        {
            "cv_id": it["cv_id"],
            "filename": it["filename"],
            "sender": it["sender"],
            "subject": it["subject"],
            "status": it["status"],
            "received_at": it["received_at"],
            "updated_at": it["updated_at"],
            "shortlist_verdict": (
                (it.get("screening_result") or {}).get("shortlist_verdict")
            ),
            "overall_score": (
                (it.get("screening_result") or {}).get("overall_score")
            ),
        }
        for it in items
    ]
    return {
        "job_id": job_id,
        "total": len(lightweight),
        "items": lightweight,
    }


@router.post("/process/{job_id}", response_model=BatchAnalysisResponse)
async def process_inbound_cvs(job_id: str):
    """
    Screen all pending inbound CVs for a job.

    Loads the saved job (for JD text + non-negotiable rules), runs each pending
    CV through the full analysis pipeline, marks items done/failed, and returns
    a BatchAnalysisResponse — the same shape as /matcher/batch-upload — so the
    frontend can feed it directly into RecruiterDashboard.
    """
    saved_job = load_job_by_id(job_id)
    if not saved_job:
        raise HTTPException(status_code=404, detail=f"No saved job found with id '{job_id}'.")

    jd_text = (saved_job.description or "").strip()
    if not jd_text:
        raise HTTPException(status_code=422, detail="The saved job has no description/JD text to screen against.")

    try:
        validated_jd = validate_job_description_input(jd_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"JD validation failed: {exc}")

    pending = [
        item for item in get_queue_for_job(job_id)
        if item["status"] == "pending"
    ]

    if not pending:
        raise HTTPException(
            status_code=404,
            detail="No pending CVs found for this job. All may already be processed.",
        )

    policy = get_screening_policy()
    jd_title = saved_job.title

    candidates: list[CandidateSummary] = []
    failed_files: list[str] = []
    file_outcomes: list[dict] = []

    for idx, item in enumerate(pending, start=1):
        cv_id = item["cv_id"]
        file_path = item["file_path"]
        filename = item["filename"]

        # Validate path is still inside our inbound directory
        abs_inbound = os.path.abspath(os.path.join("uploads", "inbound"))
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(abs_inbound + os.sep):
            update_cv_status(job_id, cv_id, "failed")
            failed_files.append(filename)
            file_outcomes.append({
                "filename": filename,
                "status": "failed_analysis",
                "reason_code": "INVALID_PATH",
                "message": "File path is invalid or outside the allowed directory.",
            })
            continue

        if not os.path.isfile(real_path):
            update_cv_status(job_id, cv_id, "failed")
            failed_files.append(filename)
            file_outcomes.append({
                "filename": filename,
                "status": "failed_analysis",
                "reason_code": "FILE_NOT_FOUND",
                "message": "Attachment file was not found on disk.",
            })
            continue

        # Mark as processing
        update_cv_status(job_id, cv_id, "processing")

        try:
            resume_text = extract_resume_text(real_path, filename)
            is_likely, warning = is_likely_resume_text(resume_text)
            if not is_likely:
                update_cv_status(job_id, cv_id, "failed")
                failed_files.append(filename)
                file_outcomes.append({
                    "filename": filename,
                    "status": "skipped_non_resume",
                    "reason_code": "NON_RESUME_INPUT",
                    "message": warning or "File does not appear to be a resume.",
                })
                continue

            analysis = analyze_resume_against_jd(
                file_path=real_path,
                filename=filename,
                job_description=validated_jd,
            )

            candidate = _build_candidate_summary(
                idx=idx,
                analysis=analysis,
                filename=filename,
                file_path=real_path,
                validated_jd=validated_jd,
                saved_job=saved_job,
            )

            # Persist a lightweight result summary back to the queue
            update_cv_status(
                job_id,
                cv_id,
                "done",
                result={
                    "overall_score": candidate.overall_score,
                    "shortlist_verdict": candidate.shortlist_verdict,
                    "fit_label": candidate.fit_label,
                },
            )

            candidates.append(candidate)
            file_outcomes.append({"filename": filename, "status": "analyzed"})

        except Exception:
            logger.exception("Inbox processing failed for cv_id=%s filename=%s", cv_id, filename)
            update_cv_status(job_id, cv_id, "failed")
            failed_files.append(filename)
            file_outcomes.append({
                "filename": filename,
                "status": "failed_analysis",
                "reason_code": "ANALYSIS_EXCEPTION",
                "message": "Analysis failed. Check the file format/content.",
            })

    if not candidates and not failed_files:
        raise HTTPException(status_code=422, detail="No CVs could be analyzed.")

    candidates.sort(key=lambda c: c.overall_score, reverse=True)

    shortlisted = [c for c in candidates if c.shortlist_verdict == "Shortlist"]
    review = [c for c in candidates if c.shortlist_verdict == "Review"]
    rejected = [c for c in candidates if c.shortlist_verdict == "Reject"]

    return BatchAnalysisResponse(
        jd_title=jd_title,
        total_candidates=len(candidates),
        policy=policy,
        shortlisted=shortlisted,
        review=review,
        rejected=rejected,
        all_candidates=candidates,
        skipped_files=[],
        failed_files=failed_files,
        file_outcomes=file_outcomes,
    )
