"""
Job Management API Routes
────────────────────────────
Handles CRUD operations for job descriptions:
- Create new jobs
- List all jobs
- Get job by ID
- Update existing jobs
- Delete jobs
- Clone jobs
"""

import os
import json
import uuid
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.models.schemas import Job, JobCreate, JobUpdate, JobListResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Absolute path — works regardless of working directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DATA_FILE = DATA_DIR / "jobs.json"
_JOBS_LOCK = threading.Lock()


def _load_jobs() -> dict:
    """Load jobs from JSON file."""
    if not JOBS_DATA_FILE.exists():
        return {}
    try:
        with open(JOBS_DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"jobs data file is corrupted: {e}")


def _save_jobs(jobs: dict):
    """Save jobs to JSON file."""
    with _JOBS_LOCK:
        with tempfile.NamedTemporaryFile("w", dir=str(DATA_DIR), delete=False) as tf:
            json.dump(jobs, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
            temp_name = tf.name
        os.replace(temp_name, JOBS_DATA_FILE)


def load_job_by_id(job_id: str) -> Job | None:
    """Shared helper for reading a saved job record by id."""
    jobs = _load_jobs()
    job_data = jobs.get(job_id)
    if not job_data:
        return None
    return Job(**job_data)


@router.post("/", response_model=Job)
def create_job(job_data: JobCreate):
    """Create a new job description."""
    try:
        jobs = _load_jobs()
        
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        job = Job(
            job_id=job_id,
            title=job_data.title,
            description=job_data.description,
            required_skills=job_data.required_skills,
            preferred_skills=job_data.preferred_skills,
            min_experience=job_data.min_experience,
            education_requirements=job_data.education_requirements or [],
            mandatory_certifications=job_data.mandatory_certifications or [],
            tags=job_data.tags or [],
            created_at=now,
            updated_at=now,
            recruiter_id="default"
        )
        
        jobs[job_id] = job.model_dump()
        _save_jobs(jobs)
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.get("/", response_model=JobListResponse)
def list_jobs():
    """List all saved job descriptions."""
    try:
        jobs = _load_jobs()
        job_list = [Job(**job_data) for job_data in jobs.values()]
        # Sort by created_at descending
        job_list.sort(key=lambda x: x.created_at, reverse=True)
        
        return JobListResponse(
            jobs=job_list,
            total=len(job_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str):
    """Get a specific job by ID."""
    try:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        return Job(**jobs[job_id])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@router.put("/{job_id}", response_model=Job)
def update_job(job_id: str, job_update: JobUpdate):
    """Update an existing job."""
    try:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        current_job = jobs[job_id]
        
        # Update only provided fields
        if job_update.title is not None:
            current_job["title"] = job_update.title
        if job_update.description is not None:
            current_job["description"] = job_update.description
        if job_update.required_skills is not None:
            current_job["required_skills"] = job_update.required_skills
        if job_update.preferred_skills is not None:
            current_job["preferred_skills"] = job_update.preferred_skills
        if job_update.min_experience is not None:
            current_job["min_experience"] = job_update.min_experience
        if job_update.education_requirements is not None:
            current_job["education_requirements"] = job_update.education_requirements
        if job_update.mandatory_certifications is not None:
            current_job["mandatory_certifications"] = job_update.mandatory_certifications
        if job_update.tags is not None:
            current_job["tags"] = job_update.tags
        
        current_job["updated_at"] = datetime.utcnow().isoformat()
        
        jobs[job_id] = current_job
        _save_jobs(jobs)
        
        return Job(**current_job)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update job: {str(e)}")


@router.delete("/{job_id}")
def delete_job(job_id: str):
    """Delete a job."""
    try:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        deleted_job = jobs.pop(job_id)
        _save_jobs(jobs)
        
        return {"message": "Job deleted successfully", "job_id": job_id, "title": deleted_job["title"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")


@router.post("/{job_id}/clone", response_model=Job)
def clone_job(job_id: str):
    """Clone an existing job with a new ID."""
    try:
        jobs = _load_jobs()
        
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        original_job = jobs[job_id]
        new_job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        cloned_job = Job(
            job_id=new_job_id,
            title=f"{original_job['title']} (Copy)",
            description=original_job["description"],
            required_skills=original_job["required_skills"],
            preferred_skills=original_job["preferred_skills"],
            min_experience=original_job.get("min_experience"),
            education_requirements=original_job.get("education_requirements", []),
            mandatory_certifications=original_job.get("mandatory_certifications", []),
            tags=original_job.get("tags", []),
            created_at=now,
            updated_at=now,
            recruiter_id="default"
        )
        
        jobs[new_job_id] = cloned_job.model_dump()
        _save_jobs(jobs)
        
        return cloned_job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone job: {str(e)}")
