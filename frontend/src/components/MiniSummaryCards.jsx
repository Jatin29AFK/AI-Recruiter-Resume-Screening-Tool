export default function MiniSummaryCards({
  result,
  tailorResult,
  applyReadiness,
}) {
  if (!result) return null

  const hasOptimizedResult = Boolean(tailorResult)

  const cards = [
    {
      title: 'Fit Score',
      value: `${result.scores?.overall_score ?? 0}%`,
      subtitle: result.scores?.fit_label || 'Unknown',
      helper:
        'Weighted blend of skill coverage, semantic similarity, evidence quality, and critical gap penalties. Primary ranking signal.',
      muted: false,
    },
    {
      title: 'ATS Format Score',
      value: `${result.ats_audit?.score ?? 0}`,
      subtitle: result.ats_audit?.grade || 'Unknown',
      helper:
        'How well the resume survives automated ATS scanning — formatting, readable section headers, keyword presence, no tables/images.',
      note:
        'Strong ATS score alone does not indicate a strong JD fit.',
      muted: false,
    },
    {
      title: 'Critical Gaps',
      value: `${result.critical_missing_skills?.length ?? 0}`,
      subtitle:
        result.critical_missing_skills?.length > 0
          ? 'Review before deciding'
          : 'No critical blockers',
      helper:
        'Count of must-have JD skills absent from the resume. Each gap reduces the overall score. Zero gaps is a strong positive signal.',
      muted: false,
    },
    {
      title: 'Optimized Score',
      value: hasOptimizedResult
        ? `${tailorResult.analysis_after?.overall_score ?? 0}%`
        : 'Pending',
      subtitle: hasOptimizedResult
        ? tailorResult.analysis_after?.fit_label || 'Updated'
        : 'Generate optimized draft',
      helper: hasOptimizedResult
        ? 'Estimated fit score after applying JD-targeted optimizations to the resume draft.'
        : 'Available after generating the JD-optimized resume draft in the Optimized Resume tab.',
      muted: !hasOptimizedResult,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-white p-5 shadow-lg">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Resume Scoring Summary
            </h2>
            <p className="mt-1 text-sm leading-6 text-gray-600">
              Readiness Score combines JD fit, ATS quality, evidence strength, and critical gap count into a single indicator. 80+ = strong submission, 65–79 = nearly ready, 50–64 = needs work, &lt;50 = significant gaps.
            </p>
          </div>

          <div className="grid min-w-[260px] grid-cols-1 gap-3 sm:grid-cols-2 lg:min-w-[320px]">
            <div className="rounded-2xl bg-gray-50 px-4 py-3 text-center">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Status
              </p>
              <div className="mt-2">
                <span
                  className={`inline-flex rounded-full px-4 py-2 text-sm font-semibold ${applyReadiness.badgeClass}`}
                >
                  {applyReadiness.label}
                </span>
              </div>
            </div>

            <div className="rounded-2xl bg-gray-50 px-4 py-3 text-center">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Readiness Score
              </p>
              <p className="mt-2 text-3xl font-bold leading-none text-gray-900">
                {applyReadiness.score}
              </p>
              <p className="mt-2 text-xs text-gray-500">
                80+ strong · 65–79 nearly ready · 50–64 needs work · &lt;50 major gaps
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div
            key={card.title}
            className={`rounded-2xl p-5 shadow-lg ${
              card.muted ? 'border border-dashed border-gray-300 bg-gray-50' : 'bg-white'
            }`}
          >
            <p className="text-sm font-medium text-gray-500">{card.title}</p>
            <p
              className={`mt-2 text-2xl font-bold ${
                card.muted ? 'text-gray-500' : 'text-gray-900'
              }`}
            >
              {card.value}
            </p>
            <p
              className={`mt-2 text-sm font-medium ${
                card.muted ? 'text-gray-600' : 'text-gray-700'
              }`}
            >
              {card.subtitle}
            </p>
            <p className="mt-2 text-xs leading-5 text-gray-500">{card.helper}</p>
          </div>
        ))}
      </div>
    </div>
  )
}