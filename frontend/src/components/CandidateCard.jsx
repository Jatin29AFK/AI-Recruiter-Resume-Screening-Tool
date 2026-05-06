import { useState, useRef, useEffect } from 'react'
import {
  HIRING_STAGE_OPTIONS,
  getCandidateId,
  getCandidateStage,
  getRejectionExplanation,
} from '../utils/candidateInsights'

const STATUS_GROUPS = [
  { label: 'Hiring Stage', options: ['New', 'Screening', 'Phone Screen', 'Interview', 'Technical Round'] },
  { label: 'Decision',     options: ['Offer', 'Hired', 'On Hold', 'Rejected'] },
]

/** Custom dropdown — button shows category label; panel shows options with checkmark */
function StatusDropdown({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1 text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-2.5 py-1 font-semibold text-gray-600 dark:text-gray-300 hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition whitespace-nowrap"
      >
        <span>{value || 'Hiring Stage'}</span>
        <span className="opacity-40 text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-30 min-w-[160px] rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-xl py-1 overflow-hidden">
          {STATUS_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="px-3 pt-2 pb-0.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-slate-500">
                {group.label}
              </p>
              {group.options.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => { onChange(opt); setOpen(false) }}
                  className={`w-full text-left px-3 py-1.5 text-xs font-medium transition flex items-center gap-2 hover:bg-blue-50 dark:hover:bg-slate-700 ${
                    value === opt
                      ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-slate-700'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  <span className="w-3 flex-shrink-0 text-center text-blue-500">{value === opt ? '✓' : ''}</span>
                  {opt}
                </button>
              ))} 
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const BUCKET_STYLES = {
  Shortlist: 'bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-200 border-green-200 dark:border-green-800',
  Review:    'bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800',
  Reject:    'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-200 border-red-200 dark:border-red-800',
}

/** How confident is the recruiter to forward this candidate to the hiring manager */
/** Auto-tags explaining why a candidate is in a bucket */
function getRejectionTags(candidate) {
  const activeScore = candidate._weighted_score ?? candidate.overall_score
  const tags = []
  if (candidate.critical_missing_skills.length > 0)
    tags.push(`Missing ${candidate.critical_missing_skills.length} critical skill${candidate.critical_missing_skills.length > 1 ? 's' : ''}`)
  if (candidate.experience_meets_requirement === false)
    tags.push('Below experience req.')
  if (candidate.ats_score < 55)
    tags.push('ATS risk')
  if (candidate.skill_support_score < 45)
    tags.push('Low evidence quality')
  if (activeScore < 40)
    tags.push('Weak overall match')
  return tags
}

export default function CandidateCard({ candidate, rank, onViewDetails, onStatusChange }) {
  const bucketStyle = BUCKET_STYLES[candidate.shortlist_verdict] || 'bg-gray-100 text-gray-700 border-gray-200'
  const activeScore = candidate._weighted_score ?? candidate.overall_score

  const activeStageRejected = getCandidateStage(candidate) === 'Rejected'
  const showRejectionReason =
    candidate.shortlist_verdict === 'Reject' ||
    activeStageRejected
  const rejectionTags = showRejectionReason ? getRejectionTags(candidate) : []
  const rejectionExplanation = showRejectionReason ? getRejectionExplanation(candidate) : ''
  const nonNegotiableReject = candidate.non_negotiable_verdict === 'reject' && candidate.shortlist_verdict === 'Reject'
  const nonNegotiableReview = candidate.non_negotiable_verdict === 'review'

  const candidateStatus = getCandidateStage(candidate)
  // Which badge section is expanded inline: 'matched' | 'gaps' | 'strengths' | 'redflags' | null
  const [expandedBadge, setExpandedBadge] = useState(null)

  const toggleBadge = (key) => setExpandedBadge(prev => prev === key ? null : key)

  const handleStatusChange = async (newStatus) => {
    if (!HIRING_STAGE_OPTIONS.includes(newStatus)) return
    await onStatusChange?.(candidate, newStatus, getCandidateId(candidate))
  }

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 shadow-sm hover:shadow-md transition-all space-y-4">

      {/* Header: name + bucket + status */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 dark:bg-slate-800 text-xs font-bold text-gray-500 dark:text-slate-400">
            #{rank}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-gray-900 dark:text-white">{candidate.filename}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{candidate.fit_label}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={`flex-shrink-0 rounded-full border px-3 py-1 text-xs font-bold ${bucketStyle}`}>
            {candidate.shortlist_verdict}
          </span>
          <StatusDropdown value={candidateStatus} onChange={handleStatusChange} />
        </div>
      </div>

      {/* Overall score */}
      <div className="flex items-stretch gap-3">
        <div className="flex flex-1 flex-col items-center justify-center rounded-xl bg-gray-50 dark:bg-slate-800 py-3">
          <span className={`text-3xl font-bold ${
            activeScore >= 70 ? 'text-green-600 dark:text-green-400'
            : activeScore >= 50 ? 'text-yellow-600 dark:text-yellow-400'
            : 'text-red-500 dark:text-red-400'
          }`}>{activeScore}</span>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">Overall match</p>
        </div>
      </div>

      {/* Key facts — clickable badges expand inline */}
      <div className="flex flex-wrap gap-1.5 text-xs">
        <button
          type="button"
          onClick={() => toggleBadge('matched')}
          className={`rounded-full border px-2.5 py-1 font-medium transition cursor-pointer ${
            expandedBadge === 'matched'
              ? 'bg-green-100 dark:bg-green-900 border-green-400 dark:border-green-500 text-green-800 dark:text-green-200'
              : 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-900'
          }`}
          title="Click to see matched skills"
        >
          ✓ {candidate.matched_skills.length} matched {expandedBadge === 'matched' ? '▲' : '▼'}
        </button>
        {candidate.critical_missing_skills.length > 0 && (
          <button
            type="button"
            onClick={() => toggleBadge('gaps')}
            className={`rounded-full border px-2.5 py-1 font-medium transition cursor-pointer ${
              expandedBadge === 'gaps'
                ? 'bg-red-100 dark:bg-red-900 border-red-400 dark:border-red-500 text-red-700 dark:text-red-200'
                : 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 text-red-600 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900'
            }`}
            title="Click to see critical gaps"
          >
            ✗ {candidate.critical_missing_skills.length} critical gap{candidate.critical_missing_skills.length !== 1 ? 's' : ''} {expandedBadge === 'gaps' ? '▲' : '▼'}
          </button>
        )}
        {candidate.estimated_experience_years != null && (
          <span className="rounded-full bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 px-2.5 py-1 font-medium">
            {candidate.estimated_experience_years}y exp{candidate.experience_meets_requirement === true ? ' ✓' : candidate.experience_meets_requirement === false ? ' ✗' : ''}
          </span>
        )}
      </div>

      {/* Inline expanded: matched skills */}
      {expandedBadge === 'matched' && candidate.matched_skills.length > 0 && (
        <div className="rounded-xl bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 px-3 py-2">
          <p className="text-xs font-bold text-green-700 dark:text-green-400 mb-1.5">Matched Skills</p>
          <div className="flex flex-wrap gap-1">
            {candidate.matched_skills.map(s => (
              <span key={s} className="rounded-full bg-green-100 dark:bg-green-900 border border-green-300 dark:border-green-700 text-green-800 dark:text-green-200 px-2 py-0.5 text-xs font-medium">{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Inline expanded: critical gaps */}
      {expandedBadge === 'gaps' && candidate.critical_missing_skills.length > 0 && (
        <div className="rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-3 py-2">
          <p className="text-xs font-bold text-red-600 dark:text-red-400 mb-1.5">Critical Gaps — Required skills not found in resume</p>
          <div className="flex flex-wrap gap-1">
            {candidate.critical_missing_skills.map(s => (
              <span key={s} className="rounded-full bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-200 px-2 py-0.5 text-xs font-medium">{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Why rejected */}
      {showRejectionReason && rejectionExplanation && (
        <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 px-3 py-2">
          <p className="text-xs font-bold text-red-700 dark:text-red-300 uppercase tracking-wide">Why rejected</p>
          <p className="mt-1 text-xs leading-snug text-red-700 dark:text-red-200">{rejectionExplanation}</p>
        </div>
      )}

      {rejectionTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {rejectionTags.map((tag) => (
            <span key={tag} className="rounded-full border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 px-2.5 py-1 text-xs font-medium text-red-600 dark:text-red-300">
              {tag}
            </span>
          ))}
        </div>
      )}

      {showRejectionReason && nonNegotiableReject && candidate.non_negotiable_reasons?.length > 0 && (
        <div className="rounded-xl border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950 px-3 py-2 space-y-1">
          <p className="text-xs font-bold text-red-700 dark:text-red-300 uppercase tracking-wide">Rejected on non-negotiables</p>
          {candidate.non_negotiable_reasons.slice(0, 2).map((reason, i) => (
            <p key={i} className="text-xs text-red-700 dark:text-red-200 leading-snug">• {reason}</p>
          ))}
        </div>
      )}

      {!nonNegotiableReject && nonNegotiableReview && candidate.review_flags?.length > 0 && (
        <div className="rounded-xl border border-orange-300 dark:border-orange-700 bg-orange-50 dark:bg-orange-950 px-3 py-2 space-y-1">
          <p className="text-xs font-bold text-orange-700 dark:text-orange-300 uppercase tracking-wide">Manual review needed</p>
          {candidate.review_flags.slice(0, 2).map((flag, i) => (
            <p key={i} className="text-xs text-orange-700 dark:text-orange-200 leading-snug">• {flag}</p>
          ))}
        </div>
      )}

      {/* Non-negotiable advisory flags */}
      {candidate.non_negotiable_flags?.length > 0 && (
        <div className="rounded-xl border border-orange-300 dark:border-orange-700 bg-orange-50 dark:bg-orange-950 px-3 py-2 space-y-1">
          <p className="text-xs font-bold text-orange-700 dark:text-orange-300 uppercase tracking-wide">⚠ Non-negotiable Review Required</p>
          {candidate.non_negotiable_flags.slice(0, 2).map((flag, i) => (
            <p key={i} className="text-xs text-orange-700 dark:text-orange-200 leading-snug">• {flag}</p>
          ))}
        </div>
      )}

      {/* Education fit — only show if JD had education requirements and result is known */}
      {candidate.education_meets_requirement === false && (
        <span className="inline-flex items-center gap-1 rounded-full border border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950 px-2.5 py-1 text-xs font-medium text-orange-700 dark:text-orange-300">
          ⚠ Education req. not evidenced
        </span>
      )}
      {candidate.education_meets_requirement === true && (
        <span className="inline-flex items-center gap-1 rounded-full border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 px-2.5 py-1 text-xs font-medium text-green-700 dark:text-green-300">
          ✓ Education req. met
        </span>
      )}

      {/* Over-tailoring warning */}
      {candidate.over_tailoring_flag && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950 px-3 py-2">
          <span className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5">⚠</span>
          <div>
            <p className="text-xs font-bold text-amber-700 dark:text-amber-300">Possibly Over-Tailored</p>
            <p className="text-xs text-amber-600 dark:text-amber-400 leading-snug">Near-perfect JD match can indicate keyword stuffing. Verify genuine experience.</p>
          </div>
        </div>
      )}

      {/* Language quality signal */}
      {candidate.language_quality?.quality_level && (
        <div className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 ${
          candidate.language_quality.quality_level === 'strong'
            ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950'
            : candidate.language_quality.quality_level === 'mixed'
            ? 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950'
            : 'border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800'
        }`}>
          <span className="text-sm">{candidate.language_quality.quality_level === 'strong' ? ' ' : candidate.language_quality.quality_level === 'mixed' ? '〰' : '💬'}</span>
          <div className="min-w-0">
            <p className={`text-xs font-semibold leading-tight ${
              candidate.language_quality.quality_level === 'strong' ? 'text-emerald-700 dark:text-emerald-300'
              : candidate.language_quality.quality_level === 'mixed' ? 'text-blue-700 dark:text-blue-300'
              : 'text-gray-600 dark:text-slate-300'
            }`}>
              Language: {candidate.language_quality.active_ratio ?? 0}% active verbs
            </p>
            <p className="text-xs text-gray-500 dark:text-slate-400 truncate">{candidate.language_quality.quality_label}</p>
          </div>
        </div>
      )}

      {/* Strengths & Red Flags — from AI recommendation */}
      {candidate.recommendation && (
        <div className="space-y-2">
          {candidate.recommendation.key_strengths?.length > 0 && (
            <div className="rounded-xl bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 px-3 py-2 space-y-1">
              <button
                type="button"
                onClick={() => toggleBadge('strengths')}
                className="w-full text-left flex items-center justify-between"
              >
                <p className="text-xs font-bold text-green-700 dark:text-green-400 uppercase tracking-wide">
                  Strengths ({candidate.recommendation.key_strengths.length})
                </p>
                <span className="text-xs text-green-600 dark:text-green-400">{expandedBadge === 'strengths' ? '▲' : '▼'}</span>
              </button>
              {(expandedBadge === 'strengths' ? candidate.recommendation.key_strengths : candidate.recommendation.key_strengths.slice(0, 2)).map((s, i) => (
                <p key={i} className="text-xs text-green-800 dark:text-green-300 leading-snug">✓ {s}</p>
              ))}
            </div>
          )}
          {candidate.recommendation.gaps_and_risks?.length > 0 && (
            <div className="rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-3 py-2 space-y-1">
              <button
                type="button"
                onClick={() => toggleBadge('redflags')}
                className="w-full text-left flex items-center justify-between"
              >
                <p className="text-xs font-bold text-red-600 dark:text-red-400 uppercase tracking-wide">
                  Red Flags ({candidate.recommendation.gaps_and_risks.length})
                </p>
                <span className="text-xs text-red-500 dark:text-red-400">{expandedBadge === 'redflags' ? '▲' : '▼'}</span>
              </button>
              {(expandedBadge === 'redflags' ? candidate.recommendation.gaps_and_risks : candidate.recommendation.gaps_and_risks.slice(0, 2)).map((g, i) => (
                <p key={i} className="text-xs text-red-700 dark:text-red-300 leading-snug">✗ {g}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Full analysis button */}
      {onViewDetails && (
        <button
          type="button"
          onClick={() => onViewDetails(candidate)}
          className="w-full rounded-xl border border-gray-200 dark:border-slate-700 py-2 text-xs font-semibold text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-800 hover:border-blue-300 dark:hover:border-blue-700 transition"
        >
          Full Analysis →
        </button>
      )}
    </div>
  )
}
