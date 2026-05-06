export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

async function postForm(endpoint, formData) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let errorMessage = 'Something went wrong while processing your request.'
    try {
      const errorData = await response.json()
      if (errorData.detail) errorMessage = errorData.detail
    } catch {}
    throw new Error(errorMessage)
  }

  return response.json()
}

export async function analyzeResume(formData) {
  return postForm('/matcher/upload', formData)
}

export async function tailorResume(formData) {
  return postForm('/matcher/tailor-resume', formData)
}

export async function compareMultipleJDs(formData) {
  return postForm('/matcher/compare-jds', formData)
}

export async function batchAnalyzeResumes(formData) {
  return postForm('/matcher/batch-upload', formData)
}

export async function incrementVisitorCount() {
  const response = await fetch(`${API_BASE_URL}/matcher/visitor-count/increment`, {
    method: 'POST',
  })

  if (!response.ok) {
    let errorMessage = 'Failed to update visitor count.'
    try {
      const errorData = await response.json()
      if (errorData.detail) errorMessage = errorData.detail
    } catch {}
    throw new Error(errorMessage)
  }

  return response.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// Job Management
// ─────────────────────────────────────────────────────────────────────────────

async function fetchJSON(url, options = {}) {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    let errorMessage = 'Request failed.'
    try {
      const errorData = await response.json()
      if (errorData.detail) errorMessage = errorData.detail
    } catch {}
    throw new Error(errorMessage)
  }

  return response.json()
}

export async function createJob(jobData) {
  return fetchJSON('/jobs/', {
    method: 'POST',
    body: JSON.stringify(jobData),
  })
}

export async function listJobs() {
  return fetchJSON('/jobs/')
}

export async function getJob(jobId) {
  return fetchJSON(`/jobs/${jobId}`)
}

export async function updateJob(jobId, jobData) {
  return fetchJSON(`/jobs/${jobId}`, {
    method: 'PUT',
    body: JSON.stringify(jobData),
  })
}

export async function deleteJob(jobId) {
  return fetchJSON(`/jobs/${jobId}`, {
    method: 'DELETE',
  })
}

export async function cloneJob(jobId) {
  return fetchJSON(`/jobs/${jobId}/clone`, {
    method: 'POST',
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Recruiter Notes
// ─────────────────────────────────────────────────────────────────────────────

export async function createNote(candidateId, content) {
  return fetchJSON('/notes/', {
    method: 'POST',
    body: JSON.stringify({ candidate_id: candidateId, content }),
  })
}

export async function getCandidateNotes(candidateId) {
  return fetchJSON(`/notes/candidate/${candidateId}`)
}

export async function updateNote(noteId, content) {
  return fetchJSON(`/notes/${noteId}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
}

export async function deleteNote(noteId) {
  return fetchJSON(`/notes/${noteId}`, {
    method: 'DELETE',
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Candidate Status Tracking
// ─────────────────────────────────────────────────────────────────────────────

export async function updateCandidateStatus(candidateId, status, note = null) {
  return fetchJSON('/matcher/candidate/status', {
    method: 'POST',
    body: JSON.stringify({ candidate_id: candidateId, status, note }),
  })
}

export async function getCandidateStatus(candidateId) {
  return fetchJSON(`/matcher/candidate/${candidateId}/status`)
}

export async function getCandidateStatuses(candidateIds) {
  return fetchJSON('/matcher/candidate/statuses', {
    method: 'POST',
    body: JSON.stringify({ candidate_ids: candidateIds }),
  })
}