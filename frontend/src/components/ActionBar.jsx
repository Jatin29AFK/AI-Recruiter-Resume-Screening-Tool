import { useState } from 'react'
import { API_BASE_URL } from '../services/api.js'

function ResumePreviewModal({ serveId, filename, onClose }) {
  const previewUrl = `${API_BASE_URL}/matcher/resume/${encodeURIComponent(serveId)}/preview`
  return (
    <>
      <div className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed inset-2 z-[70] flex flex-col rounded-2xl bg-white dark:bg-slate-900 shadow-2xl overflow-hidden">
        <div className="flex flex-shrink-0 items-center justify-between border-b border-gray-200 dark:border-slate-700 px-5 py-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Resume Preview</p>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{filename}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>
        <iframe
          src={previewUrl}
          title="Resume Preview"
          className="flex-1 w-full border-0 bg-white"
        />
      </div>
    </>
  )
}

export default function ActionBar({
  suggestions = [],
  onReset,
  result,
  tailorResult,
  applyReadiness,
}) {
  const [showPreview, setShowPreview] = useState(false)
  const handleCopySuggestions = async () => {
    if (!result) return

    const fitScore = result.scores?.overall_score ?? 0
    const fitLabel = result.scores?.fit_label || 'Unknown'
    const atsScore = result.ats_audit?.score ?? 0
    const atsGrade = result.ats_audit?.grade || 'Unknown'
    const readinessScore = applyReadiness?.score ?? 0
    const readinessLabel = applyReadiness?.label || 'Unknown'

    const matchedSkills = result.matched_skills || []
    const missingSkills = result.missing_skills || []
    const criticalMissingSkills = result.critical_missing_skills || []
    const optimizedScore = tailorResult?.analysis_after?.overall_score ?? null

    const lines = [
      'Havells Resume Improvement Plan',
      '',
      'Current Snapshot',
      `- Fit Score: ${fitScore}% (${fitLabel})`,
      `- Readiness Score: ${readinessScore} (${readinessLabel})`,
      `- ATS Format Score: ${atsScore} (${atsGrade})`,
      `- Critical Gaps: ${criticalMissingSkills.length}`,
      optimizedScore !== null
        ? `- Optimized Score: ${optimizedScore}%`
        : '- Optimized Score: Not generated yet',
      '',
      'What this means',
      '- Fit Score shows how well your current resume content matches this specific job.',
      '- Readiness Score shows how ready your resume looks to apply right now.',
      '- ATS Format Score reflects formatting quality, not job-fit by itself.',
      '',
      'Top Resume Strengths',
      ...(matchedSkills.length
        ? matchedSkills.slice(0, 8).map((skill) => `- ${skill}`)
        : ['- No strong matched skills detected yet.']),
      '',
      'Top Gaps To Fix',
      ...(criticalMissingSkills.length
        ? criticalMissingSkills.map((skill) => `- Critical gap: ${skill}`)
        : ['- No critical gaps detected.']),
      ...(missingSkills.length
        ? missingSkills
            .filter((skill) => !criticalMissingSkills.includes(skill))
            .slice(0, 8)
            .map((skill) => `- Missing skill / keyword: ${skill}`)
        : []),
      '',
      'Recommended Resume Actions',
      ...(suggestions.length
        ? suggestions.map((item, index) => `${index + 1}. ${item}`)
        : ['1. Improve your resume based on the missing skills and job-specific requirements.']),
      '',
      'Manual Review Reminder',
      '- Review every change manually before using the resume.',
      '- Do not add skills or experience you do not actually have.',
      '- Prefer rewriting existing bullets to better reflect relevant work and projects.',
    ]

    const text = lines.join('\n')
    await navigator.clipboard.writeText(text)
    alert('Improvement plan copied to clipboard.')
  }

  return (
    <>
      {showPreview && result?.resume_serve_id && (
        <ResumePreviewModal
          serveId={result.resume_serve_id}
          filename={result.filename}
          onClose={() => setShowPreview(false)}
        />
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
        {result?.resume_serve_id && (
          <button
            type="button"
            onClick={() => setShowPreview(true)}
            className="rounded-xl border border-blue-300 bg-blue-50 dark:bg-blue-950 dark:border-blue-700 px-4 py-2.5 text-sm font-medium text-blue-700 dark:text-blue-300 transition hover:bg-blue-100 dark:hover:bg-blue-900"
          >
            View Resume
          </button>
        )}
        <button
          type="button"
          onClick={handleCopySuggestions}
          className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
        >
          Copy Improvement Plan
        </button>

        <button
          type="button"
          onClick={onReset}
          className="rounded-xl bg-black px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
        >
          Analyze Another Resume
        </button>
      </div>
    </>
  )
}
