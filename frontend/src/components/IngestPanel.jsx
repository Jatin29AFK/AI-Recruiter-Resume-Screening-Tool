/**
 * IngestPanel.jsx
 * ----------------
 * Recruiter-facing panel for the email ingest feature.
 *
 * Features
 * --------
 * - Upload one or more resumes directly (drag-drop or browse)
 * - View previously ingested files (status: accepted / analyzed / rejected / error)
 * - Score resumes against a saved job and bulk-analyze pending candidates
 * - Open the same full candidate analysis drawer used in recruiter review
 * - Delete ingest records
 */

import { useState, useEffect, useRef } from 'react'
import {
  ingestUploadFile,
  listIngestJobs,
  analyzeIngestJob,
  deleteIngestJob,
  getIngestTargetJob,
  setIngestTargetJob,
} from '../services/api'
import JobManager from './JobManager'
import CandidateDetailPanel from './CandidateDetailPanel'

const STATUS_COLORS = {
  analyzed: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800',
  accepted: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800',
  rejected: 'text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800',
  error:    'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800',
}

const STATUS_LABELS = {
  analyzed: '✓ Analyzed',
  accepted: '→ Ready to score',
  rejected: '✗ Rejected',
  error:    '! Error',
}

const DEFAULT_POLICY = {
  shortlist_threshold: 63,
  review_threshold: 44,
}

function deriveShortlistVerdict(score) {
  if (score >= DEFAULT_POLICY.shortlist_threshold) return 'Shortlist'
  if (score >= DEFAULT_POLICY.review_threshold) return 'Review'
  return 'Reject'
}

function toCandidateView(job) {
  const analysis = job?.analysis
  if (!analysis) return null

  const scores = analysis.scores || {}
  const educationFit = analysis.education_fit || {}
  const shortlistSimulation = analysis.shortlist_simulation || {}
  const atsAudit = analysis.ats_audit || {}
  const keywordCoverage = analysis.keyword_coverage || {}
  const keywordSummary = keywordCoverage.summary || {}
  const overallScore = scores.overall_score ?? analysis.overall_score ?? 0
  const matchedSkills = analysis.matched_skills || []
  const missingSkills = analysis.missing_skills || []
  const criticalMissingSkills = analysis.critical_missing_skills || []
  const requiredSkills = analysis.jd_requirements?.required_skills || []
  const timelineGaps = (analysis.timeline_analysis?.gaps || []).map((gap) => {
    if (typeof gap === 'string') return gap
    if (gap?.label) return gap.label
    if (gap?.message) return gap.message
    const start = gap?.start || gap?.from || 'Unknown start'
    const end = gap?.end || gap?.to || 'Unknown end'
    return `${start} to ${end}`
  })

  const matchedRequiredSkills = matchedSkills.filter((skill) => requiredSkills.includes(skill))

  return {
    ...analysis,
    ...scores,
    candidate_id: job.ingest_id,
    candidate_index: 0,
    ingest_id: job.ingest_id,
    filename: analysis.filename || job.filename,
    fit_label: scores.fit_label || analysis.fit_label || 'Scored candidate',
    overall_score: overallScore,
    required_skill_score: scores.required_skill_score ?? 0,
    skill_support_score: scores.skill_support_score ?? 0,
    ats_score: analysis.ats_audit?.score ?? analysis.ats_score ?? 0,
    career_progression_score: scores.career_progression_score ?? 0,
    achievements_score: scores.achievements_score ?? 0,
    industry_fit_score: scores.industry_fit_score ?? 0,
    leadership_signals: scores.leadership_signals || [],
    red_flags: scores.red_flags || [],
    over_tailoring_flag: scores.over_tailoring_flag || false,
    language_quality: scores.language_quality || null,
    matched_skills: matchedSkills,
    missing_skills: missingSkills,
    critical_missing_skills: criticalMissingSkills,
    estimated_experience_years: analysis.experience_estimate?.estimated_years ?? null,
    experience_meets_requirement: analysis.experience_comparison?.meets_requirement ?? null,
    education_meets_requirement: analysis.education_meets_requirement ?? educationFit.meets_requirement ?? null,
    non_negotiable_verdict: analysis.non_negotiable_verdict || 'pass',
    non_negotiable_reasons: analysis.non_negotiable_reasons || [],
    non_negotiable_flags: analysis.non_negotiable_flags || [],
    review_flags: analysis.review_flags || [],
    keyword_missing_count: keywordSummary.missing_count ?? 0,
    keyword_strong_count: keywordSummary.strong_count ?? 0,
    keyword_coverage_items: keywordCoverage.items || [],
    cert_coverage: analysis.cert_coverage || null,
    shortlist_verdict: deriveShortlistVerdict(overallScore),
    resume_serve_id: analysis.resume_serve_id || job.serve_id,
    linkedin_url: analysis.structured_resume?.linkedin || '',
    recommendation: analysis.recommendation || null,
    shortlist_simulation: shortlistSimulation,
    shortlist_reasons: shortlistSimulation.reasons || [],
    resume_sections: analysis.resume_sections || {},
    structured_resume: analysis.structured_resume || {},
    raw_resume_text: analysis.raw_resume_text || '',
    suggestions: analysis.suggestions || [],
    ats_audit: atsAudit,
    ats_issues: atsAudit.issues || [],
    ats_issues_count: atsAudit.issues?.length ?? 0,
    evidence_summary: analysis.evidence_summary || null,
    timeline_gaps: timelineGaps,
    required_skills_count: requiredSkills.length,
    required_skills_matched_count: matchedRequiredSkills.length,
    status: 'New',
  }
}

