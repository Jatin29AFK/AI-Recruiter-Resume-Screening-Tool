import { useRef, useState } from 'react'
import {
  validateJobDescriptionInput,
  sanitizeJobDescriptionInput,
} from '../utils/jdValidation'
import { validateResumeFile } from '../services/api'
import JobManager from './JobManager'

const MAX_BATCH_RESUMES = 100
const ALLOWED_EXTENSIONS = new Set(['.pdf', '.docx'])
const ALLOWED_MIME_TYPES = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/octet-stream',
  '',
])

function isSupportedResumeFile(file) {
  const dotIndex = file.name.lastIndexOf('.')
  const ext = dotIndex >= 0 ? file.name.slice(dotIndex).toLowerCase() : ''
  const hasAllowedExt = ALLOWED_EXTENSIONS.has(ext)
  const hasAllowedMime = ALLOWED_MIME_TYPES.has((file.type || '').toLowerCase())
  return hasAllowedExt && hasAllowedMime
}

export default function UploadForm({ onBatchAnalyze, loading }) {
  const batchFileInputRef = useRef(null)

  // multi-resume state
  const [resumeFiles, setResumeFiles] = useState([])
  const [batchFileError, setBatchFileError] = useState('')
  const [isDraggingBatch, setIsDraggingBatch] = useState(false)
  const [isValidatingFiles, setIsValidatingFiles] = useState(false)

  // job description
  const [jobDescription, setJobDescription] = useState('')
  const [jdError, setJdError] = useState('')
  const [showJobManager, setShowJobManager] = useState(false)
  const [selectedJob, setSelectedJob] = useState(null)

  // Add files: perform local extension checks, then call backend quick-validate
  const addBatchFiles = async (newFiles) => {
    const validByType = []
    const invalid = []
    const duplicates = []

    Array.from(newFiles).forEach((f) => {
      if (!isSupportedResumeFile(f)) {
        invalid.push(f.name)
      } else {
        validByType.push(f)
      }
    })

    const deduplicated = []
    for (const f of validByType) {
      const isDuplicate = resumeFiles.some(
        (existing) => existing.name === f.name && existing.size === f.size
      ) || deduplicated.some(
        (existing) => existing.name === f.name && existing.size === f.size
      )
      if (isDuplicate) {
        duplicates.push(f.name)
      } else {
        deduplicated.push(f)
      }
    }

    if (deduplicated.length === 0) {
      if (invalid.length && duplicates.length) {
        setBatchFileError(
          `Unsupported: ${invalid.join(', ')}. Already added: ${duplicates.join(', ')}.`
        )
      } else if (invalid.length) {
        setBatchFileError(`Unsupported file(s): ${invalid.join(', ')}. Use PDF or DOCX.`)
      } else if (duplicates.length) {
        setBatchFileError(`Already added (skipped): ${duplicates.join(', ')}`)
      }
      return
    }

    setIsValidatingFiles(true)
    const rejectedByContent = []
    const acceptedByContent = []
    const validationWarnings = []

    try {
      const checks = await Promise.all(
        deduplicated.map(async (file) => {
          try {
            const validation = await validateResumeFile(file)
            return { file, validation, error: null }
          } catch (error) {
            return {
              file,
              validation: null,
              error,
            }
          }
        })
      )

      checks.forEach(({ file, validation, error }) => {
        if (error) {
          if (error?.code === 'API_UNREACHABLE') {
            acceptedByContent.push(file)
            validationWarnings.push(file.name)
            return
          }
          rejectedByContent.push(`${file.name} (${error?.message || 'Could not validate this file.'})`)
          return
        }
        if (!validation?.is_valid_resume || validation?.final_label === 'reject') {
          rejectedByContent.push(
            `${file.name} (${validation?.warning_message || 'Detected as non-resume document.'})`
          )
          return
        }
        acceptedByContent.push(file)
      })
    } finally {
      setIsValidatingFiles(false)
    }

    const uniqueAccepted = acceptedByContent.filter(
      (candidate) =>
        !resumeFiles.some(
          (existing) => existing.name === candidate.name && existing.size === candidate.size
        )
    )
    const remainingSlots = Math.max(0, MAX_BATCH_RESUMES - resumeFiles.length)
    const toAdd = uniqueAccepted.slice(0, remainingSlots)
    const overflow = uniqueAccepted.slice(remainingSlots).map((f) => f.name)

    if (toAdd.length > 0) {
      setResumeFiles((prev) => [...prev, ...toAdd])
    }

    const parts = []
    if (invalid.length) {
      parts.push(`Unsupported file(s): ${invalid.join(', ')}. Use PDF or DOCX.`)
    }
    if (duplicates.length) {
      parts.push(`Already added (skipped): ${duplicates.join(', ')}`)
    }
    if (rejectedByContent.length) {
      parts.push(`Skipped non-resume file(s): ${rejectedByContent.join('; ')}`)
    }
    if (validationWarnings.length) {
      parts.push(
        `Backend validation was unavailable for: ${validationWarnings.join(', ')}. These files were still added and will be checked during screening.`
      )
    }
    if (overflow.length) {
      parts.push(
        `Maximum ${MAX_BATCH_RESUMES} resumes allowed. Not added: ${overflow.join(', ')}.`
      )
    }

    setBatchFileError(parts.join(' '))
  }

  const handleBatchFileChange = async (e) => {
    await addBatchFiles(e.target.files)
    if (batchFileInputRef.current) batchFileInputRef.current.value = ''
  }

  const removeBatchFile = (index) => {
    setResumeFiles((prev) => prev.filter((_, i) => i !== index))
    setBatchFileError('')
  }

  const handleBatchDragOver = (e) => {
    e.preventDefault()
    setIsDraggingBatch(true)
  }

  const handleBatchDragLeave = (e) => {
    e.preventDefault()
    setIsDraggingBatch(false)
  }

  const handleBatchDrop = (e) => {
    e.preventDefault()
    setIsDraggingBatch(false)
    void addBatchFiles(e.dataTransfer.files)
  }

  // ── JD input ───────────────────────────────────────────────────────────────
  const handleJdChange = (e) => {
    const cleaned = sanitizeJobDescriptionInput(e.target.value)
    setJobDescription(cleaned)
    if (selectedJob) setSelectedJob(null)
    if (jdError) setJdError(validateJobDescriptionInput(cleaned))
  }

  const handleSelectSavedJob = (job) => {
    const cleaned = sanitizeJobDescriptionInput(job.description || '')
    setJobDescription(cleaned)
    setSelectedJob(job)
    setJdError(validateJobDescriptionInput(cleaned))
  }

  // ── Submit ─────────────────────────────────────────────────────────────────
  const handleSubmit = (e) => {
    e.preventDefault()
    const cleanedJd = sanitizeJobDescriptionInput(jobDescription)
    const nextJdError = validateJobDescriptionInput(cleanedJd)
    setJdError(nextJdError)

    if (resumeFiles.length === 0) {
      setBatchFileError('Please upload at least one resume.')
      return
    }
    if (nextJdError) return

    const formData = new FormData()
    resumeFiles.forEach((f) => formData.append('resumes', f))
    formData.append('job_description', cleanedJd)
    if (selectedJob?.job_id) {
      formData.append('job_id', selectedJob.job_id)
    }
    onBatchAnalyze(formData)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[0_18px_55px_rgba(15,23,42,0.08)] ring-1 ring-slate-900/5 dark:border-slate-700 dark:bg-slate-900 dark:ring-white/10"
    >

      {/* ── Multi-resume upload ── */}
      {
        <div className="space-y-3">
          <label className="text-sm font-black tracking-tight text-slate-950 dark:text-white">
            Upload Candidate Resumes
            <span className="ml-2 text-xs font-normal text-gray-500 dark:text-slate-400">
              (up to {MAX_BATCH_RESUMES} PDFs / DOCXs)
            </span>
          </label>

          <div
            onClick={() => batchFileInputRef.current?.click()}
            onDragOver={handleBatchDragOver}
            onDragLeave={handleBatchDragLeave}
            onDrop={handleBatchDrop}
            className={`group flex cursor-pointer flex-col items-center justify-center rounded-3xl border px-6 py-10 text-center transition duration-300 ${
              isDraggingBatch
                ? 'border-slate-950 bg-slate-100 shadow-inner dark:border-white dark:bg-slate-800'
                : 'border-slate-200 bg-slate-50 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white hover:shadow-lg dark:border-slate-700 dark:bg-slate-800 dark:hover:border-slate-600'
            }`}
          >
            <input
              ref={batchFileInputRef}
              type="file"
              accept=".pdf,.docx"
              multiple
              onChange={handleBatchFileChange}
              className="hidden"
            />
            <div className="mb-4 rounded-2xl bg-slate-950 p-4 shadow-lg shadow-slate-950/10 transition group-hover:scale-105 dark:bg-white">
              <svg viewBox="0 0 24 24" className="h-7 w-7 text-white dark:text-slate-950" fill="none">
                <path d="M12 16V4M12 4L7 9M12 4L17 9M5 20H19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className="relative text-base font-black text-slate-950 dark:text-white">
              {resumeFiles.length > 0
                ? `${resumeFiles.length} file${resumeFiles.length > 1 ? 's' : ''} selected — click to add more`
                : 'Browse or drag & drop candidate resumes'}
            </p>
            <p className="relative mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
              PDF, DOCX · max {MAX_BATCH_RESUMES} files
            </p>
          </div>

          {resumeFiles.length > 0 && (
            <ul className="space-y-2">
              {resumeFiles.map((f, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-800"
                >
                  <span className="truncate text-gray-800 dark:text-slate-200">{f.name}</span>
                  <button
                    type="button"
                    onClick={() => removeBatchFile(i)}
                    className="ml-3 text-gray-400 hover:text-red-500 transition"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}

          {batchFileError && (
            <p className="text-sm font-medium text-red-600">{batchFileError}</p>
          )}
          {isValidatingFiles && (
            <p className="text-sm font-medium text-amber-600">Validating uploaded files...</p>
          )}
        </div>
      }

      {/* ── JD input ── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="job-description" className="text-sm font-black tracking-tight text-slate-950 dark:text-white">
            Job Description
          </label>
          <button
            type="button"
            onClick={() => setShowJobManager(true)}
            className="rounded-full border border-slate-200 bg-white px-4 py-1.5 text-xs font-black text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-400 hover:text-slate-950 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-slate-500"
          >
             Saved Jobs
          </button>
        </div>
        <textarea
          id="job-description"
          rows="10"
          value={jobDescription}
          onChange={handleJdChange}
          placeholder="Paste the job description here. This is used to screen and rank all uploaded candidates."
          className="w-full rounded-3xl border border-slate-200 bg-slate-50 p-5 text-sm leading-6 text-slate-800 outline-none transition focus:border-slate-500 focus:bg-white focus:ring-4 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:ring-slate-700"
        />
        {jdError && <p className="text-sm font-medium text-red-600">{jdError}</p>}
        {selectedJob?.job_id && (
          <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 px-3 py-2">
            <p className="text-xs font-semibold text-blue-700 dark:text-blue-300">
              Using saved job rules from: {selectedJob.title}
            </p>
            <p className="mt-0.5 text-xs text-blue-600 dark:text-blue-400">
              Editing the JD text switches this back to pasted-JD screening only.
            </p>
          </div>
        )}
      </div>

      {/* Job Manager Modal */}
      {showJobManager && (
        <JobManager
          initialDescription={jobDescription}
          onSelectJob={handleSelectSavedJob}
          onClose={() => setShowJobManager(false)}
        />
      )}

      {/* ── Submit ── */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={loading || isValidatingFiles}
          className="rounded-2xl bg-slate-950 px-7 py-3.5 text-sm font-black text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
        >
          {isValidatingFiles
            ? 'Validating Files...'
            : loading
            ? 'Screening Candidates...'
            : `Screen ${resumeFiles.length || ''} Candidate${resumeFiles.length !== 1 ? 's' : ''}`}
        </button>
      </div>
    </form>
  )
}
