const scoreItems = [
  {
    key: 'required_skill_score',
    label: 'Required Skills Coverage',
    helper: 'Percentage of must-have skills listed in the job description that appear in the resume. Low score here is a strong rejection signal — these are non-negotiable requirements.',
  },
  {
    key: 'preferred_skill_score',
    label: 'Preferred Skills Coverage',
    helper: 'Percentage of nice-to-have / preferred skills from the JD present in the resume. Improves overall fit but is not a dealbreaker on its own.',
  },
  {
    key: 'general_skill_score',
    label: 'General Skills Overlap',
    helper: 'Breadth of skill term overlap between the resume and the full JD text. Captures domain-level alignment beyond just explicit skill bullets.',
  },
  {
    key: 'weighted_skill_score',
    label: 'Weighted Skill Score',
    helper: 'Composite skill score that gives more weight to required skills than preferred or general skills. Higher = better alignment with what the role actually demands.',
  },
  {
    key: 'semantic_score',
    label: 'Semantic Similarity',
    helper: 'How closely the overall language and context of the resume matches the job description, beyond keyword matching. Captures domain familiarity and relevant experience framing.',
  },
  {
    key: 'section_evidence_score',
    label: 'Section Evidence Score',
    helper: 'Checks that relevant skills and experience appear in the right resume sections (e.g., skills in Skills, achievements in Experience). A well-structured resume scores higher.',
  },
  {
    key: 'skill_support_score',
    label: 'Evidence Quality',
    helper: 'Are claimed skills backed by concrete proof? Measures action verbs, project outcomes, measurable results. A resume that just lists skills without context scores lower.',
  },
  {
    key: 'critical_missing_penalty',
    label: 'Critical Gap Penalty',
    helper: 'Score penalty applied for each must-have JD skill that is absent from the resume. Higher penalty = more critical gaps. This directly reduces the overall score.',
  },
]

function getScoreTone(key, value) {
  const safeValue = Math.max(0, Math.min(Number(value) || 0, 100))

  if (key === 'critical_missing_penalty') {
    if (safeValue <= 10) {
      return {
        chip: 'bg-green-100 text-green-700',
        fill: 'bg-green-600',
        track: 'bg-green-100',
        label: 'Low Penalty',
      }
    }

    if (safeValue <= 25) {
      return {
        chip: 'bg-yellow-100 text-yellow-700',
        fill: 'bg-yellow-500',
        track: 'bg-yellow-100',
        label: 'Medium Penalty',
      }
    }

    return {
      chip: 'bg-red-100 text-red-700',
      fill: 'bg-red-500',
      track: 'bg-red-100',
      label: 'High Penalty',
    }
  }

  if (safeValue >= 75) {
    return {
      chip: 'bg-green-100 text-green-700',
      fill: 'bg-green-600',
      track: 'bg-green-100',
      label: 'Strong',
    }
  }

  if (safeValue >= 50) {
    return {
      chip: 'bg-blue-100 text-blue-700',
      fill: 'bg-blue-600',
      track: 'bg-blue-100',
      label: 'Moderate',
    }
  }

  if (safeValue >= 25) {
    return {
      chip: 'bg-yellow-100 text-yellow-700',
      fill: 'bg-yellow-500',
      track: 'bg-yellow-100',
      label: 'Low',
    }
  }

  return {
    chip: 'bg-red-100 text-red-700',
    fill: 'bg-red-500',
    track: 'bg-red-100',
    label: 'Weak',
  }
}

function ScoreMetricCard({ scoreKey, label, helper, value }) {
  const safeValue = Math.max(0, Math.min(Number(value) || 0, 100))
  const tone = getScoreTone(scoreKey, safeValue)

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md cursor-default" title={helper}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold leading-none text-gray-900 dark:text-white tabular-nums">
            {safeValue}%
          </p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${tone.chip}`}
        >
          {tone.label}
        </span>
      </div>

      <p className="mt-3 text-xs leading-5 text-gray-500 dark:text-slate-400">
        {helper}
      </p>

      <div className={`mt-4 h-3 w-full overflow-hidden rounded-full ${tone.track}`}>
        <div
          className={`h-full rounded-full transition-all duration-700 ${tone.fill}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  )
}

export default function ProgressBarCard({ scores }) {
  if (!scores) return null

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-lg border border-gray-100 dark:border-slate-800">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Detailed Score Breakdown</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-slate-400">
            Each component score that contributes to the overall match. Hover a card to see what the score measures.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {scoreItems.map((item) => (
          <ScoreMetricCard
            key={item.key}
            scoreKey={item.key}
            label={item.label}
            helper={item.helper}
            value={scores[item.key]}
          />
        ))}
      </div>
    </div>
  )
}