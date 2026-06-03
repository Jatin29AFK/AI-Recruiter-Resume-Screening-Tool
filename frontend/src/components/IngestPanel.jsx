/**
 * IngestPanel.jsx
 * ----------------
 * Recruiter-facing panel for the email ingest feature.
 *
 * Features
 * --------
 * - Upload one or more resumes directly (drag-drop or browse)
 * - View previously ingested files (status: accepted / analyzed / rejected / error)
 * - Run analysis on an accepted-but-unscored resume by pasting a JD
 * - Delete ingest records
 * - Instructions for Power Automate and Outlook Quick Step setup
 */

import { useState, useEffect, useRef } from 'react'
import {
  ingestUploadFile,
  listIngestJobs,
  analyzeIngestJob,
  deleteIngestJob,
} from '../services/api'

const STATUS_COLORS = {
  analyzed: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800',
  accepted: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800',
  rejected: 'text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800',
  error:    'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800',
}

const STATUS_LABELS = {
  analyzed: '✓ Analyzed',
  accepted: '→ Pending JD',
  rejected: '✗ Rejected',
  error:    '! Error',
}

function Badge({ status }) {
  const cls = STATUS_COLORS[status] || 'text-slate-500 bg-slate-50 border-slate-200'
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${cls}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function InstructionsAccordion() {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800 text-sm font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
      >
        <span>⚡ How to connect Outlook / Power Automate</span>
        <span className="text-slate-400 text-xs">{open ? '▲ Hide' : '▼ Show'}</span>
      </button>
      {open && (
        <div className="px-4 py-3 space-y-4 text-sm text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900">
          <div>
            <p className="font-bold text-slate-800 dark:text-white mb-1">Option 1 — Outlook Quick Step (fastest, no IT needed)</p>
            <ol className="list-decimal list-inside space-y-1 text-xs">
              <li>In Outlook Desktop → Home → Quick Steps → Create New.</li>
              <li>Action: <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">Forward</code> to <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">resumes@yourcompany.com</code>.</li>
              <li>Name it "Send to Screening". Optionally add keyboard shortcut.</li>
              <li>Select email with resume → click the Quick Step.</li>
            </ol>
          </div>
          <div>
            <p className="font-bold text-slate-800 dark:text-white mb-1">Option 2 — Power Automate Button (recommended UX)</p>
            <ol className="list-decimal list-inside space-y-1 text-xs">
              <li>Download <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">power_automate_flow_template.json</code> from the backend folder.</li>
              <li>Go to <a href="https://make.powerautomate.com" target="_blank" rel="noreferrer" className="text-blue-600 underline">make.powerautomate.com</a> → My Flows → Import.</li>
              <li>Set <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">INGEST_WEBHOOK_URL</code> to your backend URL + <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">/ingest/upload</code>.</li>
              <li>Set <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">INGEST_SECRET</code> to the value of <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">INGEST_SECRET</code> in your backend <code>.env</code>.</li>
              <li>Enable the Flow. Recruiters see a "Send to Screening" button inside Outlook.</li>
            </ol>
          </div>
          <div>
            <p className="font-bold text-slate-800 dark:text-white mb-1">Option 3 — Direct upload here</p>
            <p className="text-xs">Drag and drop resume files below — same processing pipeline.</p>
          </div>
          <div className="rounded-md border border-amber-200 bg-amber-50 dark:bg-amber-900/30 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
            <strong>Security note:</strong> Set <code>INGEST_SECRET</code> and <code>VITE_INGEST_SECRET</code> in your .env files before using this panel. Keep these values private.
          </div>
        </div>
      )}
    </div>
  )
}

