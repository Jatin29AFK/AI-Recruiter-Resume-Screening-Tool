export default function ExperiencePanel({
  experienceEstimate,
  experienceComparison,
  jdRequirements,
}) {
  if (!experienceEstimate || !experienceComparison || !jdRequirements) return null

  const meetsRequirement = experienceComparison.meets_requirement
  const minYears = jdRequirements.experience_requirements?.min_years_experience
  const hasExplicitRequirement = minYears !== null && minYears !== undefined

  const badgeClass =
    meetsRequirement === true
      ? 'bg-green-100 text-green-800'
      : meetsRequirement === false
      ? 'bg-red-100 text-red-800'
      : 'bg-gray-100 text-gray-800'

  return (
    <div className="rounded-2xl bg-white p-6 shadow-lg">
      <div className="mb-5 flex flex-col gap-2">
        <h2 className="text-xl font-semibold text-gray-900">
          Experience Alignment
        </h2>
        <p className="text-sm leading-6 text-gray-600">
          This section compares estimated resume experience against the job description’s
          stated experience requirement, when one is explicitly detected.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Estimated Resume Experience</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {experienceEstimate.estimated_years != null
              ? `${experienceEstimate.estimated_years} yr${experienceEstimate.estimated_years !== 1 ? 's' : ''}`
              : 'N/A'}
          </p>
          {experienceEstimate.estimated_months != null && (
            <p className="mt-1 text-xs text-gray-500">
              ({experienceEstimate.estimated_months} months total from experience section)
            </p>
          )}
          <p className="mt-2 text-xs leading-5 text-gray-500">
            {experienceEstimate.note}
          </p>
        </div>

        <div className="rounded-2xl border border-gray-200 p-4">
          <p className="text-sm text-gray-500">JD Minimum Experience</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {hasExplicitRequirement ? minYears : 'Not explicitly stated'}
          </p>
          <p className="mt-2 text-xs leading-5 text-gray-500">
            {hasExplicitRequirement
              ? 'Detected directly from the job description.'
              : 'No clear minimum years requirement was detected from the JD text.'}
          </p>
        </div>

        <div className="rounded-2xl border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Requirement Status</p>
          <div className="mt-2">
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${badgeClass}`}>
              {meetsRequirement === true
                ? 'Likely Meets Requirement'
                : meetsRequirement === false
                ? 'May Be Below Requirement'
                : 'Could Not Confirm'}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-gray-600">
            {experienceComparison.message}
          </p>
        </div>
      </div>

      {!hasExplicitRequirement && (
        <div className="mt-4 rounded-2xl bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-800">
          No explicit minimum years requirement was detected in the JD, so this experience
          check is shown as a heuristic estimate rather than a strict pass/fail requirement.
        </div>
      )}
    </div>
  )
}