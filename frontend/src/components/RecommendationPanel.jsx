/**
 * RecommendationPanel
 * ───────────────────
 * Displays the full recruiter recommendation block:
 *   • Section-wise scores (name + bar + explanation)
 *   • Key strengths
 *   • Gaps / risks (material only)
 *   • Final recommendation badge + 2-3 line justification
 */

function SectionScoreBar({ name, score, explanation }) {
  const pct = Math.min(100, Math.max(0, score))
  const barColor =
    pct >= 70 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-400'
  const textColor =
    pct >= 70
      ? 'text-green-600 dark:text-green-400'
      : pct >= 50
      ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-red-500 dark:text-red-400'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-800 dark:text-white">{name}</p>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400 leading-relaxed">
            {explanation}
          </p>
        </div>
        <span className={`flex-shrink-0 text-xl font-bold ${textColor}`}>{pct}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

const VERDICT_STYLES = {
  'Strongly Recommended': {
    bg: 'bg-green-50 dark:bg-green-950 border-green-300 dark:border-green-700',
    badge: 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200',
    icon: '✅',
  },
  Recommended: {
    bg: 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800',
    badge: 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
    icon: '✓',
  },
  Borderline: {
    bg: 'bg-yellow-50 dark:bg-yellow-950 border-yellow-300 dark:border-yellow-700',
    badge: 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200',
    icon: '~',
  },
  'Not Recommended': {
    bg: 'bg-red-50 dark:bg-red-950 border-red-300 dark:border-red-700',
    badge: 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200',
    icon: '✗',
  },
}

export default function RecommendationPanel({ recommendation }) {
  if (!recommendation) return null

  const { section_scores, key_strengths, gaps_and_risks, final_recommendation } = recommendation
  const verdict = final_recommendation?.label || 'Borderline'
  const style = VERDICT_STYLES[verdict] || VERDICT_STYLES.Borderline

  return (
    <div className="space-y-6">

      {/* ── Final Recommendation ── */}
      <div className={`rounded-2xl border p-5 ${style.bg} space-y-3`}>
        <div className="flex flex-wrap items-center gap-3">
          <span className={`rounded-full px-4 py-1.5 text-sm font-bold ${style.badge}`}>
            {style.icon} {verdict}
          </span>
          <p className="text-xs text-gray-500 dark:text-slate-400">Final Recommendation</p>
        </div>
        <p className="text-sm leading-relaxed text-gray-700 dark:text-slate-300">
          {final_recommendation?.justification}
        </p>
      </div>

      {/* ── Section-wise Scores ── */}
      {section_scores?.length > 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-5">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">
              Section-wise Assessment
            </h3>
            <p className="mt-0.5 text-xs text-gray-400 dark:text-slate-500">
              Each dimension scored independently. Click "Score Guide" in the header for detailed range explanations.
            </p>
          </div>
          <div className="space-y-5">
            {section_scores.map((s) => (
              <SectionScoreBar
                key={s.name}
                name={s.name}
                score={s.score}
                explanation={s.explanation}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Strengths + Gaps side-by-side on wide screens ── */}
      <div className="grid gap-4 sm:grid-cols-2">

        {/* Key Strengths */}
        {key_strengths?.length > 0 && (
          <div className="rounded-2xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 p-5 space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wide text-green-800 dark:text-green-300">
              ✓ Key Strengths
            </h3>
            <ul className="space-y-2">
              {key_strengths.map((s, i) => (
                <li
                  key={i}
                  className="flex gap-2 text-sm text-gray-700 dark:text-slate-300"
                >
                  <span className="flex-shrink-0 mt-0.5 text-green-500">•</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Gaps & Risks */}
        {gaps_and_risks?.length > 0 ? (
          <div className="rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 p-5 space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wide text-amber-800 dark:text-amber-300">
              ⚠ Gaps / Risks
            </h3>
            <p className="text-xs text-amber-700 dark:text-amber-400">
              Only material gaps that could affect suitability are listed here. Minor tool gaps and preferred-only skills are excluded.
            </p>
            <ul className="space-y-2">
              {gaps_and_risks.map((g, i) => (
                <li
                  key={i}
                  className="flex gap-2 text-sm text-gray-700 dark:text-slate-300"
                >
                  <span className="flex-shrink-0 mt-0.5 text-amber-500">▸</span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="rounded-2xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 p-5 flex items-center gap-3">
            <span className="text-2xl">🟢</span>
            <div>
              <p className="text-sm font-semibold text-green-800 dark:text-green-300">No Material Gaps</p>
              <p className="text-xs text-green-700 dark:text-green-400 mt-0.5">
                No significant blockers detected against the JD requirements.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 dark:text-slate-500 text-center">
        {/* This recommendation is AI-assisted — use it as a structured starting point, not a final decision. Always review the full resume before proceeding. */}
      </p>
    </div>
  )
}