function AnalyzeModal({ job, onClose, onDone }) {
  const [jd, setJd] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleAnalyze() {
    if (!jd.trim()) { setError('Please paste a job description.'); return }
    setError('')
    setLoading(true)
    try {
      const result = await analyzeIngestJob(job.ingest_id, jd)
      onDone(result)
    } catch (e) {
      setError(e.message || 'Analysis failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed inset-x-4 top-24 z-[80] max-w-xl mx-auto rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Run Analysis</p>
            <p className="text-sm font-semibold text-slate-900 dark:text-white">{job.filename}</p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition">✕</button>
        </div>
        <div className="p-5 space-y-3">
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">
            Paste Job Description
            <textarea
              value={jd}
              onChange={e => setJd(e.target.value)}
              rows={8}
              className="mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="Paste the full job description here…"
            />
          </label>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={loading}
            className="w-full rounded-xl bg-blue-600 hover:bg-blue-700 text-white py-2.5 text-sm font-bold transition disabled:opacity-50"
          >
            {loading ? 'Analyzing…' : 'Run Analysis →'}
          </button>
        </div>
      </div>
    </>
  )
}

export default function IngestPanel() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadErrors, setUploadErrors] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const [analyzeTarget, setAnalyzeTarget] = useState(null)
  const [analyzeSuccess, setAnalyzeSuccess] = useState(null)
  const fileInputRef = useRef(null)

  async function fetchJobs() {
    try {
      const data = await listIngestJobs(200)
      setJobs(data.jobs || [])
    } catch {
      // ingest secret not configured / endpoint not reachable
      setJobs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchJobs() }, [])

  async function handleFiles(files) {
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadErrors([])
    const errors = []
    for (const file of Array.from(files)) {
      try {
        const result = await ingestUploadFile(file)
        if (result.status === 'rejected' || result.status === 'error') {
          errors.push(`${file.name}: ${result.rejection_reason || 'Rejected'}`)
        }
      } catch (e) {
        errors.push(`${file.name}: ${e.message}`)
      }
    }
    setUploadErrors(errors)
    await fetchJobs()
    setUploading(false)
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  async function handleDelete(ingestId) {
    try {
      await deleteIngestJob(ingestId)
      setJobs(prev => prev.filter(j => j.ingest_id !== ingestId))
    } catch (e) {
      alert(e.message)
    }
  }

  function onAnalyzeDone(result) {
    setAnalyzeTarget(null)
    setAnalyzeSuccess(result?.filename || 'Resume')
    fetchJobs()
    setTimeout(() => setAnalyzeSuccess(null), 4000)
  }

  const byStatus = {
    analyzed: jobs.filter(j => j.status === 'analyzed'),
    accepted: jobs.filter(j => j.status === 'accepted'),
    rejected: jobs.filter(j => j.status === 'rejected' || j.status === 'error'),
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <p className="text-xs font-black uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400 mb-1">Email Ingest</p>
        <h2 className="text-xl font-black text-slate-900 dark:text-white">Resume Intake</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Upload resumes manually or receive them automatically via Outlook / Power Automate.
        </p>
      </div>

      <InstructionsAccordion />

      {/* Upload drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed transition flex flex-col items-center justify-center gap-2 py-10 px-6 text-center
          ${dragOver
            ? 'border-blue-400 bg-blue-50 dark:bg-blue-950'
            : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:border-slate-400 dark:hover:border-slate-500'}`}
      >
        <span className="text-3xl">📄</span>
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {uploading ? 'Uploading…' : 'Drop PDF / DOCX resumes here, or click to browse'}
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500">Up to 50 files. Files are scanned and validated automatically.</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          multiple
          className="hidden"
          onChange={e => handleFiles(e.target.files)}
        />
      </div>

      {/* Upload errors */}
      {uploadErrors.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950 px-4 py-3 text-sm text-red-700 dark:text-red-300 space-y-1">
          <p className="font-semibold">Some files were not ingested:</p>
          <ul className="list-disc list-inside">
            {uploadErrors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {/* Success toast */}
      {analyzeSuccess && (
        <div className="rounded-xl border border-green-200 bg-green-50 dark:bg-green-950 px-4 py-3 text-sm text-green-700 dark:text-green-300 font-semibold">
          ✓ Analysis complete for {analyzeSuccess}
        </div>
      )}

      {/* Jobs list */}
      {loading ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Loading ingest history…</p>
      ) : jobs.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-6 py-10 text-center">
          <p className="text-slate-500 dark:text-slate-400 text-sm">No resumes ingested yet. Upload files above or connect via Power Automate.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="flex flex-wrap gap-3 text-xs font-semibold">
            <span className="text-green-600 dark:text-green-400">{byStatus.analyzed.length} analyzed</span>
            <span className="text-blue-600 dark:text-blue-400">{byStatus.accepted.length} pending JD</span>
            <span className="text-red-500 dark:text-red-400">{byStatus.rejected.length} rejected / errors</span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                  <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">File</th>
                  <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Source</th>
                  <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Submitted by</th>
                  <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Score</th>
                  <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Ingested</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {jobs.map(job => {
                  const overallScore = job.analysis?.scores?.overall_score ?? job.analysis?.overall_score ?? null
                  const ingestedAt = job.created_at
                    ? new Date(job.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
                    : '—'
                  return (
                    <tr key={job.ingest_id} className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-800 dark:text-slate-100 truncate max-w-[220px]" title={job.filename}>{job.filename}</p>
                        {job.rejection_reason && (
                          <p className="text-xs text-red-500 dark:text-red-400 mt-0.5 truncate max-w-[220px]">{job.rejection_reason}</p>
                        )}
                      </td>
                      <td className="px-4 py-3"><Badge status={job.status} /></td>
                      <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 capitalize">{job.source || '—'}</td>
                      <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 truncate max-w-[160px]">{job.recruiter_email || '—'}</td>
                      <td className="px-4 py-3">
                        {overallScore != null
                          ? <span className={`font-bold text-sm ${overallScore >= 63 ? 'text-green-600 dark:text-green-400' : overallScore >= 44 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'}`}>{overallScore}</span>
                          : <span className="text-slate-400 dark:text-slate-500 text-xs">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">{ingestedAt}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {job.status === 'accepted' && (
                            <button
                              type="button"
                              onClick={() => setAnalyzeTarget(job)}
                              className="rounded-lg border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-950 px-2 py-1 text-xs font-semibold text-blue-600 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900 transition"
                            >
                              Analyze
                            </button>
                          )}
                          {job.status === 'analyzed' && (
                            <button
                              type="button"
                              onClick={() => setAnalyzeTarget(job)}
                              className="rounded-lg border border-slate-200 dark:border-slate-700 px-2 py-1 text-xs font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                            >
                              Re-analyze
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => { if (window.confirm('Delete this ingest record?')) handleDelete(job.ingest_id) }}
                            className="rounded-lg px-2 py-1 text-xs font-medium text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950 transition"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Analyze modal */}
      {analyzeTarget && (
        <AnalyzeModal
          job={analyzeTarget}
          onClose={() => setAnalyzeTarget(null)}
          onDone={onAnalyzeDone}
        />
      )}
    </div>
  )
}
