export default function SummaryHero({ filename, scores, actions = null, analysisMeta = null }) {
  if (!scores) return null

  const fitColor =
    scores.fit_label === 'Excellent Fit'
      ? 'text-emerald-700 bg-emerald-100'
      : scores.fit_label === 'Good Fit'
      ? 'text-blue-700 bg-blue-100'
      : scores.fit_label === 'Average Fit'
      ? 'text-yellow-700 bg-yellow-100'
      : 'text-red-700 bg-red-100'

  const reliability = analysisMeta?.reliability || 'unknown'
  const activeDomainLabel = analysisMeta?.active_domain?.label || 'General'
  const warningMessage = analysisMeta?.warning_message || null

  const reliabilityClass =
    reliability === 'high'
      ? 'bg-green-100 text-green-800'
      : reliability === 'medium'
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800'

  return (
    <div className="rounded-3xl bg-white p-5 shadow-lg md:p-6">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">
            Analyzed Resume
          </p>
          <h2 className="mt-2 truncate text-2xl font-bold text-gray-900 md:text-3xl">
            {filename}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
            Compatibility snapshot: skill coverage against JD requirements, semantic text similarity,
            evidence quality (proof behind claimed skills), and estimated experience alignment.
            <span className="font-medium text-emerald-700"> Excellent ≥85</span> ·
            <span className="font-medium text-blue-700"> Good 70–84</span> ·
            <span className="font-medium text-yellow-700"> Average 50–69</span> ·
            <span className="font-medium text-red-600"> Low &lt;50</span>.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">
              Active Domain: {activeDomainLabel}
            </span>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${reliabilityClass}`}>
              Analysis Reliability: {reliability}
            </span>
          </div>

          {warningMessage ? (
            <div className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
              {warningMessage}
            </div>
          ) : null}

          {scores.recruiter_action ? (
            <div className={`mt-4 flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium ${
              scores.shortlist_recommendation
                ? 'bg-blue-50 text-blue-800'
                : 'bg-gray-100 text-gray-600'
            }`}>
              <span className="text-base">{scores.shortlist_recommendation ? '✓' : '○'}</span>
              <span>{scores.recruiter_action}</span>
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-4 lg:items-end">
          <div className="flex items-end gap-4 lg:justify-end">
            <div className="text-left lg:text-right">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">
                Overall Match
              </p>
              <p className="mt-1 text-4xl font-extrabold leading-none text-gray-900 md:text-5xl">
                {scores.overall_score}%
              </p>
            </div>

            <span className={`inline-flex rounded-full px-4 py-2 text-sm font-semibold ${fitColor}`}>
              {scores.fit_label}
            </span>
          </div>

          {actions ? <div className="w-full lg:w-auto">{actions}</div> : null}
        </div>
      </div>
    </div>
  )
}