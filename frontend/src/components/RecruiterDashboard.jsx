import { useState, useRef, useEffect } from 'react'
import CandidateCard from './CandidateCard'
import CandidateDetailPanel from './CandidateDetailPanel'
import { getCandidateStatuses, updateCandidateStatus } from '../services/api'
import {
  HIRING_STAGE_OPTIONS,
  getCandidateId,
  getCandidateStage,
} from '../utils/candidateInsights'

const WEIGHT_OPTIONS = [
  { value: 'High',   label: 'High',   sub: 'Critical — must have' },
  { value: 'Medium', label: 'Medium', sub: 'Important' },
  { value: 'Low',    label: 'Low',    sub: 'Nice to have' },
]

/** Custom weight dropdown — button shows “Priority Level”; panel shows options */
function WeightDropdown({ value, onChange }) {
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
        className="flex items-center gap-1.5 rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-700 dark:text-white px-3 py-2 text-sm font-semibold hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400 transition whitespace-nowrap"
      >
        <span>Priority Level</span>
        <span className="opacity-40 text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-30 min-w-[180px] rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-xl py-1 overflow-hidden">
          <p className="px-3 pt-2 pb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-slate-500">
            Priority Level
          </p>
          {WEIGHT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { onChange(opt.value); setOpen(false) }}
              className={`w-full text-left px-3 py-2 text-sm transition flex items-center gap-2 hover:bg-blue-50 dark:hover:bg-slate-700 ${
                value === opt.value
                  ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-slate-700'
                  : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              <span className="w-3 flex-shrink-0 text-center text-blue-500 text-xs">{value === opt.value ? '✓' : ''}</span>
              <div>
                <p className="font-semibold leading-tight">{opt.label}</p>
                <p className="text-xs opacity-60 leading-tight">{opt.sub}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

const BUCKET_TABS = [
  { key: 'all', label: 'All Candidates' },
  { key: 'Shortlist', label: 'Shortlist' },
  { key: 'Review', label: 'Review' },
  { key: 'Reject', label: 'Reject' },
]

const SCORE_GUIDE = [
  {
    name: 'Overall Match',
    key: 'overall_score',
    description: 'Primary fit score combining skills, experience, and evidence quality',
    ranges: [{ r: '≥85', label: 'Excellent' }, { r: '70–84', label: 'Good' }, { r: '50–69', label: 'Average' }, { r: '<50', label: 'Low' }],
  },
  {
    name: 'Required Skills %',
    key: 'required_skill_score',
    description: 'Percentage of must-have skills from the JD found in the resume',
    ranges: [{ r: '≥80', label: 'Most covered' }, { r: '50–79', label: 'Partial' }, { r: '<50', label: 'Low coverage' }],
  },
  {
    name: 'ATS Formatting',
    key: 'ats_score',
    description: 'How well the resume survives automated scanning systems',
    ranges: [{ r: '≥80', label: 'ATS-friendly' }, { r: '60–79', label: 'Acceptable' }, { r: '<60', label: 'ATS risk' }],
  },
  {
    name: 'Evidence Quality',
    key: 'skill_support_score',
    description: 'Skills backed by concrete achievements and measurable results',
    ranges: [{ r: '≥70', label: 'Well evidenced' }, { r: '40–69', label: 'Partial' }, { r: '<40', label: 'Claims only' }],
  },
]

// Points added/deducted per skill weight tier
const WEIGHT_POINTS = { High: 15, Medium: 8, Low: 3 }
const WEIGHT_PENALTY = { High: 8, Medium: 0, Low: 0 }  // penalty if skill is absent
const DEFAULT_SKILL_WEIGHT = 'Medium'
const TOTAL_WEIGHT = 100
const WEIGHT_STEP = 5

const SKILL_ALIASES = {
  'reactjs': 'react',
  'react js': 'react',
  'react.js': 'react',
  'nodejs': 'node.js',
  'node js': 'node.js',
  'nextjs': 'next.js',
  'next js': 'next.js',
  'vuejs': 'vue.js',
  'vue js': 'vue.js',
  'angularjs': 'angular',
  'java script': 'javascript',
  'js': 'javascript',
  'ts': 'typescript',
  'py': 'python',
  'postgres': 'postgresql',
  'amazon web services': 'aws',
  'google cloud platform': 'gcp',
  'rn': 'react native',
}

// Default scoring component weights (recruiter-adjustable per JD)
const DEFAULT_SCORING_WEIGHTS = {
  requiredSkills: 25,
  preferredSkills: 10,
  atsCompatibility: 10,
  experienceFit: 15,
  evidenceQuality: 15,
  achievementsImpact: 10,
  industryFit: 8,
  careerProgression: 7,
}

const SCORING_WEIGHT_META = [
  { key: 'requiredSkills',      label: 'Required skills',         description: 'Must-have JD skills present in resume', color: 'text-red-600 dark:text-red-400', accent: 'accent-red-500' },
  { key: 'preferredSkills',     label: 'Preferred skills',        description: 'Nice-to-have JD skills present in resume', color: 'text-sky-600 dark:text-sky-400', accent: 'accent-sky-500' },
  { key: 'atsCompatibility',    label: 'ATS compatibility',       description: 'Resume ATS readability and parsing friendliness', color: 'text-violet-600 dark:text-violet-400', accent: 'accent-violet-500' },
  { key: 'experienceFit',       label: 'Experience fit',          description: 'How closely experience level matches requirement', color: 'text-blue-600 dark:text-blue-400', accent: 'accent-blue-500' },
  { key: 'evidenceQuality',     label: 'Evidence quality',        description: 'Claims supported by concrete resume evidence', color: 'text-indigo-600 dark:text-indigo-400', accent: 'accent-indigo-500' },
  { key: 'achievementsImpact',  label: 'Achievements / impact',   description: 'Measurable results, numbers, quantified outcomes', color: 'text-emerald-600 dark:text-emerald-400', accent: 'accent-emerald-500' },
  { key: 'industryFit',         label: 'Industry / domain fit',   description: 'Alignment with role domain and sector experience', color: 'text-orange-600 dark:text-orange-400', accent: 'accent-orange-500' },
  { key: 'careerProgression',   label: 'Career progression',      description: 'Stable growth, promotions, increasing responsibility', color: 'text-teal-600 dark:text-teal-400', accent: 'accent-teal-500' },
]

const DEFAULT_SCORING_FEATURES = {
  requiredSkills: true,
  preferredSkills: true,
  atsCompatibility: true,
  experienceFit: true,
  evidenceQuality: true,
  achievementsImpact: true,
  industryFit: true,
  careerProgression: true,
}

const DEFAULT_ROLE_PARAMETER_WEIGHTS = {
  mustHaveMatch: 40,
  relevantExperience: 20,
  preferredSkills: 15,
  achievementsImpact: 10,
  industryFit: 10,
  careerProgression: 5,
}

const ROLE_PARAMETER_META = [
  { key: 'mustHaveMatch', label: 'Must-have match', description: 'Required JD skills coverage', color: 'text-red-600 dark:text-red-400', accent: 'accent-red-500' },
  { key: 'relevantExperience', label: 'Relevant experience', description: 'Experience level fit to role requirement', color: 'text-blue-600 dark:text-blue-400', accent: 'accent-blue-500' },
  { key: 'preferredSkills', label: 'Preferred skills', description: 'Nice-to-have skill coverage', color: 'text-sky-600 dark:text-sky-400', accent: 'accent-sky-500' },
  { key: 'achievementsImpact', label: 'Achievements / impact', description: 'Measured outcomes and accomplishments', color: 'text-emerald-600 dark:text-emerald-400', accent: 'accent-emerald-500' },
  { key: 'industryFit', label: 'Industry/domain fit', description: 'Domain and sector alignment', color: 'text-orange-600 dark:text-orange-400', accent: 'accent-orange-500' },
  { key: 'careerProgression', label: 'Career progression / stability', description: 'Growth trajectory and stability', color: 'text-teal-600 dark:text-teal-400', accent: 'accent-teal-500' },
]

const SORT_OPTIONS = [
  { value: 'overall_score', label: 'Overall Score' },
  { value: 'required_skill_score', label: 'Required Skills' },
  { value: 'skill_support_score', label: 'Evidence Quality' },
  { value: 'ats_score', label: 'ATS Score' },
  { value: 'achievements_score', label: 'Achievements Impact' },
  { value: 'industry_fit_score', label: 'Industry Fit' },
  { value: 'career_progression_score', label: 'Career Progression' },
  { value: 'matched_skills_count', label: 'Matched Skills Count' },
  { value: 'keyword_strong_count', label: 'Strong Keywords' },
  { value: 'experience_years', label: 'Experience Years' },
  { value: 'critical_gaps_asc', label: 'Fewest Critical Gaps' },
  { value: 'ats_issues_asc', label: 'Fewest ATS Issues' },
  { value: 'keyword_missing_asc', label: 'Fewest Missing Keywords' },
  { value: 'red_flags_asc', label: 'Fewest Red Flags' },
  { value: 'hiring_stage', label: 'Hiring Stage' },
]

const DEFAULT_SCREENING_POLICY = {
  shortlist_threshold: 63,
  review_threshold: 44,
  // policy_version: '2026-05-05.v1',
}

function normalizeSkillName(skill) {
  const cleaned = String(skill || '')
    .toLowerCase()
    .replace(/\([^)]*\)/g, ' ')
    .replace(/[^a-z0-9+#.]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  return SKILL_ALIASES[cleaned] || cleaned
}

function hasExactSkillMatch(candidateSkills = [], requiredSkill = '') {
  const required = normalizeSkillName(requiredSkill)
  if (!required) return false

  return candidateSkills.some((skill) => normalizeSkillName(skill) === required)
}

function getValidSkillWeight(weight) {
  return WEIGHT_POINTS[weight] != null ? weight : DEFAULT_SKILL_WEIGHT
}

function clampWeight(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 0
  const stepped = Math.round(numeric / WEIGHT_STEP) * WEIGHT_STEP
  return Math.max(0, Math.min(TOTAL_WEIGHT, stepped))
}

/**
 * Recompute the overall score using the recruiter's custom component weights.
 * Uses recruiter-selected scoring signals and dynamic normalization.
 */
function getExperienceFitScore(candidate) {
  if (candidate.experience_meets_requirement === true) return 100
  if (candidate.experience_meets_requirement === false) return 30
  const years = Number(candidate.estimated_experience_years ?? 0)
  if (!Number.isFinite(years) || years <= 0) return 50
  return Math.max(35, Math.min(90, Math.round(40 + years * 8)))
}

function computeComponentWeightedScore(candidate, weights, featureToggles) {
  const featureScores = {
    requiredSkills: candidate.required_skill_score ?? 0,
    preferredSkills: candidate.preferred_skill_score ?? Math.round((candidate.required_skill_score ?? 0) * 0.6),
    atsCompatibility: candidate.ats_score ?? 0,
    experienceFit: getExperienceFitScore(candidate),
    evidenceQuality: candidate.skill_support_score ?? 0,
    achievementsImpact: candidate.achievements_score ?? 0,
    industryFit: candidate.industry_fit_score ?? 0,
    careerProgression: candidate.career_progression_score ?? 0,
  }

  const activeEntries = Object.keys(featureScores).filter((key) => {
    const enabled = featureToggles?.[key] !== false
    const weight = Number(weights?.[key] ?? 0)
    return enabled && weight > 0
  })

  if (activeEntries.length === 0) return candidate.overall_score

  const totalActiveWeight = activeEntries.reduce((sum, key) => sum + Number(weights[key] || 0), 0)
  if (totalActiveWeight <= 0) return candidate.overall_score

  const score = activeEntries.reduce((sum, key) => {
    const normalizedWeight = Number(weights[key] || 0) / totalActiveWeight
    return sum + normalizedWeight * Number(featureScores[key] || 0)
  }, 0)

  return Math.max(0, Math.min(100, Math.round(score)))
}

function computeRoleParameterScore(candidate, weights) {
  const total = Object.values(weights || {}).reduce((a, b) => a + Number(b || 0), 0)
  if (total <= 0) return candidate.overall_score

  const normalized = {
    mustHaveMatch: Number(weights.mustHaveMatch || 0) / total,
    relevantExperience: Number(weights.relevantExperience || 0) / total,
    preferredSkills: Number(weights.preferredSkills || 0) / total,
    achievementsImpact: Number(weights.achievementsImpact || 0) / total,
    industryFit: Number(weights.industryFit || 0) / total,
    careerProgression: Number(weights.careerProgression || 0) / total,
  }

  const score =
    normalized.mustHaveMatch * (candidate.required_skill_score ?? 0) +
    normalized.relevantExperience * getExperienceFitScore(candidate) +
    normalized.preferredSkills * (candidate.preferred_skill_score ?? Math.round((candidate.required_skill_score ?? 0) * 0.6)) +
    normalized.achievementsImpact * (candidate.achievements_score ?? 0) +
    normalized.industryFit * (candidate.industry_fit_score ?? 0) +
    normalized.careerProgression * (candidate.career_progression_score ?? 0)

  return Math.max(0, Math.min(100, Math.round(score)))
}

/**
 * Returns an adjusted score based on recruiter-defined skill weights.
 * For each weighted skill:
 *   - Present in matched_skills → add bonus
 *   - Absent + High weight     → subtract penalty
 * Score is clamped to [0, 100].
 */
function computeSkillWeightedScore(baseScore, candidate, skillWeights) {
  if (!skillWeights || skillWeights.length === 0) return baseScore
  const candidateSkills = candidate.matched_skills || []
  let delta = 0
  for (const sw of skillWeights) {
    const weight = getValidSkillWeight(sw.weight)
    const hasSkill = hasExactSkillMatch(candidateSkills, sw.skill)
    if (hasSkill) {
      delta += WEIGHT_POINTS[weight]
    } else {
      delta -= WEIGHT_PENALTY[weight]
    }
  }
  return Math.max(0, Math.min(100, Math.round(baseScore + delta)))
}

function applyHRRules(candidates, rules, skillWeights, scoringWeights, scoringFeatures, roleParameterWeights, useSignalScoring, useRoleParameterScoring) {
  const mustHave = rules.mustHaveSkills
    .split(',')
    .map(s => s.trim().toLowerCase())
    .filter(Boolean)
  const minExp = rules.minExperience !== '' ? parseInt(rules.minExperience, 10) : null
  // Scoring only activates when the recruiter has actually changed weights from defaults or turned on signal model.
  // Role param toggle being ON with unchanged defaults = sliders visible but no re-bucketing.
  const roleParamIsDefault = JSON.stringify(roleParameterWeights) === JSON.stringify(DEFAULT_ROLE_PARAMETER_WEIGHTS)
  const scoringActive = useSignalScoring || (useRoleParameterScoring && !roleParamIsDefault) || skillWeights.length > 0

  return candidates.map(c => {
    const backendVerdict = c.backend_verdict || c.shortlist_verdict

    // Hard filter: must-have skills (always enforced regardless of scoring model)
    if (rules.enforceMustHaveSkills && mustHave.length > 0) {
      const candidateSkills = c.matched_skills || []
      const absent = mustHave.filter(req =>
        !hasExactSkillMatch(candidateSkills, req)
      )
      if (absent.length > 0) {
        return {
          ...c,
          backend_verdict: backendVerdict,
          filtered_verdict: 'Reject',
          shortlist_verdict: 'Reject',
          _weighted_score: c.overall_score,
          _rule_note: `Missing non-negotiable: ${absent.join(', ')}`,
        }
      }
    }

    // Hard filter: min experience (always enforced regardless of scoring model)
    if (rules.enforceMinExperience && minExp !== null && c.estimated_experience_years !== null && c.estimated_experience_years < minExp) {
      return {
        ...c,
        backend_verdict: backendVerdict,
        filtered_verdict: 'Reject',
        shortlist_verdict: 'Reject',
        _weighted_score: c.overall_score,
        _rule_note: `Exp. ${c.estimated_experience_years}y < ${minExp}y required`,
      }
    }

    // No custom scoring active → re-bucket using backend overall_score against thresholds.
    // We do NOT preserve the backend's shortlist_verdict because the backend may have rejected
    // a candidate via non-negotiable logic even when their score is above the threshold.
    // The frontend threshold (63/44) is always the primary bucketing rule.
    if (!scoringActive) {
      const baseVerdict =
        c.overall_score >= rules.shortlistThreshold
          ? 'Shortlist'
          : c.overall_score >= rules.reviewThreshold
            ? 'Review'
            : 'Reject'
      return {
        ...c,
        backend_verdict: backendVerdict,
        filtered_verdict: baseVerdict,
        shortlist_verdict: baseVerdict,
        _weighted_score: c.overall_score,
        _rule_note: null,
      }
    }

    // Custom scoring active — compute weighted/blended score and re-bucket
    const componentScore = computeComponentWeightedScore(c, scoringWeights, scoringFeatures)
    const roleParameterScore = computeRoleParameterScore(c, roleParameterWeights)

    const activeScores = []
    if (useSignalScoring) activeScores.push(componentScore)
    if (useRoleParameterScoring) activeScores.push(roleParameterScore)

    const blendedScore = activeScores.length > 0
      ? Math.round(activeScores.reduce((sum, v) => sum + v, 0) / activeScores.length)
      : c.overall_score

    const baseScore = computeSkillWeightedScore(blendedScore, c, skillWeights)

    const filteredVerdict =
      baseScore >= rules.shortlistThreshold
        ? 'Shortlist'
        : baseScore >= rules.reviewThreshold
          ? 'Review'
          : 'Reject'

    return {
      ...c,
      backend_verdict: backendVerdict,
      filtered_verdict: filteredVerdict,
      shortlist_verdict: filteredVerdict,
      _weighted_score: baseScore,
      _component_score: componentScore,
      _role_parameter_score: roleParameterScore,
      _rule_note: null,
    }
  })
}

function getSortValue(candidate, sortBy) {
  if (sortBy === 'overall_score') return candidate.overall_score ?? 0
  if (sortBy === 'weighted_score') return candidate._weighted_score ?? candidate.overall_score ?? 0
  if (sortBy === 'matched_skills_count') return candidate.matched_skills?.length ?? 0
  if (sortBy === 'critical_gaps_asc') return candidate.critical_missing_skills?.length ?? 0
  if (sortBy === 'ats_issues_asc') return candidate.ats_issues_count ?? 0
  if (sortBy === 'keyword_missing_asc') return candidate.keyword_missing_count ?? 0
  if (sortBy === 'red_flags_asc') return candidate.red_flags?.length ?? 0
  if (sortBy === 'experience_years') return candidate.estimated_experience_years ?? -1
  if (sortBy === 'hiring_stage') return HIRING_STAGE_OPTIONS.indexOf(getCandidateStage(candidate))
  return candidate[sortBy] ?? 0
}

function sortCandidates(candidates, sortBy) {
  const ascendingSorts = new Set([
    'critical_gaps_asc',
    'ats_issues_asc',
    'keyword_missing_asc',
    'red_flags_asc',
    'hiring_stage',
  ])

  return [...candidates].sort((a, b) => {
    const aValue = getSortValue(a, sortBy)
    const bValue = getSortValue(b, sortBy)
    if (ascendingSorts.has(sortBy)) return aValue - bValue
    return bValue - aValue
  })
}

function exportCandidatesCSV(candidates, jdTitle) {
  const headers = [
    'Rank', 'Filename', 'Bucket', 'Hiring Stage', 'Original Overall Score', 'Adjusted Screening Score', 'ATS Score',
    'Required Skills', 'Evidence Score', 'Matched Skills Count',
    'Critical Gaps', 'Experience (yrs)', 'Exp Meets Req',
    'Strong Keywords', 'ATS Issues', 'Rule Note',
  ]
  const rows = candidates.map((c, i) => [
    i + 1,
    `"${(c.filename || '').replace(/"/g, '""')}"`,
    c.shortlist_verdict,
    getCandidateStage(c),
    c.overall_score,
    c._weighted_score ?? c.overall_score,
    c.ats_score,
    c.required_skills_count > 0 ? `${c.required_skills_matched_count}/${c.required_skills_count} (${c.required_skill_score})` : 'N/A',
    c.skill_support_score,
    c.matched_skills.length,
    c.critical_missing_skills.length,
    c.estimated_experience_years ?? '',
    c.experience_meets_requirement === true ? 'Yes' : c.experience_meets_requirement === false ? 'No' : '',
    c.keyword_strong_count,
    c.ats_issues_count,
    `"${(c._rule_note || '').replace(/"/g, '""')}"`,
  ])
  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `screening-${(jdTitle || 'results').replace(/[^a-z0-9]/gi, '-').toLowerCase().slice(0, 40)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function RecruiterDashboard({ batchResult, onReset }) {
  const [activeTab, setActiveTab] = useState('all')
  const [sortBy, setSortBy] = useState('overall_score')
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const [candidateStatuses, setCandidateStatuses] = useState({})
  const [showRulesPanel, setShowRulesPanel] = useState(false)
  const [hrRules, setHrRules] = useState({
    shortlistThreshold: DEFAULT_SCREENING_POLICY.shortlist_threshold,
    reviewThreshold: DEFAULT_SCREENING_POLICY.review_threshold,
    mustHaveSkills: '',
    minExperience: '',
    enforceMustHaveSkills: true,
    enforceMinExperience: true,
  })
  const [skillWeights, setSkillWeights] = useState([])  // [{skill: 'Python', weight: 'High'}]
  const [swSkillInput, setSwSkillInput] = useState('')
  const [swWeightInput, setSwWeightInput] = useState(DEFAULT_SKILL_WEIGHT)
  const [scoringWeights, setScoringWeights] = useState({ ...DEFAULT_SCORING_WEIGHTS })
  const [scoringFeatures, setScoringFeatures] = useState({ ...DEFAULT_SCORING_FEATURES })
  const [roleParameterWeights, setRoleParameterWeights] = useState({ ...DEFAULT_ROLE_PARAMETER_WEIGHTS })
  const [useSignalScoring, setUseSignalScoring] = useState(false)
  const [useRoleParameterScoring, setUseRoleParameterScoring] = useState(true)
  const [showScoringWeights, setShowScoringWeights] = useState(true)
  const [statusSyncError, setStatusSyncError] = useState('')

  useEffect(() => {
    if (!batchResult?.all_candidates?.length) {
      return
    }

    let cancelled = false

    async function loadStatuses() {
      const ids = batchResult.all_candidates.map((candidate) => getCandidateId(candidate))
      let entries = []
      try {
        const data = await getCandidateStatuses(ids)
        setStatusSyncError('')
        entries = ids.map((candidateId, idx) => {
          const fallback = batchResult.all_candidates[idx]?.status || 'New'
          const statusEntry = data?.statuses?.[candidateId]
          return [candidateId, statusEntry?.status || fallback]
        })
      } catch (error) {
        console.error('Failed to load candidate statuses:', error)
        setStatusSyncError('Could not load saved candidate stages. Showing default stage values for now.')
        entries = batchResult.all_candidates.map((candidate) => [
          getCandidateId(candidate),
          candidate.status || 'New',
        ])
      }

      if (!cancelled) {
        setCandidateStatuses(Object.fromEntries(entries))
      }
    }

    loadStatuses()

    return () => {
      cancelled = true
    }
  }, [batchResult])

  useEffect(() => {
    const policy = batchResult?.policy || DEFAULT_SCREENING_POLICY
    setHrRules((prev) => ({
      ...prev,
      shortlistThreshold: policy.shortlist_threshold,
      reviewThreshold: policy.review_threshold,
      enforceMustHaveSkills: prev.enforceMustHaveSkills ?? true,
      enforceMinExperience: prev.enforceMinExperience ?? true,
    }))
  }, [batchResult])

  if (!batchResult) return null

  const policy = batchResult.policy || DEFAULT_SCREENING_POLICY

  const { jd_title, total_candidates, all_candidates } = batchResult
  const skippedFiles = batchResult.skipped_files || []
  const failedFiles = batchResult.failed_files || []
  const activeScoringWeightKeys = SCORING_WEIGHT_META
    .filter((meta) => scoringFeatures[meta.key] !== false)
    .map((meta) => meta.key)
  const roleParameterWeightKeys = ROLE_PARAMETER_META.map((meta) => meta.key)
  const scoringWeightTotal = Object.values(scoringWeights).reduce((sum, value) => sum + Number(value || 0), 0)
  const activeScoringWeightTotal = activeScoringWeightKeys.reduce((sum, key) => sum + Number(scoringWeights[key] || 0), 0)
  const roleParameterWeightTotal = roleParameterWeightKeys.reduce((sum, key) => sum + Number(roleParameterWeights[key] || 0), 0)
  const signalScoringReady = activeScoringWeightKeys.length > 0 && activeScoringWeightTotal === TOTAL_WEIGHT
  const roleParameterScoringReady = roleParameterWeightTotal === TOTAL_WEIGHT
  const applySignalScoring = useSignalScoring && signalScoringReady
  const applyRoleParameterScoring = useRoleParameterScoring && roleParameterScoringReady

  const candidatesWithStatus = all_candidates.map((candidate) => {
    const candidateId = getCandidateId(candidate)
    return {
      ...candidate,
      status: candidateStatuses[candidateId] || candidate.status || 'New',
    }
  })

  const ruledCandidates = applyHRRules(
    candidatesWithStatus,
    hrRules,
    skillWeights,
    scoringWeights,
    scoringFeatures,
    roleParameterWeights,
    applySignalScoring,
    applyRoleParameterScoring,
  )
  const effectiveCandidates = ruledCandidates
  const effectiveShortlisted = effectiveCandidates.filter(c => c.shortlist_verdict === 'Shortlist')
  const effectiveReview = effectiveCandidates.filter(c => c.shortlist_verdict === 'Review')
  const effectiveRejected = effectiveCandidates.filter(c => c.shortlist_verdict === 'Reject')
  const scoringWeightsChanged = JSON.stringify(scoringWeights) !== JSON.stringify(DEFAULT_SCORING_WEIGHTS)
  const scoringFeaturesChanged = JSON.stringify(scoringFeatures) !== JSON.stringify(DEFAULT_SCORING_FEATURES)
  const roleParameterWeightsChanged = JSON.stringify(roleParameterWeights) !== JSON.stringify(DEFAULT_ROLE_PARAMETER_WEIGHTS)
  const rulesModified =
    hrRules.shortlistThreshold !== policy.shortlist_threshold ||
    hrRules.reviewThreshold !== policy.review_threshold ||
    (hrRules.enforceMustHaveSkills && hrRules.mustHaveSkills.trim() !== '') ||
    (hrRules.enforceMinExperience && hrRules.minExperience !== '') ||
    hrRules.enforceMustHaveSkills !== true ||
    hrRules.enforceMinExperience !== true ||
    skillWeights.length > 0 ||
    useSignalScoring !== false ||
    useRoleParameterScoring !== true ||
    scoringWeightsChanged ||
    scoringFeaturesChanged ||
    roleParameterWeightsChanged
  const weightsActive =
    skillWeights.length > 0 ||
    applySignalScoring ||
    (applyRoleParameterScoring && roleParameterWeightsChanged) ||
    (applySignalScoring && (scoringWeightsChanged || scoringFeaturesChanged))

  const tabCandidates = {
    all: effectiveCandidates,
    Shortlist: effectiveShortlisted,
    Review: effectiveReview,
    Reject: effectiveRejected,
  }

  const sorted = sortCandidates(tabCandidates[activeTab] || [], sortBy)
  const tableCandidates = sortCandidates(effectiveCandidates, sortBy)
  const selectedCandidateForPanel = selectedCandidate
    ? effectiveCandidates.find((candidate) => getCandidateId(candidate) === getCandidateId(selectedCandidate)) || selectedCandidate
    : null
  const handleScoringFeatureToggle = (key, enabled) => {
    setScoringFeatures((prev) => ({ ...prev, [key]: enabled }))
  }

  const handleScoringWeightChange = (key, value) => {
    setScoringWeights((prev) => ({ ...prev, [key]: clampWeight(value) }))
  }

  const handleRoleParameterWeightChange = (key, value) => {
    setRoleParameterWeights((prev) => ({ ...prev, [key]: clampWeight(value) }))
  }

  const handleCandidateStatusChange = async (candidate, newStatus, candidateId = getCandidateId(candidate)) => {
    try {
      await updateCandidateStatus(candidateId, newStatus)
      setStatusSyncError('')
      setCandidateStatuses((prev) => ({ ...prev, [candidateId]: newStatus }))
      setSelectedCandidate((prev) => (
        prev && getCandidateId(prev) === candidateId
          ? { ...prev, status: newStatus }
          : prev
      ))
    } catch (error) {
      console.error('Failed to update status:', error)
      setStatusSyncError('Could not save status update. Please retry.')
    }
  }

  return (
    <div className="space-y-6">

      {/* Detail panel (slide-in) */}
      {selectedCandidateForPanel && (
        <CandidateDetailPanel
          candidate={selectedCandidateForPanel}
          policy={policy}
          onClose={() => setSelectedCandidate(null)}
        />
      )}

      {/* Header */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        {/* Skipped files warning */}
        {skippedFiles.length > 0 && (
          <div className="rounded-2xl border border-yellow-300 bg-yellow-50 dark:bg-yellow-950 p-4 text-yellow-800 dark:text-yellow-200 mb-4">
            <p className="font-semibold">Some uploaded files were skipped</p>
            <p className="mt-1 text-sm">The following files were strongly classified as non-resume inputs and were ignored:</p>
            <ul className="mt-2 list-disc list-inside text-sm">
              {skippedFiles.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>
        )}

        {failedFiles.length > 0 && (
          <div className="rounded-2xl border border-red-300 bg-red-50 dark:bg-red-950 p-4 text-red-800 dark:text-red-200 mb-4">
            <p className="font-semibold">Some files could not be analyzed</p>
            <p className="mt-1 text-sm">The following files failed during analysis. These candidates were not included in ranking.</p>
            <ul className="mt-2 list-disc list-inside text-sm">
              {failedFiles.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>
        )}

        {statusSyncError && (
          <div className="rounded-2xl border border-orange-300 bg-orange-50 dark:bg-orange-950 p-4 text-orange-800 dark:text-orange-200 mb-4">
            <p className="font-semibold">Status sync warning</p>
            <p className="mt-1 text-sm">{statusSyncError}</p>
          </div>
        )}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400 mb-1">
              Recruiter Screening Results
            </p>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white line-clamp-2">{jd_title}</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
              {total_candidates} candidate{total_candidates !== 1 ? 's' : ''} screened
            </p>
            <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
              Policy {policy.policy_version} · Shortlist ≥{policy.shortlist_threshold} · Review ≥{policy.review_threshold}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => exportCandidatesCSV(effectiveCandidates, jd_title)}
              className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition"
            >
              ↓ Export CSV
            </button>
            <button
              type="button"
              onClick={() => setShowRulesPanel((v) => !v)}
              className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${
                rulesModified
                  ? 'border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700'
              }`}
            >
              ⚙ {rulesModified ? 'Controls Active' : 'Controls'}
            </button>
            <button
              type="button"
              onClick={onReset}
              className="rounded-xl border-2 border-red-600 bg-red-50 dark:bg-red-950 px-4 py-2 text-sm font-bold text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900 transition flex items-center gap-2"
              title="Exit to new screening"
            >
              <span className="text-lg">⎋</span> New Screening
            </button>
          </div>
        </div>

        {/* Bucket summary */}
        <div className="mt-5 grid grid-cols-3 gap-3">
          {[
            { label: 'Shortlist', count: effectiveShortlisted.length, color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-950', border: 'border border-green-200 dark:border-green-800', sub: `Score ≥${hrRules.shortlistThreshold}` },
            { label: 'Review',    count: effectiveReview.length,      color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-50 dark:bg-yellow-950', border: 'border border-yellow-200 dark:border-yellow-800', sub: `Score ${hrRules.reviewThreshold}–${hrRules.shortlistThreshold - 1}` },
            { label: 'Reject',    count: effectiveRejected.length,    color: 'text-red-500 dark:text-red-400',    bg: 'bg-red-50 dark:bg-red-950',    border: 'border border-red-200 dark:border-red-800',    sub: `Score <${hrRules.reviewThreshold}` },
          ].map((b) => (
            <button
              key={b.label}
              type="button"
              onClick={() => setActiveTab(b.label)}
              className={`rounded-2xl ${b.bg} ${b.border} p-4 text-left transition hover:opacity-80`}
            >
              <p className={`text-2xl font-bold ${b.color}`}>{b.count}</p>
              <p className="mt-1 text-xs font-bold text-gray-800 dark:text-slate-200">{b.label}</p>
              <p className={`text-xs ${b.color}`}>{b.sub}</p>
            </button>
          ))}
        </div>
      </div>

      {/* HR Filters panel */}
      {showRulesPanel && (
        <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-slate-50 dark:bg-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Screening Controls</h3>
            {rulesModified && (
              <button
                type="button"
                onClick={() => {
                  setHrRules({ shortlistThreshold: policy.shortlist_threshold, reviewThreshold: policy.review_threshold, mustHaveSkills: '', minExperience: '', enforceMustHaveSkills: true, enforceMinExperience: true })
                  setScoringWeights({ ...DEFAULT_SCORING_WEIGHTS })
                  setScoringFeatures({ ...DEFAULT_SCORING_FEATURES })
                  setRoleParameterWeights({ ...DEFAULT_ROLE_PARAMETER_WEIGHTS })
                  setUseSignalScoring(false)
                  setUseRoleParameterScoring(true)
                  setSkillWeights([])
                  setSortBy('overall_score')
                }}
                className="text-xs text-slate-500 dark:text-slate-400 underline hover:no-underline"
              >
                Reset
              </button>
            )}
          </div>

          {/* Scoring weights — interactive sliders */}
          <div className="rounded-xl bg-white dark:bg-slate-900 border border-blue-200 dark:border-slate-600 p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold text-slate-700 dark:text-slate-200"> Scoring Component Weights</p>
              <div className="flex items-center gap-2">
                {(scoringWeightsChanged || scoringFeaturesChanged) && (
                  <button
                    type="button"
                    onClick={() => {
                      setScoringWeights({ ...DEFAULT_SCORING_WEIGHTS })
                      setScoringFeatures({ ...DEFAULT_SCORING_FEATURES })
                    }}
                    className="text-xs text-slate-500 dark:text-slate-400 underline hover:no-underline"
                  >
                    Reset
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowScoringWeights(v => !v)}
                  className="text-xs text-slate-600 dark:text-slate-300 font-semibold"
                >
                  {showScoringWeights ? '▲ Hide' : '▼ Adjust'}
                </button>
              </div>
            </div>

            {/* Always-visible compact summary */}
            <div className="grid grid-cols-3 gap-1 text-xs mb-1">
              {SCORING_WEIGHT_META.map(m => (
                <div key={m.key} className="flex items-center gap-1">
                  <span className={`font-bold ${m.color}`}>{scoringWeights[m.key]}%</span>
                  <span className="text-slate-600 dark:text-slate-400 truncate">{m.label}</span>
                  {scoringFeatures[m.key] === false && (
                    <span className="text-[10px] font-semibold text-red-500 dark:text-red-400">OFF</span>
                  )}
                </div>
              ))}
            </div>

            {/* Expandable sliders */}
            {showScoringWeights && (
              <div className="mt-3 space-y-2.5 border-t border-gray-200 dark:border-slate-700 pt-3">
                <label className="inline-flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
                  <input
                    type="checkbox"
                    checked={useSignalScoring}
                    onChange={(e) => setUseSignalScoring(e.target.checked)}
                    className="accent-blue-500"
                  />
                  Use Signal-Based Scoring (new model)
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400 italic mb-2">
                  Tick/untick any scoring signal and adjust weights yourself. This model applies only when active allocation is exactly 100%.
                </p>
                {SCORING_WEIGHT_META.map(m => (
                    <div key={m.key} className="space-y-0.5">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <label className="inline-flex items-center gap-2 cursor-pointer">
	                            <input
	                              type="checkbox"
	                              checked={scoringFeatures[m.key] !== false}
	                              onChange={(e) => handleScoringFeatureToggle(m.key, e.target.checked)}
	                              disabled={!useSignalScoring}
	                              className="accent-blue-500"
	                            />
                            <span className={`text-xs font-semibold ${m.color}`}>{m.label}</span>
                          </label>
                          <p className="text-xs text-gray-500 dark:text-slate-400">{m.description}</p>
                        </div>
                        <span className={`text-sm font-bold w-14 text-right ${m.color}`}>
                          {scoringFeatures[m.key] !== false ? `${scoringWeights[m.key]}%` : 'Off'}
                        </span>
	                      </div>
	                      <input
	                        type="range" min="0" max="100" step="5"
	                        value={scoringWeights[m.key]}
	                        onChange={e => handleScoringWeightChange(m.key, Number(e.target.value))}
	                        disabled={!useSignalScoring || scoringFeatures[m.key] === false}
	                        className={`w-full ${m.accent} ${(!useSignalScoring || scoringFeatures[m.key] === false) ? 'opacity-40 cursor-not-allowed' : ''}`}
	                      />
                    </div>
	                  ))}
	                {/* Total indicator */}
		                <div className={`mt-2 rounded-lg px-3 py-2 text-xs font-semibold text-center border ${
		                  signalScoringReady
		                    ? 'bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700'
		                    : 'bg-yellow-50 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-700'
		                }`}>
		                  Total configured: {scoringWeightTotal}% · Active allocation: {activeScoringWeightTotal}% · {activeScoringWeightKeys.length} feature{activeScoringWeightKeys.length !== 1 ? 's' : ''} active
		                  {useSignalScoring && !signalScoringReady && (
		                    <span className="block mt-1">Complete active allocation to exactly 100% to apply signal-based scoring.</span>
		                  )}
		                </div>
              </div>
            )}

            <p className="text-xs text-slate-500 dark:text-slate-400 italic">
              {/* "How well does this candidate match the JD?" — not comparing candidates to each other */}
            </p>
          </div>

          {/* Original JD parameter weights (kept separately) */}
          <div className="rounded-xl bg-white dark:bg-slate-900 border border-blue-200 dark:border-slate-600 p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold text-slate-700 dark:text-slate-200">Role Parameter Weights (Original)</p>
              {roleParameterWeightsChanged && (
                <button
                  type="button"
                  onClick={() => setRoleParameterWeights({ ...DEFAULT_ROLE_PARAMETER_WEIGHTS })}
                  className="text-xs text-slate-500 dark:text-slate-400 underline hover:no-underline"
                >
                  Reset
                </button>
              )}
            </div>

            <div className="space-y-2.5 border-t border-gray-200 dark:border-slate-700 pt-3">
              <label className="inline-flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={useRoleParameterScoring}
                  onChange={(e) => setUseRoleParameterScoring(e.target.checked)}
                  className="accent-blue-500"
                />
                Use Role Parameter Scoring (40/20/15/10/10/5)
              </label>

              <p className="text-xs text-slate-500 dark:text-slate-400 italic mb-2">
                {/* This is the original recruiter model you asked to keep. You can run this separately or together with the signal-based model. */}
              </p>

              {ROLE_PARAMETER_META.map((m) => (
                <div key={m.key} className="space-y-0.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={`text-xs font-semibold ${m.color}`}>{m.label}</span>
                      <p className="text-xs text-gray-500 dark:text-slate-400">{m.description}</p>
                    </div>
                    <span className={`text-sm font-bold w-14 text-right ${m.color}`}>{roleParameterWeights[m.key]}%</span>
                  </div>
	                  <input
	                    type="range"
	                    min="0"
	                    max="100"
	                    step="5"
	                    value={roleParameterWeights[m.key]}
	                    onChange={e => handleRoleParameterWeightChange(m.key, Number(e.target.value))}
	                    disabled={!useRoleParameterScoring}
	                    className={`w-full ${m.accent} ${!useRoleParameterScoring ? 'opacity-40 cursor-not-allowed' : ''}`}
	                  />
	                </div>
	              ))}

		              <div className={`mt-2 rounded-lg px-3 py-2 text-xs font-semibold text-center border ${
		                roleParameterScoringReady
		                  ? 'bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700'
		                  : 'bg-yellow-50 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-700'
		              }`}>
		                Role parameter allocation: {roleParameterWeightTotal}%
		                {useRoleParameterScoring && !roleParameterScoringReady && (
		                  <span className="block mt-1">Complete role parameter allocation to exactly 100% to apply this model.</span>
		                )}
		              </div>

		              <div className="mt-2 rounded-lg px-3 py-2 text-xs font-semibold text-center bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700">
	                Blend behavior: {applySignalScoring && applyRoleParameterScoring
	                  ? 'both enabled → final score is the average of both models'
	                  : applySignalScoring
	                    ? 'signal-based model only'
	                    : applyRoleParameterScoring
	                      ? 'role-parameter model only'
	                      : 'no valid scoring model active → falls back to backend overall score'}
	              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-800 dark:text-slate-200">Shortlist if score ≥</label>
              <div className="flex items-center gap-3">
                <input type="range" min="50" max="95" step="5" value={hrRules.shortlistThreshold}
                  onChange={e => setHrRules(r => ({ ...r, shortlistThreshold: Number(e.target.value) }))}
                  className="flex-1 accent-blue-500" />
                <span className="w-8 text-right text-sm font-bold text-blue-700 dark:text-blue-300">{hrRules.shortlistThreshold}</span>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-800 dark:text-slate-200">Review if score ≥</label>
              <div className="flex items-center gap-3">
                <input type="range" min="20" max="70" step="5" value={hrRules.reviewThreshold}
                  onChange={e => setHrRules(r => ({ ...r, reviewThreshold: Math.min(Number(e.target.value), hrRules.shortlistThreshold - 5) }))}
                  className="flex-1 accent-blue-500" />
                <span className="w-8 text-right text-sm font-bold text-blue-700 dark:text-blue-300">{hrRules.reviewThreshold}</span>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-800 dark:text-slate-200 inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={hrRules.enforceMustHaveSkills}
                  onChange={(e) => setHrRules(r => ({ ...r, enforceMustHaveSkills: e.target.checked }))}
                  className="accent-blue-500"
                />
                Must-have skills (comma-separated)
              </label>
              <input type="text" value={hrRules.mustHaveSkills}
                onChange={e => setHrRules(r => ({ ...r, mustHaveSkills: e.target.value }))}
                placeholder="e.g. Python, SQL, AWS"
                disabled={!hrRules.enforceMustHaveSkills}
                className="w-full rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 dark:text-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-800 dark:text-slate-200 inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={hrRules.enforceMinExperience}
                  onChange={(e) => setHrRules(r => ({ ...r, enforceMinExperience: e.target.checked }))}
                  className="accent-blue-500"
                />
                Min. experience (years)
              </label>
              <input type="number" min="0" max="30" value={hrRules.minExperience}
                onChange={e => setHrRules(r => ({ ...r, minExperience: e.target.value }))}
                placeholder="e.g. 3"
                disabled={!hrRules.enforceMinExperience}
                className="w-full rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 dark:text-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>

          {rulesModified && (
            <p className="text-xs text-slate-600 dark:text-slate-300">
              <span className="font-semibold text-green-600">{effectiveShortlisted.length} Shortlist</span>
              {' · '}
              <span className="font-semibold text-yellow-600">{effectiveReview.length} Review</span>
              {' · '}
              <span className="font-semibold text-red-500">{effectiveRejected.length} Reject</span>
            </p>
          )}

          {/* ── Skill Weightage ── */}
          <div className="mt-2 border-t border-gray-200 dark:border-slate-700 pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Skill Weightage</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Prioritize candidates with specific skills
              </p>
            </div>
            {skillWeights.length > 0 && (
              <button type="button" onClick={() => setSkillWeights([])}
                className="text-xs text-slate-500 dark:text-slate-400 underline hover:no-underline">
                Clear all
              </button>
            )}
          </div>

          {/* How weights work — compact legend */}
          <div className="flex flex-wrap gap-2 text-xs">
            {[['High', 'bg-orange-50 dark:bg-orange-950 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-800', 'Critical'],
              ['Medium', 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800', 'Important'],
              ['Low', 'bg-gray-50 dark:bg-slate-700 text-gray-600 dark:text-slate-300 border-gray-200 dark:border-slate-600', 'Nice to have'],
            ].map(([label, cls, tip]) => (
              <span key={label} className={`rounded-full border px-2.5 py-1 font-medium ${cls}`} title={tip}>
                {label} — {tip}
              </span>
            ))}
          </div>

          {/* Add skill row */}
          <div className="flex gap-2">
            <input
              type="text"
              value={swSkillInput}
              onChange={e => setSwSkillInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && swSkillInput.trim()) {
                  const skill = swSkillInput.trim()
                  if (!skillWeights.some(sw => normalizeSkillName(sw.skill) === normalizeSkillName(skill))) {
                    setSkillWeights(prev => [...prev, { skill, weight: getValidSkillWeight(swWeightInput) }])
                  }
                  setSwSkillInput('')
                }
              }}
              placeholder="Skill name (e.g. Python)"
              className="flex-1 rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 dark:text-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400"
            />
            <WeightDropdown value={swWeightInput} onChange={setSwWeightInput} />
            <button
              type="button"
              onClick={() => {
                const skill = swSkillInput.trim()
                if (!skill) return
                if (!skillWeights.some(sw => normalizeSkillName(sw.skill) === normalizeSkillName(skill))) {
                  setSkillWeights(prev => [...prev, { skill, weight: getValidSkillWeight(swWeightInput) }])
                }
                setSwSkillInput('')
              }}
              className="rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 text-sm font-semibold transition"
            >
              + Add
            </button>
          </div>

          {/* Skill weight chips */}
          {skillWeights.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {skillWeights.map((sw) => {
                const chipCls =
                  sw.weight === 'High'   ? 'bg-orange-50 dark:bg-orange-950 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700'
                  : sw.weight === 'Medium' ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700'
                  : 'bg-gray-50 dark:bg-slate-700 text-gray-600 dark:text-slate-300 border-gray-300 dark:border-slate-600'
                return (
                  <span key={sw.skill} className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${chipCls}`}>
                    {sw.skill}
                    <span className="opacity-60 font-normal">({sw.weight})</span>
                    <button
                      type="button"
                      onClick={() => setSkillWeights(prev => prev.filter(x => x.skill !== sw.skill))}
                      className="ml-0.5 opacity-50 hover:opacity-100 transition text-xs leading-none"
                      title="Remove"
                    >
                      ✕
                    </button>
                  </span>
                )
              })}
            </div>
          )}
          </div>
        </div>
      )}

      {/* Tabs + sort */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 rounded-2xl bg-gray-50 dark:bg-slate-800 p-1">
          {BUCKET_TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setActiveTab(t.key)}
              className={`rounded-xl px-4 py-1.5 text-sm font-semibold transition ${
                activeTab === t.key
                  ? 'bg-purple-600 dark:bg-black text-white shadow'
                  : 'text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              {t.label}
              {t.key !== 'all' && (
                <span className="ml-1.5 text-xs opacity-70">
                  ({tabCandidates[t.key]?.length ?? 0})
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-400">
          <span>Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 dark:text-white px-3 py-1.5 text-sm focus:outline-none"
          >
            {(weightsActive || sortBy === 'weighted_score') && <option value="weighted_score">Weighted Score ★</option>}
            {SORT_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Candidate grid */}
      {sorted.length === 0 ? (
        <div className="rounded-2xl bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 p-8 text-center text-sm text-gray-500 dark:text-slate-400">
          No candidates in this category.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {sorted.map((c, i) => (
            <CandidateCard
              key={c.candidate_id || c.candidate_index}
              candidate={c}
              rank={i + 1}
              onViewDetails={setSelectedCandidate}
              onStatusChange={handleCandidateStatusChange}
            />
          ))}
        </div>
      )}

      {/* Comparison table */}
      <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
        <div className="px-4 pt-4 pb-2 border-b border-gray-100 dark:border-slate-800">
          <p className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">Full Comparison Table</p>
          <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">
            Click any row for details
            {(rulesModified || weightsActive) && <span className="ml-1 text-purple-600 dark:text-purple-400 font-semibold">· Controls applied</span>}
          </p>
        </div>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-slate-400">#</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-slate-400">Candidate</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400" title="Original backend overall fit score">Overall ↕</th>
              {weightsActive && <th className="px-4 py-3 text-center text-xs font-semibold text-orange-500 dark:text-orange-400" title="Score adjusted for your custom skill weights">Wtd. Score ★</th>}
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400" title="ATS formatting quality">ATS</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400" title="% of required JD skills present">Req. Skills</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400" title="Evidence quality behind claims">Evidence</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400">Matched</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400">Critical Gaps</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400">Exp (yrs)</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400">Hiring Stage</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 dark:text-slate-400">Bucket</th>
              {rulesModified && <th className="px-4 py-3 text-left text-xs font-semibold text-purple-500 dark:text-purple-400">Rule Note</th>}
            </tr>
          </thead>
          <tbody>
            {tableCandidates.map((c, i) => {
              const originalScore = c.overall_score ?? 0
              const adjustedScore = c._weighted_score ?? originalScore
              const bucketClass =
                c.shortlist_verdict === 'Shortlist'
                  ? 'text-green-700 dark:text-green-400'
                  : c.shortlist_verdict === 'Review'
                  ? 'text-yellow-700 dark:text-yellow-400'
                  : 'text-red-600 dark:text-red-400'
              const scoreColor =
                originalScore >= 70 ? 'text-green-600 dark:text-green-400 font-bold'
                : originalScore >= 50 ? 'text-yellow-600 dark:text-yellow-400 font-bold'
                : 'text-red-500 dark:text-red-400 font-bold'

              return (
                <tr
                  key={c.candidate_id || c.candidate_index}
                  onClick={() => setSelectedCandidate(c)}
                  className={`border-b border-gray-50 dark:border-slate-800 hover:bg-blue-50 dark:hover:bg-blue-950 cursor-pointer transition ${
                    c._rule_note ? 'bg-purple-50/40 dark:bg-purple-950/20' : ''
                  }`}
                >
                  <td className="px-4 py-3 text-gray-500 dark:text-slate-400">{i + 1}</td>
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white max-w-[180px] truncate">{c.filename}</td>
                  <td className={`px-4 py-3 text-center ${scoreColor}`}>{originalScore}</td>
                  {weightsActive && (
                    <td className={`px-4 py-3 text-center font-bold ${
                      adjustedScore >= 70 ? 'text-orange-600 dark:text-orange-400'
                      : adjustedScore >= 50 ? 'text-yellow-600 dark:text-yellow-400'
                      : 'text-red-500 dark:text-red-400'
                    }`}>
                      {adjustedScore}
                      {c._weighted_score != null && c._weighted_score !== originalScore && (
                        <span className={`ml-1 text-xs ${
                          c._weighted_score > originalScore ? 'text-green-500' : 'text-red-400'
                        }`}>
                          ({c._weighted_score > originalScore ? '+' : ''}{c._weighted_score - originalScore})
                        </span>
                      )}
                    </td>
                  )}
                  <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-300">{c.ats_score}</td>
                  <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-300">
                    {c.required_skills_count > 0 ? (
                      <span className="text-sm font-semibold">{c.required_skills_matched_count}/{c.required_skills_count}</span>
                    ) : (
                      <span className="text-xs text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-300">{c.skill_support_score}</td>
                  <td className="px-4 py-3 text-center text-green-600 dark:text-green-400">{c.matched_skills.length}</td>
                  <td className="px-4 py-3 text-center text-red-500 dark:text-red-400">{c.critical_missing_skills.length}</td>
                  <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-300">
                    {c.estimated_experience_years ?? '–'}
                    {c.experience_meets_requirement === true && <span className="ml-1 text-green-500">✓</span>}
                    {c.experience_meets_requirement === false && <span className="ml-1 text-red-400">✗</span>}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-300">{getCandidateStage(c)}</td>
                  <td className={`px-4 py-3 text-center font-semibold ${bucketClass}`}>{c.shortlist_verdict}</td>
                  {rulesModified && (
                    <td className="px-4 py-3 text-xs text-purple-600 dark:text-purple-400 max-w-[160px]">
                      {c._rule_note || ''}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
