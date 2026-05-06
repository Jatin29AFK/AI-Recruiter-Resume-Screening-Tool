import { useState } from 'react'

function statusClass(status) {
  if (status === 'strong') return 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200'
  if (status === 'medium') return 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200'
  if (status === 'weak') return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200'
  return 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200'
}

function priorityClass(priority) {
  if (priority === 'required') return 'text-red-700 dark:text-red-400'
  if (priority === 'preferred') return 'text-blue-700 dark:text-blue-400'
  return 'text-gray-700 dark:text-slate-300'
}

const FILTER_OPTIONS = [
  { key: 'all',     label: 'All' },
  { key: 'strong',  label: 'Strong' },
  { key: 'medium',  label: 'Medium' },
  { key: 'weak',    label: 'Weak' },
  { key: 'missing', label: 'Missing' },
]

export default function KeywordCoveragePanel({ keywordCoverage }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [expandedSkill, setExpandedSkill] = useState(null)

  if (!keywordCoverage || !keywordCoverage.items?.length) {
    return <p className="text-sm text-gray-500">No keyword coverage available.</p>
  }

  const summary = keywordCoverage.summary ?? {}
  const items = keywordCoverage.items ?? []

  const filtered = activeFilter === 'all'
    ? items
    : items.filter(item => item.status === activeFilter)

  const summaryBadges = [
    { key: 'strong',  label: 'Strong',  count: summary.strong_count  ?? 0, cls: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200 border border-green-300 dark:border-green-700' },
    { key: 'medium',  label: 'Medium',  count: summary.medium_count  ?? 0, cls: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200 border border-blue-300 dark:border-blue-700' },
    { key: 'weak',    label: 'Weak',    count: summary.weak_count    ?? 0, cls: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200 border border-yellow-300 dark:border-yellow-700' },
    { key: 'missing', label: 'Missing', count: summary.missing_count ?? 0, cls: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200 border border-red-300 dark:border-red-700' },
  ]

  return (
    <div className="space-y-5">
      {/* Clickable summary badges — click to filter */}
      <div className="flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          onClick={() => setActiveFilter('all')}
          className={`rounded-full px-3 py-1.5 font-semibold transition border ${
            activeFilter === 'all'
              ? 'bg-gray-900 text-white border-gray-900 dark:bg-white dark:text-gray-900 dark:border-white'
              : 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-600 hover:bg-gray-200 dark:hover:bg-slate-700'
          }`}
        >
          All ({items.length})
        </button>
        {summaryBadges.map(b => (
          <button
            key={b.key}
            type="button"
            onClick={() => setActiveFilter(prev => prev === b.key ? 'all' : b.key)}
            className={`rounded-full px-3 py-1.5 font-semibold transition ${b.cls} ${
              activeFilter === b.key ? 'ring-2 ring-offset-1 ring-current' : 'hover:opacity-80'
            }`}
            title={`Click to show only ${b.label.toLowerCase()} keywords`}
          >
            {b.label}: {b.count} {activeFilter === b.key ? '▲' : '▼'}
          </button>
        ))}
      </div>

      {/* Filter label */}
      {activeFilter !== 'all' && (
        <p className="text-xs text-gray-500 dark:text-slate-400">
          Showing {filtered.length} <span className="font-semibold">{activeFilter}</span> keyword{filtered.length !== 1 ? 's' : ''}.{' '}
          <button type="button" onClick={() => setActiveFilter('all')} className="underline hover:no-underline">Show all</button>
        </p>
      )}

      {filtered.length === 0 && (
        <p className="text-sm text-gray-400 dark:text-slate-500">No {activeFilter} keywords found.</p>
      )}

      <div className="grid gap-3">
        {filtered.map((item, index) => {
          const isExpanded = expandedSkill === item.skill
          const hasEvidence = item.supporting_lines?.length > 0
          return (
            <div
              key={`${item.skill}-${item.priority}-${index}`}
              className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 p-4"
            >
              <div className="mb-2 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <h3 className={`font-semibold ${priorityClass(item.priority)}`}>
                  {item.skill}
                </h3>

                <div className="flex gap-2 flex-wrap">
                  <span className="rounded-full bg-white dark:bg-slate-700 px-3 py-1 text-xs font-semibold text-gray-700 dark:text-slate-200 border border-gray-200 dark:border-slate-600">
                    {item.priority}
                  </span>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClass(item.status)}`}>
                    {item.status}
                  </span>
                  {hasEvidence && (
                    <button
                      type="button"
                      onClick={() => setExpandedSkill(isExpanded ? null : item.skill)}
                      className="rounded-full bg-white dark:bg-slate-700 px-3 py-1 text-xs font-semibold text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950 transition"
                    >
                      {isExpanded ? 'Hide evidence ▲' : `${item.supporting_lines.length} evidence ▼`}
                    </button>
                  )}
                </div>
              </div>

              <p className="text-sm text-gray-600 dark:text-slate-400">
                Evidence Sections:{' '}
                {item.evidence_sections?.length ? item.evidence_sections.join(', ') : 'None'}
              </p>

              {/* Expandable evidence lines */}
              {isExpanded && hasEvidence && (
                <div className="mt-3 space-y-1.5 border-t border-gray-200 dark:border-slate-700 pt-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-gray-400 dark:text-slate-500">Supporting Lines from Resume</p>
                  {item.supporting_lines.map((line, li) => (
                    <p key={li} className="text-xs text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-900 rounded-xl px-3 py-2 border border-gray-100 dark:border-slate-700 leading-relaxed">
                      "{line}"
                    </p>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}