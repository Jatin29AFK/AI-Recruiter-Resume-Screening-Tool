import os
import uuid
import json
import mimetypes
import logging
import tempfile
import threading
import time
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from app.models.schemas import (
    MatchAnalysisResponse, ResumeTailorResponse, MultiJDCompareResponse,
    BatchAnalysisResponse, CandidateSummary, CandidateStatusBatchRequest,
)
from app.services.analyzer import analyze_resume_against_jd
from app.services.parser import extract_resume_text, is_likely_resume_text
from app.services.tailor_service import generate_optimized_resume_for_jd
from app.services.multi_jd_compare import compare_resume_against_multiple_jds
from app.services.jd_guardrails import validate_job_description_input
from app.services.visitor_counter import register_visit, get_visitor_count
from app.services.jd_url_extractor import extract_job_description_from_url
from app.services.non_negotiable_evaluator import evaluate_non_negotiables
from app.services.decision_policy import bucket_label, get_screening_policy
from app.routes.jobs import load_job_by_id

router = APIRouter(prefix="/matcher", tags=["Matcher"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class JobUrlRequest(BaseModel):
    url: str


@router.get("/visitor-count")
def read_visitor_count():
    try:
        count = get_visitor_count()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read visitor count: {str(e)}")


@router.post("/visitor-count/increment")
def increment_visitor_count():
    try:
        count = register_visit()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update visitor count: {str(e)}")


@router.post("/extract-jd-from-url")
def extract_jd_from_url(payload: JobUrlRequest):
    try:
        if not payload.url or not payload.url.strip():
            raise HTTPException(status_code=400, detail="URL is required.")

        extracted = extract_job_description_from_url(payload.url.strip())
        validated = validate_job_description_input(extracted)

        return {
            "url": payload.url.strip(),
            "job_description": validated,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract JD from URL: {str(e)}")


@router.post("/tailor-resume", response_model=ResumeTailorResponse)
async def tailor_resume_for_job(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        if not resume.filename:
            raise HTTPException(status_code=400, detail="Resume file must have a valid filename.")

        allowed_extensions = (".pdf", ".docx")
        if not resume.filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

        safe_filename = f"{uuid.uuid4()}_{resume.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as f:
            content = await resume.read()
            f.write(content)

        # Quick content-based guardrail: ensure the uploaded file resembles a resume
        resume_text = extract_resume_text(file_path, resume.filename)
        is_likely, warning = is_likely_resume_text(resume_text)
        if not is_likely:
            raise HTTPException(status_code=400, detail=warning or "Uploaded file does not appear to be a resume.")

        validated_jd = validate_job_description_input(job_description)

        result = generate_optimized_resume_for_jd(
            file_path=file_path,
            filename=resume.filename,
            job_description=validated_jd,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/resume/{serve_id}")
def download_resume_file(serve_id: str):
    """
    Serve an originally-uploaded resume file (PDF or DOCX) by its serve_id.
    The serve_id is the UUID-prefixed filename stored in the uploads/ directory.
    """
    # Security: block path traversal and only allow safe filenames
    if '/' in serve_id or '\\' in serve_id or '..' in serve_id:
        raise HTTPException(status_code=400, detail="Invalid file identifier.")

    # Only allow known extensions
    lower = serve_id.lower()
    if not (lower.endswith('.pdf') or lower.endswith('.docx')):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    abs_uploads = os.path.abspath(UPLOAD_DIR)
    file_path = os.path.join(abs_uploads, serve_id)
    real_path = os.path.realpath(file_path)

    # Ensure the resolved path is inside uploads dir (prevent symlink traversal)
    if not real_path.startswith(abs_uploads + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file identifier.")

    if not os.path.isfile(real_path):
        raise HTTPException(status_code=404, detail="File not found. It may have been cleaned up.")

    media_type = "application/pdf" if lower.endswith('.pdf') else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=real_path,
        media_type=media_type,
        filename=serve_id.split('_', 1)[-1] if '_' in serve_id else serve_id,
    )


@router.get("/resume/{serve_id}/preview")
def preview_resume_file(serve_id: str):
    """
    Preview endpoint:
    - PDF files: served with Content-Disposition: inline so the browser renders them directly.
    - DOCX files: converted to styled HTML via mammoth for in-browser display.
    """
    if '/' in serve_id or '\\' in serve_id or '..' in serve_id:
        raise HTTPException(status_code=400, detail="Invalid file identifier.")

    lower = serve_id.lower()
    if not (lower.endswith('.pdf') or lower.endswith('.docx')):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    abs_uploads = os.path.abspath(UPLOAD_DIR)
    file_path = os.path.join(abs_uploads, serve_id)
    real_path = os.path.realpath(file_path)

    if not real_path.startswith(abs_uploads + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file identifier.")

    if not os.path.isfile(real_path):
        raise HTTPException(status_code=404, detail="File not found.")

    if lower.endswith('.pdf'):
        # Serve PDF inline so the browser renders it
        return FileResponse(
            path=real_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    # DOCX → convert to HTML for in-browser preview
    try:
        import mammoth
        with open(real_path, "rb") as f:
            result = mammoth.convert_to_html(f)
        body_html = result.value
    except Exception as e:
        body_html = f"<p style='color:red'>Could not convert document: {e}</p>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Resume Preview</title>
  <style>
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      max-width: 860px;
      margin: 0 auto;
      padding: 32px 24px;
      line-height: 1.6;
      color: #1a1a1a;
      background: #fff;
    }}
    h1 {{ font-size: 1.6rem; margin-bottom: 2px; }}
    h2 {{ font-size: 1.1rem; margin-top: 1.4em; border-bottom: 1px solid #ddd; padding-bottom: 3px; }}
    h3 {{ font-size: 1rem; margin-bottom: 2px; }}
    p  {{ margin: 4px 0; }}
    ul {{ padding-left: 20px; margin: 4px 0; }}
    li {{ margin-bottom: 3px; }}
    a  {{ color: #2563eb; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
  </style>
</head>
<body>
{body_html}
</body>
</html>"""

    return HTMLResponse(content=html)


@router.post("/upload", response_model=MatchAnalysisResponse)
async def upload_resume_and_jd(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    try:
        if not resume.filename:
            raise HTTPException(status_code=400, detail="Resume file must have a valid filename.")

        allowed_extensions = (".pdf", ".docx")
        if not resume.filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

        safe_filename = f"{uuid.uuid4()}_{resume.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as f:
            content = await resume.read()
            f.write(content)

        validated_jd = validate_job_description_input(job_description)

        result = analyze_resume_against_jd(
            file_path=file_path,
            filename=resume.filename,
            job_description=validated_jd,
        )

        # If analysis indicates the file doesn't look like a resume, return a clear 400
        if not result.get("is_likely_resume", True):
            raise HTTPException(status_code=400, detail=result.get("resume_file_warning") or "Uploaded file does not appear to be a resume.")

        # Inject the serve ID so the frontend can fetch the original file
        result["resume_serve_id"] = safe_filename

        # Hide certification coverage unless the JD explicitly requires certifications
        try:
            non_neg = evaluate_non_negotiables(result, validated_jd, saved_job=None)
            required_certs = non_neg.get("evaluated_rules", {}).get("mandatory_certifications", [])
            if not required_certs:
                result["cert_coverage"] = None
        except Exception:
            # On any evaluation error, fall back to including the cert coverage (safe default)
            pass

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/compare-jds", response_model=MultiJDCompareResponse)
async def compare_resume_with_multiple_jds(
    resume: UploadFile = File(...),
    job_descriptions_json: str = Form(...),
):
    try:
        if not resume.filename:
            raise HTTPException(
                status_code=400,
                detail="Resume file must have a valid filename."
            )

        allowed_extensions = (".pdf", ".docx")
        if not resume.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail="Only PDF and DOCX files are supported."
            )

        try:
            job_descriptions = json.loads(job_descriptions_json)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="job_descriptions_json must be a valid JSON array of job descriptions."
            )

        if not isinstance(job_descriptions, list) or len(job_descriptions) == 0:
            raise HTTPException(
                status_code=400,
                detail="Please provide at least one job description."
            )

        validated_job_descriptions = []
        for index, jd in enumerate(job_descriptions, start=1):
            try:
                validated_jd = validate_job_description_input(jd)
                validated_job_descriptions.append(validated_jd)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"JD {index}: {str(e)}"
                )

        safe_filename = f"{uuid.uuid4()}_{resume.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as f:
            content = await resume.read()
            f.write(content)

        # Quick content-based guardrail: ensure the uploaded file resembles a resume
        resume_text = extract_resume_text(file_path, resume.filename)
        is_likely, warning = is_likely_resume_text(resume_text)
        if not is_likely:
            raise HTTPException(status_code=400, detail=warning or "Uploaded file does not appear to be a resume.")

        result = compare_resume_against_multiple_jds(
            file_path=file_path,
            filename=resume.filename,
            job_descriptions=validated_job_descriptions,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/batch-upload", response_model=BatchAnalysisResponse)
async def batch_upload_resumes(
    resumes: List[UploadFile] = File(...),
    job_description: str = Form(...),
    job_id: str | None = Form(None),
):
    """
    Recruiter endpoint: upload multiple resumes against a single JD.
    Returns ranked candidates grouped into Shortlist / Review / Reject buckets.
    """
    try:
        batch_started_at = time.perf_counter()
        if not resumes or len(resumes) == 0:
            raise HTTPException(status_code=400, detail="Please upload at least one resume.")

        if len(resumes) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 resumes allowed per batch.")

        allowed_extensions = (".pdf", ".docx")
        for r in resumes:
            if not r.filename or not r.filename.lower().endswith(allowed_extensions):
                raise HTTPException(
                    status_code=400,
                    detail=f"'{r.filename}' is not a supported file type. Use PDF or DOCX."
                )

        validated_jd = validate_job_description_input(job_description)
        saved_job = None
        if job_id:
            saved_job = load_job_by_id(job_id)
            if not saved_job:
                raise HTTPException(status_code=404, detail="Saved job not found.")

        # Derive a JD title from first line of the validated JD
        first_line = validated_jd.strip().splitlines()[0][:80] if validated_jd.strip() else "Job Description"
        jd_title = saved_job.title if saved_job else first_line

        candidates: list[CandidateSummary] = []
        policy = get_screening_policy()
        bad_files: list[str] = []
        failed_files: list[str] = []
        file_outcomes: list[dict] = []

        logger.info(
            "Batch screening started",
            extra={
                "resume_count": len(resumes),
                "has_saved_job": bool(saved_job),
            },
        )

        for idx, resume_file in enumerate(resumes, start=1):
            file_started_at = time.perf_counter()
            safe_filename = f"{uuid.uuid4()}_{resume_file.filename}"
            file_path = os.path.join(UPLOAD_DIR, safe_filename)

            content = await resume_file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            try:
                # Quick content-based check before heavy analysis
                resume_text = extract_resume_text(file_path, resume_file.filename)
                is_likely, warning = is_likely_resume_text(resume_text)
                if not is_likely:
                    bad_files.append(resume_file.filename)
                    file_outcomes.append({
                        "filename": resume_file.filename,
                        "status": "skipped_non_resume",
                        "reason_code": "NON_RESUME_INPUT",
                        "message": warning or "File does not appear to be a resume.",
                    })
                    # Skip heavy analysis for this file
                    continue

                analysis = analyze_resume_against_jd(
                    file_path=file_path,
                    filename=resume_file.filename,
                    job_description=validated_jd,
                    include_llm_explanation=False,
                )
            except Exception as e:
                # Log and expose this file as failed analysis for transparency.
                logger.exception("Batch analysis failed", extra={"filename": resume_file.filename})
                failed_files.append(resume_file.filename)
                file_outcomes.append({
                    "filename": resume_file.filename,
                    "status": "failed_analysis",
                    "reason_code": "ANALYSIS_EXCEPTION",
                    "message": "The file could not be analyzed. Please retry or inspect file format/content.",
                })
                continue

            logger.info(
                "Batch candidate analyzed",
                extra={
                    "filename": resume_file.filename,
                    "elapsed_ms": round((time.perf_counter() - file_started_at) * 1000, 1),
                },
            )

            scores = analysis["scores"]
            ats_audit = analysis["ats_audit"]
            keyword_coverage = analysis["keyword_coverage"]
            shortlist_simulation = analysis["shortlist_simulation"]
            experience_estimate = analysis["experience_estimate"]
            experience_comparison = analysis["experience_comparison"]
            non_negotiable_result = evaluate_non_negotiables(
                analysis=analysis,
                job_description=validated_jd,
                saved_job=saved_job.model_dump() if saved_job else None,
            )

            overall = round(scores["overall_score"], 1)
            if non_negotiable_result["hard_reject"]:
                bucket = "Reject"
            else:
                bucket = bucket_label(overall)

            candidate_id = str(uuid.uuid4())

            candidate = CandidateSummary(
                candidate_id=candidate_id,
                candidate_index=idx,
                filename=resume_file.filename,
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
                    non_negotiable_result["hard_reject_reasons"][:4]
                    if non_negotiable_result["hard_reject_reasons"]
                    else shortlist_simulation.get("reasons", [])[:4]
                ),
                ats_issues_count=len(ats_audit.get("issues", [])),
                keyword_strong_count=keyword_coverage.get("summary", {}).get("strong_count", 0),
                keyword_missing_count=keyword_coverage.get("summary", {}).get("missing_count", 0),
                recommendation=analysis.get("recommendation"),
                linkedin_url=analysis.get("structured_resume", {}).get("linkedin") or None,
                # New recruiter-focused fields
                career_progression_score=round(scores.get("career_progression_score", 0.0), 1),
                achievements_score=round(scores.get("achievements_score", 0.0), 1),
                industry_fit_score=round(scores.get("industry_fit_score", 0.0), 1),
                leadership_signals=scores.get("leadership_signals", []),
                red_flags=scores.get("red_flags", []),
                language_quality=scores.get("language_quality", {}),
                over_tailoring_flag=scores.get("over_tailoring_flag", False),
                # Education fit & non-negotiable advisory flags
                education_meets_requirement=analysis.get("education_fit", {}).get("meets_requirement"),
                non_negotiable_flags=analysis.get("non_negotiable_flags", []),
                seniority_level=analysis.get("seniority_level", "mid"),
                # Serve ID for original file download
                resume_serve_id=safe_filename,
                # Evidence summary for detail panel
                evidence_summary={
                    "strong_evidence_skills": analysis.get("evidence_summary", {}).get("strong_evidence_skills", []),
                    "medium_evidence_skills": analysis.get("evidence_summary", {}).get("medium_evidence_skills", []),
                    "weak_evidence_skills": analysis.get("evidence_summary", {}).get("weak_evidence_skills", []),
                    "skill_support_score": analysis.get("evidence_summary", {}).get("skill_support_score", 0),
                },
                # Timeline gap analysis flags
                timeline_gaps=[
                    *[f"Short tenure: {s}" for s in analysis.get("timeline_analysis", {}).get("short_tenure_flags", [])],
                    *[
                        f"Gap of {g['months']}mo between roles ({g['from']} – {g['to']})"
                        for g in analysis.get("timeline_analysis", {}).get("gaps", [])
                        if g["months"] >= 3
                    ],
                ],
                # Full ATS issues for drill-down
                ats_issues=[
                    {"title": issue.get("title", ""), "severity": issue.get("severity", ""),
                     "details": issue.get("details", ""), "recommendation": issue.get("recommendation", "")}
                    for issue in analysis.get("ats_audit", {}).get("issues", [])
                ],
                # Keyword coverage items for drill-down (strong + missing only to keep payload manageable)
                keyword_coverage_items=[
                    {"skill": item.get("skill", ""), "status": item.get("status", ""),
                     "priority": item.get("priority", ""),
                     "evidence_sections": item.get("evidence_sections", []),
                     "supporting_lines": item.get("supporting_lines", [])}
                    for item in analysis.get("keyword_coverage", {}).get("items", [])
                    if item.get("status") in ("strong", "missing")
                ],
                primary_coverage=round(scores.get("primary_coverage", 0), 1),
                primary_coverage_source=scores.get("primary_coverage_source", "required"),
                required_skills_count=int(scores.get("required_skills_count", 0)),
                required_skills_matched_count=int(scores.get("required_skills_matched_count", 0)),
                non_negotiable_verdict=non_negotiable_result["non_negotiable_verdict"],
                non_negotiable_reasons=non_negotiable_result["hard_reject_reasons"],
                review_flags=non_negotiable_result["review_flags"],
                # Only surface certification coverage when the JD/saved job explicitly
                # requires certifications. Otherwise hide the panel while still
                # using certs as evidence for skills elsewhere.
                cert_coverage=(analysis.get("cert_coverage") if non_negotiable_result
                               .get("evaluated_rules", {}).get("mandatory_certifications") else None),
            )
            candidates.append(candidate)
            file_outcomes.append({
                "filename": resume_file.filename,
                "status": "analyzed",
            })

        if not candidates:
            if bad_files:
                raise HTTPException(
                    status_code=400,
                    detail=f"The following files do not appear to be resumes: {', '.join(bad_files)}. Please upload PDF or DOCX resumes."
                )
            raise HTTPException(status_code=422, detail="None of the uploaded resumes could be analyzed.")

        candidates.sort(key=lambda c: c.overall_score, reverse=True)

        shortlisted = [c for c in candidates if c.shortlist_verdict == "Shortlist"]
        review = [c for c in candidates if c.shortlist_verdict == "Review"]
        rejected = [c for c in candidates if c.shortlist_verdict == "Reject"]

        logger.info(
            "Batch screening completed",
            extra={
                "resume_count": len(resumes),
                "candidate_count": len(candidates),
                "skipped_count": len(bad_files),
                "failed_count": len(failed_files),
                "elapsed_ms": round((time.perf_counter() - batch_started_at) * 1000, 1),
            },
        )

        return BatchAnalysisResponse(
            jd_title=jd_title,
            total_candidates=len(candidates),
            policy=policy,
            shortlisted=shortlisted,
            review=review,
            rejected=rejected,
            all_candidates=candidates,
            skipped_files=bad_files,
            failed_files=failed_files,
            file_outcomes=file_outcomes,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ── Candidate Status Tracking ───────────────────────────────────────────────

from datetime import datetime
from app.models.schemas import CandidateStatusUpdate, CandidateStatus, StatusHistoryEntry

# Absolute path — works regardless of working directory
_STATUS_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
os.makedirs(_STATUS_DATA_DIR, exist_ok=True)
CANDIDATE_STATUS_FILE = os.path.join(_STATUS_DATA_DIR, "candidate_statuses.json")
_STATUS_LOCK = threading.Lock()


def _load_candidate_statuses() -> dict:
    """Load candidate statuses from JSON file."""
    if not os.path.exists(CANDIDATE_STATUS_FILE):
        return {}
    try:
        with open(CANDIDATE_STATUS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"candidate status data file is corrupted: {e}")


def _save_candidate_statuses(statuses: dict):
    """Save candidate statuses to JSON file."""
    with _STATUS_LOCK:
        with tempfile.NamedTemporaryFile("w", dir=_STATUS_DATA_DIR, delete=False) as tf:
            json.dump(statuses, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
            temp_name = tf.name
        os.replace(temp_name, CANDIDATE_STATUS_FILE)


@router.post("/candidate/status")
def update_candidate_status(status_update: CandidateStatusUpdate):
    """Update the hiring status of a candidate and record in history."""
    try:
        statuses = _load_candidate_statuses()
        
        candidate_id = status_update.candidate_id
        
        # Initialize candidate if not exists
        if candidate_id not in statuses:
            statuses[candidate_id] = {
                "candidate_id": candidate_id,
                "status": "New",
                "status_history": []
            }
        
        candidate_data = statuses[candidate_id]
        
        # Add to history
        history_entry = StatusHistoryEntry(
            status=status_update.status.value,
            changed_at=datetime.utcnow().isoformat(),
            changed_by="default",  # In real app, get from auth context
            note=status_update.note
        )
        
        candidate_data["status"] = status_update.status.value
        candidate_data["status_history"].append(history_entry.model_dump())
        
        statuses[candidate_id] = candidate_data
        _save_candidate_statuses(statuses)
        
        return {
            "message": "Status updated successfully",
            "candidate_id": candidate_id,
            "new_status": status_update.status.value,
            "history": candidate_data["status_history"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.get("/candidate/{candidate_id}/status")
def get_candidate_status(candidate_id: str):
    """Get the current status and history for a candidate."""
    try:
        statuses = _load_candidate_statuses()
        
        if candidate_id not in statuses:
            return {
                "candidate_id": candidate_id,
                "status": "New",
                "status_history": []
            }
        
        return statuses[candidate_id]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/candidate/statuses")
def get_candidate_statuses(payload: CandidateStatusBatchRequest):
    """Get statuses for multiple candidates in one request."""
    try:
        statuses = _load_candidate_statuses()
        result = {}
        for candidate_id in payload.candidate_ids:
            result[candidate_id] = statuses.get(candidate_id, {
                "candidate_id": candidate_id,
                "status": "New",
                "status_history": [],
            })
        return {"statuses": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statuses: {str(e)}")
