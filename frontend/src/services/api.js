export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

const REQUEST_TIMEOUT_MS = 300000

function buildApiUrl(endpoint) {
  return `${API_BASE_URL}${endpoint}`
}

function createRequestError(message, code) {
  const error = new Error(message)
  if (code) error.code = code
  return error
}

function getTimeoutErrorMessage(endpoint) {
  if (endpoint === '/matcher/batch-upload') {
    return 'Screening is taking longer than expected. Please try a smaller batch or retry in a moment.'
  }

  return 'The request took too long to finish. Please retry.'
}

async function fetchWithTimeout(url, options = {}, timeoutMessage) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(timeoutMessage)
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}

async function postForm(endpoint, formData) {
  const requestUrl = buildApiUrl(endpoint)
  let response

  try {
    response = await fetchWithTimeout(
      requestUrl,
      {
        method: 'POST',
        body: formData,
      },
      getTimeoutErrorMessage(endpoint)
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${requestUrl}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }

  if (!response.ok) {
    let errorMessage = 'Something went wrong while processing your request.'
    try {
      const errorData = await response.json()
      if (errorData.detail) errorMessage = errorData.detail
    } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
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

export async function validateResumeFile(file) {
  const formData = new FormData()
  formData.append('resume', file)
  return postForm('/matcher/validate-resume-file', formData)
}

export async function incrementVisitorCount() {
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl('/matcher/visitor-count/increment'),
      {
        method: 'POST',
      },
      'Updating the visitor counter took too long.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl('/matcher/visitor-count/increment')}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }

  if (!response.ok) {
    let errorMessage = 'Failed to update visitor count.'
    try {
      const errorData = await response.json()
      if (errorData.detail) errorMessage = errorData.detail
    } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
    throw new Error(errorMessage)
  }

  return response.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// Ingest (Power Automate / email intake)

function getIngestHeaders() {
  const secret = import.meta.env.VITE_INGEST_SECRET || ''
  return secret ? { 'X-Ingest-Secret': secret } : {}
}

export async function ingestUploadFile(file, { recruiterEmail = '', messageId = '', subject = '', jobDescription = '', jobId = '' } = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('recruiter_email', recruiterEmail)
  formData.append('message_id', messageId)
  formData.append('subject', subject)
  formData.append('job_description', jobDescription)
  formData.append('job_id', jobId)
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl('/ingest/upload'),
      { method: 'POST', body: formData, headers: getIngestHeaders() },
      'Ingest upload timed out.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl('/ingest/upload')}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }
  if (!response.ok) {
    let msg = 'Ingest upload failed.'
    try { const d = await response.json(); if (d.detail) msg = d.detail } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
    throw new Error(msg)
  }
  return response.json()
}

export async function listIngestJobs(limit = 100) {
  let response
  try {
    response = await fetchWithTimeout(
      `${buildApiUrl('/ingest/jobs')}?limit=${limit}`,
      { method: 'GET', headers: getIngestHeaders() },
      'Fetching ingest jobs timed out.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl('/ingest/jobs')}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }
  if (!response.ok) throw new Error('Failed to fetch ingest jobs.')
  return response.json()
}

export async function getIngestTargetJob() {
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl('/ingest/target-job'),
      { method: 'GET', headers: getIngestHeaders() },
      'Fetching Email Intake target job timed out.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl('/ingest/target-job')}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }
  if (!response.ok) {
    let msg = 'Failed to fetch Email Intake target job.'
    try { const d = await response.json(); if (d.detail) msg = d.detail } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
    throw new Error(msg)
  }
  return response.json()
}

export async function setIngestTargetJob(jobId = '') {
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl('/ingest/target-job'),
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getIngestHeaders(),
        },
        body: JSON.stringify({ job_id: jobId }),
      },
      'Saving Email Intake target job timed out.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl('/ingest/target-job')}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }
  if (!response.ok) {
    let msg = 'Failed to save Email Intake target job.'
    try { const d = await response.json(); if (d.detail) msg = d.detail } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
    throw new Error(msg)
  }
  return response.json()
}

export async function analyzeIngestJob(ingestId, jobDescription, jobId = '') {
  const formData = new FormData()
  formData.append('job_description', jobDescription)
  formData.append('job_id', jobId)
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl(`/ingest/analyze/${ingestId}`),
      { method: 'POST', body: formData, headers: getIngestHeaders() },
      'Analysis timed out.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl(`/ingest/analyze/${ingestId}`)}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }
  if (!response.ok) {
    let msg = 'Analysis failed.'
    try { const d = await response.json(); if (d.detail) msg = d.detail } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
    throw new Error(msg)
  }
  return response.json()
}

export async function deleteIngestJob(ingestId) {
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl(`/ingest/jobs/${ingestId}`),
      { method: 'DELETE', headers: getIngestHeaders() },
      'Delete timed out.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl(`/ingest/jobs/${ingestId}`)}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }
  if (!response.ok) {
    let msg = 'Failed to delete ingest job.'
    try { const d = await response.json(); if (d.detail) msg = d.detail } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
    throw new Error(msg)
  }
  return response.json()
}

// ─────────────────────────────────────────────────────────────────────────────
// Job Management
// ─────────────────────────────────────────────────────────────────────────────

async function fetchJSON(url, options = {}) {
  let response
  try {
    response = await fetchWithTimeout(
      buildApiUrl(url),
      {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      },
      'The request took too long to finish. Please retry.'
    )
  } catch (error) {
    if (error?.name === 'TypeError') {
      throw createRequestError(
        `Could not reach the backend at ${buildApiUrl(url)}. Start the backend server or update VITE_API_BASE_URL.`,
        'API_UNREACHABLE'
      )
    }
    throw error
  }

  if (!response.ok) {
    let errorMessage = 'Request failed.'
    try {
      const errorData = await response.json()
      if (errorData.detail) errorMessage = errorData.detail
    } catch {
      // Ignore non-JSON error bodies and keep the fallback message.
    }
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

export const fetchJobs = listJobs
