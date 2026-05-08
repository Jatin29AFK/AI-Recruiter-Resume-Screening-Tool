import { useEffect, useState } from 'react'
import RecommendationPanel from './RecommendationPanel'
import NotesPanel from './NotesPanel'
import CertificationCoveragePanel from './CertificationCoveragePanel'
import { API_BASE_URL } from '../services/api.js'
import {
  getCandidateStage,
  getRejectionExplanation,
} from '../utils/candidateInsights'

function ResumePreviewModal({ serveId, filename, onClose }) {
  const previewUrl = `${API_BASE_URL}/matcher/resume/${encodeURIComponent(serveId)}/preview`
  return (
    <>
      <div className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed inset-2 z-[90] flex flex-col rounded-2xl bg-white dark:bg-slate-900 shadow-2xl overflow-hidden">
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

/** How confident is the recruiter to forward this candidate — same logic as CandidateCard */
/** Score bar with label and explanation */
function ScoreBar({ label, score, explanation }) {
  const pct = Math.min(100, Math.max(0, score))
  const barColor =
    pct >= 70 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-400'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">{label}</span>
          {explanation && (
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{explanation}</p>
          )}
        </div>
        <span className="flex-shrink-0 text-lg font-bold text-gray-900 dark:text-white">{pct}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

/** Chip list — green (matched), red (missing) */
function SkillChips({ skills, variant = 'neutral' }) {
  const styles = {
    matched: 'bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800',
    critical: 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-300 border border-red-200 dark:border-red-800',
    missing: 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300',
  }
  const cls = styles[variant] || styles.missing

  if (!skills || skills.length === 0) return <p className="text-xs text-gray-400">None</p>
  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((s) => (
        <span key={s} className={`rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{s}</span>
      ))}
    </div>
  )
}

const SCORE_META = {
  overall_score: {
    label: 'Overall Match Score',
    explanation:
      'A weighted combination of skill coverage, semantic similarity to the JD, evidence quality, and penalties for critical missing requirements. Range: 0–100. Excellent ≥85 · Good 70–84 · Average 50–69 · Low <50.',
  },
  ats_score: {
    label: 'ATS Score',
    explanation:
      'How well this resume would pass an Automated Tracking System scan. Checks for clean formatting, readable sections, keyword presence, no tables/images that break parsing, and standard section headings. Range: 0–100.',
  },
  required_skill_score: {
    label: 'Required Skills Coverage',
    explanation:
      'Percentage of must-have skills from the JD that appear in this resume. These are non-negotiable skills a recruiter listed as required. Range: 0–100.',
  },
  skill_support_score: {
    label: 'Evidence Quality Score',
    explanation:
      'Measures how well the candidate has demonstrated their claimed skills with concrete proof — project descriptions, measurable outcomes, action verbs. A candidate who just lists skills without context scores lower here. Range: 0–100.',
  },
}

function getBucketMeta(policy) {
  const shortlist = policy?.shortlist_threshold ?? 63
  const review = policy?.review_threshold ?? 44
  return {
    Shortlist: {
      label: 'Shortlisted',
      color: 'text-green-700 dark:text-green-400',
      bg: 'bg-green-50 dark:bg-green-950 border-green-300 dark:border-green-700',
      icon: '✓',
      reason: `Overall score ≥${shortlist} — strong fit against the JD requirements.`,
    },
    Review: {
      label: 'Needs Review',
      color: 'text-yellow-700 dark:text-yellow-400',
      bg: 'bg-yellow-50 dark:bg-yellow-950 border-yellow-300 dark:border-yellow-700',
      icon: '~',
      reason: `Overall score ${review}–${shortlist - 1} — partial fit; review manually before deciding.`,
    },
    Reject: {
      label: 'Not Suitable',
      color: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-50 dark:bg-red-950 border-red-300 dark:border-red-700',
      icon: '✗',
      reason: `Overall score <${review} — significant gaps against JD requirements.`,
    },
  }
}

export default function CandidateDetailPanel({ candidate, onClose, policy }) {
  // close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const [linkedinUrl, setLinkedinUrl] = useState(candidate?.linkedin_url || '')
  const [linkedinEditing, setLinkedinEditing] = useState(false)
  const [linkedinInput, setLinkedinInput] = useState('')
  const [expandedBox, setExpandedBox] = useState(null)
  const [showPreview, setShowPreview] = useState(false)

  if (!candidate) return null

  const bucketMeta = getBucketMeta(policy)
  const bucket = bucketMeta[candidate.shortlist_verdict] || bucketMeta.Review
  const activeScore = candidate._weighted_score ?? candidate.overall_score
  const candidateStage = getCandidateStage(candidate)
  const activeStageRejected = getCandidateStage(candidate) === 'Rejected'
  const rejected =
    candidate.shortlist_verdict === 'Reject' ||
    activeStageRejected
  const showRejectionReason = rejected
  const rejectionExplanation = showRejectionReason ? getRejectionExplanation(candidate) : ''
  const nonNegotiableReject = candidate.non_negotiable_verdict === 'reject' && candidate.shortlist_verdict === 'Reject'
  const nonNegotiableReview = candidate.non_negotiable_verdict === 'review'

  const normalizeLinkedinUrl = (url) => {
    if (!url) return ''
    const trimmed = url.trim()
    if (trimmed.startsWith('http')) return trimmed
    if (trimmed.startsWith('linkedin.com')) return `https://${trimmed}`
    return trimmed
  }

  return (
    <>
      {showPreview && candidate?.resume_serve_id && (
        <ResumePreviewModal
          serveId={candidate.resume_serve_id}
          filename={candidate.filename}
          onClose={() => setShowPreview(false)}
        />
      )}

      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-in panel - Full width */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-white dark:bg-slate-900 shadow-2xl overflow-y-auto">

        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-6 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Candidate Analysis</p>
            <h2 className="mt-0.5 truncate text-base font-bold text-gray-900 dark:text-white">{candidate.filename}</h2>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {candidate.resume_serve_id && (
              <button
                onClick={() => setShowPreview(true)}
                className="rounded-xl border border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 px-3 py-1.5 text-xs font-semibold hover:bg-blue-100 dark:hover:bg-blue-900 transition"
              >
                View Resume
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded-full p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 transition"
              title="Close"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="flex-1 space-y-8 px-6 py-6">

          {/* LinkedIn Profile — optional */}
          <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 px-4 py-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-blue-600 dark:text-blue-400 text-base flex-shrink-0">in</span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-blue-800 dark:text-blue-200 uppercase tracking-wide">LinkedIn Profile</p>
                  {linkedinUrl ? (
                    <a
                      href={normalizeLinkedinUrl(linkedinUrl)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-700 dark:text-blue-300 underline hover:text-blue-900 dark:hover:text-blue-100 truncate block max-w-[300px]"
                    >
                      {linkedinUrl}
                    </a>
                  ) : (
                    <p className="text-xs text-blue-500 dark:text-blue-400 italic">Not found in resume — add manually</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {linkedinUrl && (
                  <a
                    href={normalizeLinkedinUrl(linkedinUrl)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-xs font-semibold transition"
                  >
                    Open Profile
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => { setLinkedinInput(linkedinUrl); setLinkedinEditing(true) }}
                  className="rounded-xl border border-blue-300 dark:border-blue-700 bg-white dark:bg-slate-900 text-blue-700 dark:text-blue-300 px-3 py-1.5 text-xs font-semibold hover:bg-blue-50 dark:hover:bg-blue-900 transition"
                >
                  {linkedinUrl ? 'Edit' : '+ Add URL'}
                </button>
              </div>
            </div>
            {linkedinEditing && (
              <div className="mt-3 flex gap-2">
                <input
                  type="url"
                  value={linkedinInput}
                  onChange={e => setLinkedinInput(e.target.value)}
                  placeholder="https://linkedin.com/in/username"
                  className="flex-1 rounded-xl border border-blue-300 dark:border-blue-700 dark:bg-slate-900 dark:text-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => { setLinkedinUrl(linkedinInput.trim()); setLinkedinEditing(false) }}
                  className="rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 text-xs font-semibold transition"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setLinkedinEditing(false)}
                  className="rounded-xl border border-gray-200 dark:border-slate-700 px-3 py-2 text-xs font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
              </div>
            )}
            <p className="mt-2 text-xs text-blue-600 dark:text-blue-400 opacity-70">
              URL auto-extracted from resume if present. Add manually if missing.
            </p>
          </div>

          {/* Shortlist verdict */}
          <div className={`rounded-2xl border p-5 ${bucket.bg}`}>
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-bold ${bucket.color}`}>{bucket.icon}</span>
              <div>
                <p className={`text-base font-bold ${bucket.color}`}>{bucket.label}</p>
                <p className="text-sm text-gray-600 dark:text-slate-400">
                  {nonNegotiableReject
                    ? 'Forced to Reject because one or more backend non-negotiable criteria failed.'
                    : bucket.reason}
                </p>
                <p className="mt-1 text-xs font-semibold text-gray-500 dark:text-slate-400">Hiring stage: {candidateStage}</p>
              </div>
            </div>
          </div>

          {showRejectionReason && nonNegotiableReject && candidate.non_negotiable_reasons?.length > 0 && (
            <div className="rounded-2xl border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-red-700 dark:text-red-300">Rejected on Non-Negotiables</p>
              <ul className="mt-2 space-y-1.5">
                {candidate.non_negotiable_reasons.map((reason, i) => (
                  <li key={i} className="text-sm leading-relaxed text-red-700 dark:text-red-200">• {reason}</li>
                ))}
              </ul>
            </div>
          )}

          {!nonNegotiableReject && nonNegotiableReview && candidate.review_flags?.length > 0 && (
            <div className="rounded-2xl border border-orange-300 dark:border-orange-700 bg-orange-50 dark:bg-orange-950 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-orange-700 dark:text-orange-300">Manual Review Needed on Non-Negotiables</p>
              <ul className="mt-2 space-y-1.5">
                {candidate.review_flags.map((flag, i) => (
                  <li key={i} className="text-sm leading-relaxed text-orange-700 dark:text-orange-200">• {flag}</li>
                ))}
              </ul>
            </div>
          )}

          {showRejectionReason && rejected && rejectionExplanation && (
            <div className="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-red-700 dark:text-red-300">Plain-English Rejection Reason</p>
              <p className="mt-1 text-sm leading-relaxed text-red-700 dark:text-red-200">{rejectionExplanation}</p>
            </div>
          )}

          {/* ── Verdict Evidence Summary ──────────────────────────────────── */}
          {/* A quick-scan checklist answering: why this verdict? */}
          <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 divide-y divide-gray-200 dark:divide-slate-700">
            <div className="px-4 py-3">
              <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Screening Criteria — Verdict Evidence</h3>
              <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">
                 
              </p>
            </div>

            {/* Row: Must-have skills */}
            <div className="flex items-start gap-3 px-4 py-3">
              <span className={`mt-0.5 text-sm flex-shrink-0 font-bold ${
                candidate.required_skill_score >= 80 ? 'text-green-500' :
                candidate.required_skill_score >= 50 ? 'text-yellow-500' : 'text-red-500'
              }`}>
                {candidate.required_skill_score >= 80 ? '✓' : candidate.required_skill_score >= 50 ? '~' : '✗'}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 dark:text-slate-200">
                  Must-have skills — {candidate.required_skill_score}% matched
                </p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                  {candidate.critical_missing_skills?.length > 0
                    ? `Critical gaps: ${candidate.critical_missing_skills.slice(0, 4).join(', ')}${candidate.critical_missing_skills.length > 4 ? ` +${candidate.critical_missing_skills.length - 4} more` : ''}`
                    : candidate.required_skill_score === 0
                    ? 'No required skills matched — verify resume language and JD keyword alignment'
                    : 'No critical gaps identified'}
                </p>
              </div>
            </div>

            {/* Row: Experience */}
            <div className="flex items-start gap-3 px-4 py-3">
              <span className={`mt-0.5 text-sm flex-shrink-0 font-bold ${
                candidate.experience_meets_requirement === true ? 'text-green-500' :
                candidate.experience_meets_requirement === false ? 'text-red-500' : 'text-gray-400'
              }`}>
                {candidate.experience_meets_requirement === true ? '✓' :
                 candidate.experience_meets_requirement === false ? '✗' : '?'}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 dark:text-slate-200">
                  Minimum experience
                  {candidate.estimated_experience_years != null
                    ? ` — ~${candidate.estimated_experience_years}y detected`
                    : ' — not clearly stated in resume'}
                </p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                  {candidate.experience_meets_requirement === true
                    ? 'Meets the JD experience requirement'
                    : candidate.experience_meets_requirement === false
                    ? 'Below the JD minimum — verify if the role allows junior/trainee candidates'
                    : 'Could not determine — check resume dates manually'}
                </p>
              </div>
            </div>

            {/* Row: Education */}
            <div className="flex items-start gap-3 px-4 py-3">
              <span className={`mt-0.5 text-sm flex-shrink-0 font-bold ${
                candidate.education_meets_requirement === true ? 'text-green-500' :
                candidate.education_meets_requirement === false ? 'text-yellow-500' : 'text-gray-400'
              }`}>
                {candidate.education_meets_requirement === true ? '✓' :
                 candidate.education_meets_requirement === false ? '⚠' : '?'}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 dark:text-slate-200">Education / certification requirement</p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                  {candidate.education_meets_requirement === true
                    ? 'Qualification evidenced in resume'
                    : candidate.education_meets_requirement === false
                    ? 'Not clearly visible in resume — verify manually before screening out'
                    : 'No specific education requirement in JD, or could not auto-detect'}
                </p>
              </div>
            </div>

            {/* Row: Career stability */}
            <div className="flex items-start gap-3 px-4 py-3">
              <span className={`mt-0.5 text-sm flex-shrink-0 font-bold ${
                (candidate.red_flags?.length ?? 0) === 0 ? 'text-green-500' :
                (candidate.red_flags?.length ?? 0) <= 1 ? 'text-yellow-500' : 'text-orange-500'
              }`}>
                {(candidate.red_flags?.length ?? 0) === 0 ? '✓' : '⚠'}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 dark:text-slate-200">
                  Career stability / red flags — {(candidate.red_flags?.length ?? 0) === 0 ? 'none detected' : `${candidate.red_flags.length} flag(s)`}
                </p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                  {(candidate.red_flags?.length ?? 0) === 0
                    ? 'No short tenures, gaps, or vague language detected'
                    : candidate.red_flags?.slice(0, 2).join(' · ')}
                </p>
              </div>
            </div>

            {/* Row: Non-negotiable flags (if any) */}
            {(candidate.non_negotiable_flags?.length > 0 || candidate.review_flags?.length > 0) && (
              <div className="flex items-start gap-3 px-4 py-3 bg-orange-50 dark:bg-orange-950 rounded-b-2xl">
                <span className="mt-0.5 text-sm flex-shrink-0 font-bold text-orange-500">!</span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-orange-800 dark:text-orange-200">
                    {nonNegotiableReview ? 'Non-negotiable review flags' : 'Non-negotiable advisory flags'}
                  </p>
                  {candidate.review_flags?.map((flag, i) => (
                    <p key={`review-${i}`} className="text-xs text-orange-700 dark:text-orange-300 mt-0.5">• {flag}</p>
                  ))}
                  {candidate.non_negotiable_flags?.map((f, i) => (
                    <p key={`advisory-${i}`} className="text-xs text-orange-700 dark:text-orange-300 mt-0.5">• {f}</p>
                  ))}
                </div>
              </div>
            )}

            {/* Always-on human review notice */}
            <div className="px-4 py-2.5 bg-blue-50 dark:bg-blue-950 rounded-b-2xl flex items-center gap-2">
              {/* <span className="text-blue-500 text-sm flex-shrink-0">ℹ</span> */}
              <p className="text-xs text-blue-700 dark:text-blue-300">
                {/* <span className="font-semibold">Human review recommended.</span>{' '} */}
                {/* Automated scoring may miss strong candidates with unconventional profiles, career breaks, or industry transitions. */}
              </p>
            </div>
          </section>

          {/* Score explanations */}
          <section className="space-y-5">
            <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Score Breakdown — What Each Score Means</h3>

            <ScoreBar
              label={SCORE_META.overall_score.label}
              score={activeScore}
              explanation={SCORE_META.overall_score.explanation}
            />
            <ScoreBar
              label={SCORE_META.required_skill_score.label}
              score={candidate.required_skill_score}
              explanation={SCORE_META.required_skill_score.explanation}
            />
            <ScoreBar
              label={SCORE_META.ats_score.label}
              score={candidate.ats_score}
              explanation={SCORE_META.ats_score.explanation}
            />
            <ScoreBar
              label={SCORE_META.skill_support_score.label}
              score={candidate.skill_support_score}
              explanation={SCORE_META.skill_support_score.explanation}
            />

            {/* New Recruiter-Focused Dimensions */}
            {(candidate.career_progression_score > 0 || candidate.achievements_score > 0 || candidate.industry_fit_score > 0) && (
              <>
                <div className="border-t border-gray-200 dark:border-slate-700 pt-4 mt-6">
                  <h4 className="text-xs font-bold uppercase tracking-wide text-purple-600 dark:text-purple-400 mb-4">Recruiter-Focused Assessment</h4>
                </div>
                
                {candidate.career_progression_score > 0 && (
                  <ScoreBar
                    label="Career Progression"
                    score={candidate.career_progression_score}
                    explanation="Career growth, stability, and role advancement indicators"
                  />
                )}
                
                {candidate.achievements_score > 0 && (
                  <ScoreBar
                    label="Achievements & Impact"
                    score={candidate.achievements_score}
                    explanation="Measurable results, quantifiable outcomes, and concrete achievements"
                  />
                )}
                
                {candidate.industry_fit_score > 0 && (
                  <ScoreBar
                    label="Industry/Domain Fit"
                    score={candidate.industry_fit_score}
                    explanation="Alignment with role's industry, domain expertise, and relevant background"
                  />
                )}
              </>
            )}
          </section>

          {/* Certification Coverage */}
          {(candidate.cert_coverage?.has_any_certs || (candidate.cert_coverage && Object.keys(candidate.cert_coverage.jd_skill_cert_map || {}).length > 0)) && (
            <CertificationCoveragePanel
              certCoverage={candidate.cert_coverage}
              jdRequiredSkills={[]}
              jdPreferredSkills={[]}
            />
          )}

          {/* Leadership Signals & Red Flags */}
          {(candidate.leadership_signals?.length > 0 || candidate.red_flags?.length > 0 || candidate.over_tailoring_flag || candidate.language_quality?.quality_level) && (
            <section className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Candidate Signals</h3>
              
              {/* Non-negotiable advisory flags — shown first, before other signals */}
              {(candidate.non_negotiable_flags?.length > 0 || candidate.review_flags?.length > 0 || candidate.non_negotiable_reasons?.length > 0) && (
                <div className="rounded-2xl border-2 border-orange-400 dark:border-orange-600 bg-orange-50 dark:bg-orange-950 p-4 space-y-2">
                  <p className="text-xs font-bold text-orange-800 dark:text-orange-200 uppercase tracking-wide">
                    {nonNegotiableReject ? '⚠ Non-negotiable Criteria — Backend Rejected' : '⚠ Non-negotiable Criteria — Recruiter Review Required'}
                  </p>
                  <p className="text-xs text-orange-600 dark:text-orange-400">
                    These are screening signals that may warrant manual verification before a decision is made.
                    Automated screening can miss strong candidates with unconventional profiles.
                  </p>
                  <ul className="space-y-1.5">
                    {candidate.non_negotiable_reasons?.map((reason, i) => (
                      <li key={`reject-${i}`} className="text-xs text-orange-800 dark:text-orange-200 leading-snug font-medium">• {reason}</li>
                    ))}
                    {candidate.review_flags?.map((flag, i) => (
                      <li key={`review-${i}`} className="text-xs text-orange-800 dark:text-orange-200 leading-snug font-medium">• {flag}</li>
                    ))}
                    {candidate.non_negotiable_flags?.map((flag, i) => (
                      <li key={`flag-${i}`} className="text-xs text-orange-800 dark:text-orange-200 leading-snug font-medium">• {flag}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Education fit result */}
              {candidate.education_meets_requirement !== null && candidate.education_meets_requirement !== undefined && (
                <div className={`rounded-2xl border p-3.5 ${
                  candidate.education_meets_requirement
                    ? 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800'
                    : 'bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800'
                }`}>
                  <div className="flex items-center gap-2">
                    <span className={candidate.education_meets_requirement ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400'}>
                      {candidate.education_meets_requirement ? '✓' : '⚠'}
                    </span>
                    <div>
                      <p className={`text-xs font-bold ${
                        candidate.education_meets_requirement ? 'text-green-800 dark:text-green-200' : 'text-orange-800 dark:text-orange-200'
                      }`}>
                        Education / Certification Requirement — {candidate.education_meets_requirement ? 'Evidenced' : 'Not Clearly Evidenced'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                        {candidate.education_meets_requirement
                          ? 'Resume education section appears to match JD requirements.'
                          : 'JD education requirement not clearly visible in resume — verify manually before screening out.'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {candidate.over_tailoring_flag && (
                <div className="rounded-2xl border-2 border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-950 p-4">
                  <p className="text-xs font-bold text-amber-800 dark:text-amber-200 uppercase tracking-wide mb-1.5">
                    ⚠ Possibly Over-Tailored to This JD
                  </p>
                  <p className="text-sm text-amber-700 dark:text-amber-300 leading-snug">
                    This resume shows near-perfect required skill coverage with a high overall score. While that's often positive,
                    it can occasionally indicate keyword stuffing or a resume reverse-engineered from the JD rather than reflecting genuine experience.
                  </p>
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 italic">
                    Recommendation: Verify claims in a phone/video screen. Ask for specific examples of each claimed skill.
                  </p>
                </div>
              )}

              {/* Language quality analysis */}
              {candidate.language_quality?.quality_level && (
                <div className={`rounded-2xl border p-4 ${
                  candidate.language_quality.quality_level === 'strong'
                    ? 'bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800'
                    : candidate.language_quality.quality_level === 'mixed'
                    ? 'bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800'
                    : 'bg-gray-50 dark:bg-slate-800 border-gray-200 dark:border-slate-700'
                }`}>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <p className={`text-xs font-bold uppercase tracking-wide mb-0.5 ${
                        candidate.language_quality.quality_level === 'strong' ? 'text-emerald-800 dark:text-emerald-200'
                        : candidate.language_quality.quality_level === 'mixed' ? 'text-blue-800 dark:text-blue-200'
                        : 'text-gray-700 dark:text-slate-300'
                      }`}>
                        Language Quality — Action Verb Analysis
                      </p>
                      <p className="text-sm text-gray-600 dark:text-slate-400">{candidate.language_quality.quality_label}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className={`text-2xl font-bold ${
                        candidate.language_quality.quality_level === 'strong' ? 'text-emerald-600 dark:text-emerald-400'
                        : candidate.language_quality.quality_level === 'mixed' ? 'text-blue-600 dark:text-blue-400'
                        : 'text-gray-500 dark:text-slate-400'
                      }`}>{candidate.language_quality.active_ratio ?? 0}%</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">active verbs</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {candidate.language_quality.active_verbs?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1.5">
                          ✓ Initiative verbs ({candidate.language_quality.active_count})
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {candidate.language_quality.active_verbs.map((v, i) => (
                            <span key={i} className="rounded-full bg-emerald-100 dark:bg-emerald-900 border border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300 px-2 py-0.5 text-xs font-medium">
                              {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {candidate.language_quality.passive_verbs?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 mb-1.5">
                          〰 Support verbs ({candidate.language_quality.passive_count})
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {candidate.language_quality.passive_verbs.map((v, i) => (
                            <span key={i} className="rounded-full bg-gray-100 dark:bg-slate-700 border border-gray-300 dark:border-slate-600 text-gray-500 dark:text-slate-400 px-2 py-0.5 text-xs">
                              {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-2.5 italic">
                    {candidate.language_quality.seniority_level
                      ? `Calibrated for ${candidate.language_quality.seniority_level}-level role. `
                      : ''}
                    {candidate.language_quality.seniority_level === 'junior'
                      ? 'Some support language is normal at junior/entry level — assess depth of initiative rather than verb choice alone.'
                      : candidate.language_quality.seniority_level === 'senior' || candidate.language_quality.seniority_level === 'lead'
                      ? 'Senior/lead roles benefit from strong ownership language — mixed verbs may warrant a conversation about decision-making scope.'
                      : 'Language style varies by role seniority. View alongside experience level when assessing.'
                    }
                  </p>
                </div>
              )}
              
              {candidate.leadership_signals?.length > 0 && (
                <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 p-4">
                  <p className="text-xs font-bold text-emerald-800 dark:text-emerald-200 uppercase tracking-wide mb-2">
                    ✓ Positive Leadership Signals
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {candidate.leadership_signals.map((signal, i) => (
                      <span key={i} className="rounded-full bg-emerald-100 dark:bg-emerald-900 border border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300 px-3 py-1 text-xs font-medium">
                        {signal}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-2">
                    Demonstrates initiative, ownership, and leadership through action verbs
                  </p>
                </div>
              )}
              
              {candidate.red_flags?.length > 0 && (
                <div className="rounded-2xl bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 p-4">
                  <p className="text-xs font-bold text-orange-800 dark:text-orange-200 uppercase tracking-wide mb-2">
                    ⚠ Potential Concerns
                  </p>
                  <ul className="space-y-1.5">
                    {candidate.red_flags.map((flag, i) => (
                      <li key={i} className="text-xs text-orange-700 dark:text-orange-300 leading-snug">
                        • {flag}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-orange-700 dark:text-orange-400 mt-2 italic">
                    These are flags to review — not automatic rejections. Unconventional profiles can still be strong candidates.
                  </p>
                </div>
              )}
            </section>
          )}

          {/* Score interpretation guide */}
          <section className="rounded-2xl bg-gray-50 dark:bg-slate-800 p-5 space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">How to Read These Scores</h3>
            <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
              {[
                { range: '85 – 100', label: 'Excellent Fit', color: 'text-emerald-600' },
                { range: '70 – 84', label: 'Good Fit', color: 'text-blue-600' },
                { range: '50 – 69', label: 'Average Fit', color: 'text-yellow-600' },
                { range: '0 – 49', label: 'Low Fit', color: 'text-red-500' },
              ].map((g) => (
                <div key={g.range} className="rounded-xl bg-white dark:bg-slate-900 p-3 text-center border border-gray-100 dark:border-slate-700">
                  <p className={`font-bold ${g.color}`}>{g.range}</p>
                  <p className="text-gray-500 dark:text-slate-400 mt-0.5">{g.label}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-slate-400 pt-1">
              Scores should be read together — a 65 overall with zero critical gaps and strong evidence is often a better choice than a 72 with 3 critical gaps.
            </p>
          </section>

          {/* Experience */}
          <section className="space-y-2">
            <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Experience</h3>
            <div className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 flex items-center gap-4">
              <div className="text-center min-w-[64px]">
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {candidate.estimated_experience_years != null ? `${candidate.estimated_experience_years}y` : '–'}
                </p>
                <p className="text-xs text-gray-500 dark:text-slate-400">estimated</p>
              </div>
              <div className="flex-1 text-sm text-gray-600 dark:text-slate-400">
                {candidate.experience_meets_requirement === true && (
                  <span className="text-green-600 font-semibold">✓ Likely meets the JD experience requirement</span>
                )}
                {candidate.experience_meets_requirement === false && (
                  <span className="text-red-500 font-semibold">✗ May fall below the JD experience requirement</span>
                )}
                {candidate.experience_meets_requirement == null && (
                  <span className="text-gray-400">Experience requirement could not be confirmed from resume</span>
                )}
              </div>
            </div>
          </section>

          {/* Skills breakdown */}
          <section className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Skill Coverage</h3>

            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1.5">
                  Matched Skills ({candidate.matched_skills.length})
                  <span className="ml-1 font-normal text-gray-500">— present in resume and required by JD</span>
                </p>
                <SkillChips skills={candidate.matched_skills} variant="matched" />
              </div>

              {candidate.critical_missing_skills.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-red-600 dark:text-red-400 mb-1.5">
                    Critical Missing Skills ({candidate.critical_missing_skills.length})
                    <span className="ml-1 font-normal text-gray-500">— required by JD but absent from resume</span>
                  </p>
                  <SkillChips skills={candidate.critical_missing_skills} variant="critical" />
                </div>
              )}

              {candidate.missing_skills.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">
                    Other Missing Skills ({candidate.missing_skills.length})
                    <span className="ml-1 font-normal text-gray-500">— preferred or general JD keywords not found</span>
                  </p>
                  <SkillChips skills={candidate.missing_skills.slice(0, 20)} variant="missing" />
                </div>
              )}
            </div>
          </section>

          {/* Evidence Summary */}
          {candidate.evidence_summary && (
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Evidence Quality</h3>
              <p className="text-xs text-gray-500 dark:text-slate-400">Skills backed by concrete resume evidence vs. simply listed.</p>
              <div className="space-y-2">
                {candidate.evidence_summary.strong_evidence_skills?.length > 0 && (
                  <div className="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 p-3">
                    <p className="text-xs font-bold text-green-800 dark:text-green-200 mb-1.5">Strong Evidence ({candidate.evidence_summary.strong_evidence_skills.length})</p>
                    <div className="flex flex-wrap gap-1">
                      {candidate.evidence_summary.strong_evidence_skills.map((s, i) => (
                        <span key={i} className="rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800 px-2 py-0.5 text-xs">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {candidate.evidence_summary.medium_evidence_skills?.length > 0 && (
                  <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 p-3">
                    <p className="text-xs font-bold text-blue-800 dark:text-blue-200 mb-1.5">Medium Evidence ({candidate.evidence_summary.medium_evidence_skills.length})</p>
                    <div className="flex flex-wrap gap-1">
                      {candidate.evidence_summary.medium_evidence_skills.map((s, i) => (
                        <span key={i} className="rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 px-2 py-0.5 text-xs">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {candidate.evidence_summary.weak_evidence_skills?.length > 0 && (
                  <div className="rounded-xl border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-950 p-3">
                    <p className="text-xs font-bold text-yellow-800 dark:text-yellow-200 mb-1.5">Weak Evidence ({candidate.evidence_summary.weak_evidence_skills.length}) — listed but not demonstrated</p>
                    <div className="flex flex-wrap gap-1">
                      {candidate.evidence_summary.weak_evidence_skills.map((s, i) => (
                        <span key={i} className="rounded-full bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800 px-2 py-0.5 text-xs">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Timeline Gaps */}
          {candidate.timeline_gaps?.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Career Timeline Flags</h3>
              <div className="rounded-2xl border border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950 p-4 space-y-1">
                {candidate.timeline_gaps.map((gap, i) => (
                  <p key={i} className="text-xs text-orange-700 dark:text-orange-300">• {gap}</p>
                ))}
                <p className="text-xs text-orange-600 dark:text-orange-400 mt-1.5 italic">Verify context with candidate before screening out.</p>
              </div>
            </section>
          )}

          {/* Keyword coverage */}
          {(() => {
            const strongItems = (candidate.keyword_coverage_items || []).filter(i => i.status === 'strong')
            const missingItems = (candidate.keyword_coverage_items || []).filter(i => i.status === 'missing')
            const atsIssues = candidate.ats_issues || []

            const boxes = [
              {
                key: 'strong',
                label: 'Strong evidence',
                value: candidate.keyword_strong_count,
                color: 'text-green-600',
                ring: 'ring-green-400',
                clickable: strongItems.length > 0,
              },
              {
                key: 'missing',
                label: 'Missing',
                value: candidate.keyword_missing_count,
                color: 'text-red-500',
                ring: 'ring-red-400',
                clickable: missingItems.length > 0 || (candidate.missing_skills || []).length > 0,
              },
              {
                key: 'ats',
                label: 'ATS issues',
                value: candidate.ats_issues_count,
                color: 'text-yellow-600',
                ring: 'ring-yellow-400',
                clickable: atsIssues.length > 0,
              },
              {
                key: null,
                label: 'Overall',
                value: activeScore,
                color: 'text-blue-600',
                ring: '',
                clickable: false,
              },
            ]

            return (
              <section className="rounded-2xl bg-gray-50 dark:bg-slate-800 p-5 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Keyword Coverage Summary</h3>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  Click a stat to see the details. Strong evidence = keyword found with supporting proof in resume.
                </p>

                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 mt-1">
                  {boxes.map((s) => (
                    <button
                      key={s.label}
                      type="button"
                      disabled={!s.clickable}
                      onClick={() => s.clickable && setExpandedBox(expandedBox === s.key ? null : s.key)}
                      className={[
                        'rounded-xl bg-white dark:bg-slate-900 p-3 text-center border transition',
                        s.clickable
                          ? 'border-gray-200 dark:border-slate-600 hover:shadow-md cursor-pointer'
                          : 'border-gray-100 dark:border-slate-700 cursor-default',
                        expandedBox === s.key ? `ring-2 ${s.ring}` : '',
                      ].join(' ')}
                    >
                      <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                      <p className="text-gray-500 dark:text-slate-400 mt-0.5 leading-tight">{s.label}</p>
                      {s.clickable && <p className="text-gray-400 dark:text-slate-500 mt-1">{expandedBox === s.key ? '▲ hide' : '▼ show'}</p>}
                    </button>
                  ))}
                </div>

                {/* Strong evidence drill-down */}
                {expandedBox === 'strong' && strongItems.length > 0 && (
                  <div className="mt-2 rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 p-4 space-y-3">
                    <p className="text-xs font-bold text-green-700 dark:text-green-300 uppercase tracking-wide">Keywords with strong evidence ({strongItems.length})</p>
                    <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                      {strongItems.map((item) => (
                        <div key={item.skill} className="text-xs">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <span className="font-semibold text-green-800 dark:text-green-200">{item.skill}</span>
                            {(item.evidence_sections || []).map((sec) => (
                              <span key={sec} className="rounded-full bg-green-100 dark:bg-green-900 px-2 py-0.5 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-700">
                                {sec}
                              </span>
                            ))}
                          </div>
                          {(item.supporting_lines || []).length > 0 && (
                            <ul className="pl-3 space-y-1 border-l-2 border-green-200 dark:border-green-700">
                              {item.supporting_lines.map((line, li) => (
                                <li key={li} className="text-gray-600 dark:text-slate-300 italic leading-snug">&ldquo;{line}&rdquo;</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Missing skills drill-down */}
                {expandedBox === 'missing' && (
                  <div className="mt-2 rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 p-4 space-y-2">
                    <p className="text-xs font-bold text-red-700 dark:text-red-300 uppercase tracking-wide">Missing JD keywords</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(missingItems.length > 0 ? missingItems.map(i => i.skill) : (candidate.missing_skills || [])).map((skill) => (
                        <span key={skill} className="rounded-full bg-red-100 dark:bg-red-900 px-2.5 py-1 text-xs font-medium text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* ATS issues drill-down */}
                {expandedBox === 'ats' && atsIssues.length > 0 && (
                  <div className="mt-2 rounded-xl border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-950 p-4 space-y-3">
                    <p className="text-xs font-bold text-yellow-700 dark:text-yellow-300 uppercase tracking-wide">ATS issues ({atsIssues.length})</p>
                    <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                      {atsIssues.map((issue, idx) => (
                        <div key={idx} className="rounded-lg border border-yellow-200 dark:border-yellow-700 bg-white dark:bg-slate-900 p-3 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className={[
                              'rounded-full px-2 py-0.5 text-xs font-bold uppercase',
                              issue.severity === 'high' ? 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300' :
                              issue.severity === 'medium' ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300' :
                              'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300',
                            ].join(' ')}>
                              {issue.severity || 'info'}
                            </span>
                            <span className="text-sm font-semibold text-gray-900 dark:text-white">{issue.title}</span>
                          </div>
                          {issue.details && <p className="text-xs text-gray-600 dark:text-slate-300">{issue.details}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )
          })()}

          {/* Shortlist reasons */}
          {candidate.shortlist_reasons.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Screening Signals</h3>
              <p className="text-xs text-gray-500 dark:text-slate-400">
                Key flags identified during automated screening. These are indicators, not final decisions.
              </p>
              <ul className="space-y-2">
                {candidate.shortlist_reasons.map((r, i) => (
                  <li key={i} className="flex gap-2.5 rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-900 p-3 text-sm text-gray-700 dark:text-slate-300">
                    <span className="flex-shrink-0 text-gray-400">→</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* AI Recommendation */}
          {candidate.recommendation && (
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">AI Recommendation</h3>
              <RecommendationPanel recommendation={candidate.recommendation} />
            </section>
          )}

          {/* Recruiter Notes */}
          <section className="space-y-3">
            <NotesPanel 
              candidateId={`${candidate.filename}-${candidate.candidate_index || 0}`} 
              candidateName={candidate.filename} 
            />
          </section>

          {/* Disclaimer */}
          <div className="rounded-2xl border border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950 p-4 text-xs text-blue-700 dark:text-blue-300">
            {/* <strong>Recruiter note:</strong> These scores are AI-assisted signals to support — not replace — your judgment. Always review the full resume before making final shortlisting or rejection decisions. */}
          </div>

        </div>
      </div>
    </>
  )
}
