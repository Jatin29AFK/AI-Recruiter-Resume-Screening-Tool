"""
Recruiter Notes API Routes
───────────────────────────
Handles CRUD operations for internal recruiter notes on candidates:
- Create notes
- List notes by candidate
- Update notes
- Delete notes
"""

import os
import json
import uuid
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.models.schemas import RecruiterNote, NoteCreate, NoteUpdate, NoteListResponse

router = APIRouter(prefix="/notes", tags=["Notes"])

# Absolute path — works regardless of working directory
_DATA_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DATA_FILE = str(_DATA_DIR / "recruiter_notes.json")
_NOTES_LOCK = threading.Lock()


def _load_notes() -> dict:
    """Load notes from JSON file."""
    if not os.path.exists(NOTES_DATA_FILE):
        return {}
    try:
        with open(NOTES_DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"notes data file is corrupted: {e}")


def _save_notes(notes: dict):
    """Save notes to JSON file."""
    with _NOTES_LOCK:
        with tempfile.NamedTemporaryFile("w", dir=str(_DATA_DIR), delete=False) as tf:
            json.dump(notes, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
            temp_name = tf.name
        os.replace(temp_name, NOTES_DATA_FILE)


@router.post("/", response_model=RecruiterNote)
def create_note(note_data: NoteCreate):
    """Create a new recruiter note for a candidate."""
    try:
        notes = _load_notes()
        
        note_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        note = RecruiterNote(
            note_id=note_id,
            candidate_id=note_data.candidate_id,
            recruiter_id="default",  # In real app, get from auth context
            content=note_data.content,
            created_at=now,
            updated_at=now
        )
        
        notes[note_id] = note.model_dump()
        _save_notes(notes)
        
        return note
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")


@router.get("/candidate/{candidate_id}", response_model=NoteListResponse)
def list_candidate_notes(candidate_id: str):
    """List all notes for a specific candidate."""
    try:
        notes = _load_notes()
        
        candidate_notes = [
            RecruiterNote(**note_data)
            for note_data in notes.values()
            if note_data["candidate_id"] == candidate_id
        ]
        
        # Sort by created_at descending (newest first)
        candidate_notes.sort(key=lambda x: x.created_at, reverse=True)
        
        return NoteListResponse(
            notes=candidate_notes,
            total=len(candidate_notes)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list notes: {str(e)}")


@router.put("/{note_id}", response_model=RecruiterNote)
def update_note(note_id: str, note_update: NoteUpdate):
    """Update an existing note."""
    try:
        notes = _load_notes()
        
        if note_id not in notes:
            raise HTTPException(status_code=404, detail="Note not found")
        
        current_note = notes[note_id]
        current_note["content"] = note_update.content
        current_note["updated_at"] = datetime.utcnow().isoformat()
        
        notes[note_id] = current_note
        _save_notes(notes)
        
        return RecruiterNote(**current_note)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update note: {str(e)}")


@router.delete("/{note_id}")
def delete_note(note_id: str):
    """Delete a note."""
    try:
        notes = _load_notes()
        
        if note_id not in notes:
            raise HTTPException(status_code=404, detail="Note not found")
        
        deleted_note = notes.pop(note_id)
        _save_notes(notes)
        
        return {"message": "Note deleted successfully", "note_id": note_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {str(e)}")