function Badge({ status }) {
  const cls = STATUS_COLORS[status] || 'text-slate-500 bg-slate-50 border-slate-200'
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${cls}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function SavedJobBar({
  selectedJob,
  pendingCount,
  analyzingAll,
  analyzeProgress,
  targetJobSaving,
  onOpenJobs,
  onClearJob,
  onAnalyzeAll,
}) {
  return (
    <div className="rounded-3xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-black uppercase tracking-[0.24em] text-slate-400 dark:text-slate-500">Scoring target</p>
          <h3 className="text-lg font-black text-slate-900 dark:text-white">
            {selectedJob?.title || 'Choose a saved job'}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {selectedJob
              ? `New uploads can be scored immediately and ${pendingCount} pending candidate${pendingCount === 1 ? '' : 's'} can be analyzed in one run.`
              : 'Pick one saved job to enable scoring for new and incoming resumes.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onOpenJobs}
            className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-200 transition hover:border-slate-400 dark:hover:border-slate-500"
          >
            Saved Jobs
          </button>
          {selectedJob && (
            <button
              type="button"
              onClick={onClearJob}
              disabled={targetJobSaving}
              className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2.5 text-sm font-semibold text-slate-500 dark:text-slate-300 transition hover:border-slate-400"
            >
              {targetJobSaving ? 'Saving…' : 'Clear'}
            </button>
          )}
          <button
            type="button"
            onClick={onAnalyzeAll}
            disabled={!selectedJob || pendingCount === 0 || analyzingAll}
            className="rounded-2xl bg-slate-950 dark:bg-white px-5 py-2.5 text-sm font-black text-white dark:text-slate-950 shadow-lg transition hover:-translate-y-0.5 hover:bg-slate-800 dark:hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzingAll
              ? `Analyzing ${analyzeProgress.done}/${analyzeProgress.total}`
              : pendingCount > 0
              ? `Analyze All (${pendingCount})`
              : 'All Scored'}
          </button>
        </div>
      </div>

      {selectedJob?.description && (
        <div className="mt-4 rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 px-4 py-3 text-sm text-blue-700 dark:text-blue-300">
          <p className="font-semibold">Using saved job rules from {selectedJob.title}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-blue-600 dark:text-blue-400">{selectedJob.description}</p>
        </div>
      )}
    </div>
  )
}

export default function IngestPanel({ onBack }) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadErrors, setUploadErrors] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const [analyzeSuccess, setAnalyzeSuccess] = useState(null)
  const [selectedJob, setSelectedJob] = useState(null)
  const [showJobManager, setShowJobManager] = useState(false)
  const [analyzingAll, setAnalyzingAll] = useState(false)
  const [analyzeProgress, setAnalyzeProgress] = useState({ done: 0, total: 0 })
  const [activeAnalyzeIds, setActiveAnalyzeIds] = useState([])
  const [selectedCandidateId, setSelectedCandidateId] = useState(null)
  const [targetJobSaving, setTargetJobSaving] = useState(false)
  const fileInputRef = useRef(null)

  async function fetchJobs({ silent = false } = {}) {
    if (!silent) {
      setLoading(true)
    }

    try {
      const data = await listIngestJobs(200)
      setJobs(data.jobs || [])
    } catch {
      if (!silent) {
        setJobs([])
      }
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    let cancelled = false

    async function loadInitialState() {
      setLoading(true)
      try {
        const [jobsData, targetData] = await Promise.all([
          listIngestJobs(200),
          getIngestTargetJob(),
        ])
        if (cancelled) return
        setJobs(jobsData.jobs || [])
        setSelectedJob(targetData.job || null)
      } catch {
        if (cancelled) return
        setJobs([])
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadInitialState()
    const intervalId = window.setInterval(() => {
      fetchJobs({ silent: true })
    }, 3000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  async function handleSelectJob(job) {
    setTargetJobSaving(true)
    try {
      const result = await setIngestTargetJob(job?.job_id || '')
      setSelectedJob(result.job || null)
      setShowJobManager(false)
    } catch (e) {
      alert(e.message || 'Failed to save Email Intake target job.')
    } finally {
      setTargetJobSaving(false)
    }
  }

  async function handleClearJob() {
    setTargetJobSaving(true)
    try {
      await setIngestTargetJob('')
      setSelectedJob(null)
    } catch (e) {
      alert(e.message || 'Failed to clear Email Intake target job.')
    } finally {
      setTargetJobSaving(false)
    }
  }

  async function handleFiles(files) {
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadErrors([])
    const errors = []
    for (const file of Array.from(files)) {
      try {
        const result = await ingestUploadFile(file, {
          jobDescription: selectedJob?.description || '',
          jobId: selectedJob?.job_id || '',
        })
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

  async function handleAnalyzeJob(job) {
    if (!selectedJob?.description) {
      setShowJobManager(true)
      return
    }

    setActiveAnalyzeIds(prev => [...prev, job.ingest_id])
    try {
      const result = await analyzeIngestJob(job.ingest_id, selectedJob.description, selectedJob.job_id)
      setAnalyzeSuccess(result?.filename || job.filename)
      await fetchJobs({ silent: true })
      window.setTimeout(() => setAnalyzeSuccess(null), 4000)
    } catch (e) {
      alert(e.message || 'Analysis failed.')
    } finally {
      setActiveAnalyzeIds(prev => prev.filter(id => id !== job.ingest_id))
    }
  }

  async function handleAnalyzeAll() {
    if (!selectedJob?.description) {
      setShowJobManager(true)
      return
    }

    const pendingJobs = jobs.filter(job => job.status === 'accepted')
    if (pendingJobs.length === 0) return

    setAnalyzingAll(true)
    setAnalyzeProgress({ done: 0, total: pendingJobs.length })
    setActiveAnalyzeIds(pendingJobs.map(job => job.ingest_id))

    try {
      for (let index = 0; index < pendingJobs.length; index += 1) {
        const job = pendingJobs[index]
        await analyzeIngestJob(job.ingest_id, selectedJob.description, selectedJob.job_id)
        setAnalyzeProgress({ done: index + 1, total: pendingJobs.length })
      }
      setAnalyzeSuccess(`${pendingJobs.length} candidate${pendingJobs.length === 1 ? '' : 's'} scored against ${selectedJob.title}`)
      await fetchJobs({ silent: true })
      window.setTimeout(() => setAnalyzeSuccess(null), 5000)
    } catch (e) {
      alert(e.message || 'Bulk analysis failed.')
    } finally {
      setAnalyzingAll(false)
      setActiveAnalyzeIds([])
    }
  }

  async function handleDelete(ingestId) {
    try {
      await deleteIngestJob(ingestId)
      setJobs(prev => prev.filter(j => j.ingest_id !== ingestId))
      if (selectedCandidateId === ingestId) {
        setSelectedCandidateId(null)
      }
      await fetchJobs({ silent: true })
    } catch (e) {
      const message = e.message || 'Failed to delete ingest job.'
      if (message.toLowerCase().includes('not found')) {
        setJobs(prev => prev.filter(j => j.ingest_id !== ingestId))
        if (selectedCandidateId === ingestId) {
          setSelectedCandidateId(null)
        }
        await fetchJobs({ silent: true })
        return
      }
      alert(message)
    }
  }

  const byStatus = {
    analyzed: jobs.filter(j => j.status === 'analyzed'),
    accepted: jobs.filter(j => j.status === 'accepted'),
    rejected: jobs.filter(j => j.status === 'rejected' || j.status === 'error'),
  }
  const selectedCandidate = toCandidateView(jobs.find(job => job.ingest_id === selectedCandidateId))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400 mb-1">Recruiter workspace</p>
          <h2 className="text-2xl font-black text-slate-900 dark:text-white">Email Intake</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Incoming resumes land here for scoring, review, and shortlist decisions.
          </p>
        </div>
        {typeof onBack === 'function' && (
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 self-start rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200 transition hover:border-slate-400 dark:hover:border-slate-500"
          >
            <span aria-hidden="true">←</span>
            Back
          </button>
        )}
      </div>

      <SavedJobBar
        selectedJob={selectedJob}
        pendingCount={byStatus.accepted.length}
        analyzingAll={analyzingAll}
        analyzeProgress={analyzeProgress}
        targetJobSaving={targetJobSaving}
        onOpenJobs={() => setShowJobManager(true)}
        onClearJob={handleClearJob}
        onAnalyzeAll={handleAnalyzeAll}
      />

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
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Up to 50 files. Files are scanned automatically{selectedJob ? ` and scored against ${selectedJob.title}.` : '.'}
        </p>
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
          <p className="text-slate-500 dark:text-slate-400 text-sm">No resumes yet. Upload a candidate file or wait for inbox resumes to appear here.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="flex flex-wrap gap-3 text-xs font-semibold">
            <span className="text-green-600 dark:text-green-400">{byStatus.analyzed.length} scored</span>
            <span className="text-blue-600 dark:text-blue-400">{byStatus.accepted.length} ready to score</span>
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
                  const isAnalyzing = activeAnalyzeIds.includes(job.ingest_id)
                  const ingestedAt = job.created_at
                    ? new Date(job.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
                    : '—'
                  return (
                    <tr key={job.ingest_id} className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition">
                      <td className="px-4 py-3">
                        {job.status === 'analyzed' ? (
                          <button
                            type="button"
                            onClick={() => setSelectedCandidateId(job.ingest_id)}
                            className="max-w-[220px] truncate text-left font-semibold text-slate-800 dark:text-slate-100 underline-offset-2 hover:underline"
                            title={job.filename}
                          >
                            {job.filename}
                          </button>
                        ) : (
                          <p className="font-medium text-slate-800 dark:text-slate-100 truncate max-w-[220px]" title={job.filename}>{job.filename}</p>
                        )}
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
                              onClick={() => handleAnalyzeJob(job)}
                              disabled={!selectedJob || isAnalyzing}
                              className="rounded-lg border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-950 px-2 py-1 text-xs font-semibold text-blue-600 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900 transition disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {isAnalyzing ? 'Analyzing…' : 'Analyze'}
                            </button>
                          )}
                          {job.status === 'analyzed' && (
                            <>
                              <button
                                type="button"
                                onClick={() => setSelectedCandidateId(job.ingest_id)}
                                className="rounded-lg border border-emerald-200 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950 px-2 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900 transition"
                              >
                                View Analysis
                              </button>
                              <button
                                type="button"
                                onClick={() => handleAnalyzeJob(job)}
                                disabled={!selectedJob || isAnalyzing}
                                className="rounded-lg border border-slate-200 dark:border-slate-700 px-2 py-1 text-xs font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {isAnalyzing ? 'Analyzing…' : 'Re-analyze'}
                              </button>
                            </>
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

      {showJobManager && (
        <JobManager
          onSelectJob={handleSelectJob}
          onClose={() => setShowJobManager(false)}
        />
      )}

      {selectedCandidate && (
        <CandidateDetailPanel
          candidate={selectedCandidate}
          policy={DEFAULT_POLICY}
          onClose={() => setSelectedCandidateId(null)}
        />
      )}
    </div>
  )
}
