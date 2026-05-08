/**
 * CertificationCoveragePanel
 * Shows whether the candidate holds certifications relevant to JD skills.
 *
 * Props:
 *   certCoverage – the `cert_coverage` object from the backend:
 *     {
 *       certs_found: string[],
 *       jd_skill_cert_map: { [skill]: string[] },
 *       covered_skills: string[],
 *       uncovered_skills: string[],
 *       coverage_pct: number,
 *       has_any_certs: boolean,
 *     }
 *   jdRequiredSkills  – string[] (optional, for context label)
 *   jdPreferredSkills – string[] (optional)
 */
export default function CertificationCoveragePanel({
  certCoverage,
  jdRequiredSkills = [],
  jdPreferredSkills = [],
}) {
  if (!certCoverage) return null

  const {
    certs_found = [],
    jd_skill_cert_map = {},
    covered_skills = [],
    uncovered_skills = [],
    coverage_pct = 0,
    has_any_certs = false,
  } = certCoverage

  const allJdSkills = Object.keys(jd_skill_cert_map)
  const requiredSet = new Set((jdRequiredSkills || []).map((s) => s.toLowerCase()))

  // If no certs at all and no JD skills to check — nothing to show
  if (!has_any_certs && allJdSkills.length === 0) return null

  const coverageBadgeClass =
    coverage_pct >= 60
      ? 'bg-green-100 text-green-800'
      : coverage_pct >= 30
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-gray-100 text-gray-700'

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-lg border border-gray-100 dark:border-slate-700">
      {/* Header */}
      <div className="mb-5 flex flex-col gap-1">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Certification Coverage
          </h2>
          {allJdSkills.length > 0 && (
            <span
              className={`rounded-full px-3 py-1 text-sm font-semibold ${coverageBadgeClass}`}
            >
              {covered_skills.length}/{allJdSkills.length} JD skills have cert support
            </span>
          )}
        </div>
        <p className="text-sm leading-6 text-gray-600 dark:text-slate-400">
          Checks whether the candidate holds certifications relevant to the skills
          listed in the JD. Certifications are extracted from the resume and
          cross-referenced — useful for regulatory or cloud-heavy roles.
        </p>
      </div>

      {/* No certs found notice */}
      {!has_any_certs && (
        <div className="rounded-2xl bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-600 px-4 py-3 mb-5">
          <p className="text-sm text-gray-600 dark:text-slate-400">
            <span className="font-semibold text-gray-800 dark:text-slate-200">
              No certifications detected
            </span>{' '}
            in this resume. Skills may still be demonstrated through experience —
            confirm in a technical interview.
          </p>
        </div>
      )}

      {/* Certs found list */}
      {has_any_certs && certs_found.length > 0 && (
        <div className="mb-5">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            Certifications Found in Resume
          </p>
          <ul className="space-y-1.5">
            {certs_found.map((cert, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-gray-800 dark:text-slate-200"
              >
                <span className="mt-0.5 text-green-500 flex-shrink-0 font-bold">✓</span>
                {cert}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* JD skill → cert map */}
      {allJdSkills.length > 0 && (
        <div>
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            JD Skills vs. Candidate Certifications
          </p>
          <div className="space-y-2">
            {allJdSkills.map((skill) => {
              const skillCerts = jd_skill_cert_map[skill] || []
              const hasCert = skillCerts.length > 0
              const isRequired = requiredSet.has(skill.toLowerCase())

              return (
                <div
                  key={skill}
                  className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
                    hasCert
                      ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950'
                      : isRequired
                      ? 'border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950'
                      : 'border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-800'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex-shrink-0 font-bold text-sm ${
                      hasCert
                        ? 'text-green-600 dark:text-green-400'
                        : isRequired
                        ? 'text-orange-500 dark:text-orange-400'
                        : 'text-gray-400 dark:text-slate-500'
                    }`}
                  >
                    {hasCert ? '✓' : isRequired ? '!' : '–'}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white capitalize">
                        {skill}
                      </span>
                      {isRequired && (
                        <span className="rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 text-xs font-semibold">
                          Required
                        </span>
                      )}
                    </div>

                    {hasCert ? (
                      <ul className="mt-1 space-y-0.5">
                        {skillCerts.map((c, ci) => (
                          <li
                            key={ci}
                            className="text-xs text-green-700 dark:text-green-300"
                          >
                            {c}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                        {isRequired
                          ? 'No related certificate found — verify skill depth in interview'
                          : 'No certificate evidence for this preferred skill'}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Footer note */}
      <p className="mt-5 text-xs text-gray-400 dark:text-slate-500 leading-5">
        Cert detection uses keyword matching on the resume's certifications section and
        inline credential mentions. A missing cert does not mean the candidate lacks the
        skill — it means no documented credential was found. Always verify via interview.
      </p>
    </div>
  )
}
