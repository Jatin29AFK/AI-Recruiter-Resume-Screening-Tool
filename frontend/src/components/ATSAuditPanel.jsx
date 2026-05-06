function severityClass(severity) {
  if (severity === 'high') return 'bg-red-100 text-red-800'
  if (severity === 'medium') return 'bg-yellow-100 text-yellow-800'
  return 'bg-blue-100 text-blue-800'
}

export default function ATSAuditPanel({ atsAudit }) {
  if (!atsAudit) return null

  return (
    <div className="rounded-2xl bg-white p-6 shadow-lg">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-600">Grade: {atsAudit.grade}</p>
        <span className="rounded-full bg-black px-4 py-2 text-sm font-semibold text-white">
          Score: {atsAudit.score}
        </span>
      </div>

      <div className="space-y-3">
        {atsAudit.issues?.length > 0 ? (
          atsAudit.issues.map((issue, index) => (
            <div key={index} className="rounded-2xl border border-gray-200 p-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">{issue.title}</h3>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${severityClass(issue.severity)}`}>
                  {issue.severity}
                </span>
              </div>
              <p className="text-sm text-gray-700">{issue.details}</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-gray-500">No major ATS issues found.</p>
        )}
      </div>
    </div>
  )
}
