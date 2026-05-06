/**
 * NotesPanel Component
 * ────────────────────
 * Internal recruiter notes for candidates
 * - Create new notes
 * - View note history
 * - Edit/delete notes
 * - No applicant visibility
 */

import { useState, useEffect } from 'react'
import { getCandidateNotes, createNote, updateNote, deleteNote } from '../services/api'

export default function NotesPanel({ candidateId, candidateName }) {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [newNoteContent, setNewNoteContent] = useState('')
  const [editingNote, setEditingNote] = useState(null)

  useEffect(() => {
    if (candidateId) {
      loadNotes()
    }
  }, [candidateId])

  const loadNotes = async () => {
    try {
      setLoading(true)
      const response = await getCandidateNotes(candidateId)
      setNotes(response.notes || [])
    } catch (error) {
      console.error('Failed to load notes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateNote = async (e) => {
    e.preventDefault()
    
    if (!newNoteContent.trim()) return

    try {
      await createNote(candidateId, newNoteContent.trim())
      setNewNoteContent('')
      loadNotes()
    } catch (error) {
      alert(`Failed to create note: ${error.message}`)
    }
  }

  const handleUpdateNote = async (noteId, content) => {
    try {
      await updateNote(noteId, content)
      setEditingNote(null)
      loadNotes()
    } catch (error) {
      alert(`Failed to update note: ${error.message}`)
    }
  }

  const handleDeleteNote = async (noteId) => {
    if (!confirm('Delete this note?')) return

    try {
      await deleteNote(noteId)
      loadNotes()
    } catch (error) {
      alert(`Failed to delete note: ${error.message}`)
    }
  }

  const formatDate = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-4">
      
      {/* Header */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">
          🗒 Internal Notes
        </h3>
        <p className="mt-0.5 text-xs text-gray-400 dark:text-slate-500">
          Private recruiter notes • Not visible to candidates
        </p>
      </div>

      {/* Create Note Form */}
      <form onSubmit={handleCreateNote} className="space-y-2">
        <textarea
          placeholder="Add a private note about this candidate..."
          value={newNoteContent}
          onChange={(e) => setNewNoteContent(e.target.value)}
          rows="3"
          className="w-full rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-4 py-2 text-sm resize-none focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        />
        <button
          type="submit"
          disabled={!newNoteContent.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add Note
        </button>
      </form>

      {/* Notes List */}
      {loading ? (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400 text-sm">Loading notes...</div>
      ) : notes.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400 text-sm">
          No notes yet. Add one above to keep track of your observations.
        </div>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <div
              key={note.note_id}
              className="rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 p-4"
            >
              {editingNote === note.note_id ? (
                <div className="space-y-2">
                  <textarea
                    defaultValue={note.content}
                    rows="3"
                    id={`edit-${note.note_id}`}
                    className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm resize-none"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        const content = document.getElementById(`edit-${note.note_id}`).value
                        handleUpdateNote(note.note_id, content)
                      }}
                      className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingNote(null)}
                      className="rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-3">
                    <p className="flex-1 text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                      {note.content}
                    </p>
                    <div className="flex gap-1">
                      <button
                        onClick={() => setEditingNote(note.note_id)}
                        className="rounded-lg border border-gray-300 dark:border-slate-600 px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700"
                        title="Edit note"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteNote(note.note_id)}
                        className="rounded-lg border border-red-300 dark:border-red-800 px-2 py-1 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950"
                        title="Delete note"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                  
                  <div className="mt-2 flex items-center gap-3 text-xs text-gray-500 dark:text-slate-400">
                    <span>{formatDate(note.created_at)}</span>
                    {note.updated_at !== note.created_at && (
                      <span className="text-xs text-gray-400 dark:text-slate-500">
                        (edited {formatDate(note.updated_at)})
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}