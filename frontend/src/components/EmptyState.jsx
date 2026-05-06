const FEATURES = [
  { icon: '', title: 'Candidate Ranking', desc: 'Automatically ranks all uploaded candidates by JD fit score.' },
  { icon: '', title: 'Shortlist / Review / Reject', desc: 'Each resume is auto-bucketed into actionable hiring decisions.' },
  { icon: '', title: 'Skill Gap Detection', desc: 'Identifies critical missing skills vs JD requirements.' },
  { icon: '', title: 'ATS Audit', desc: 'Checks if resumes survive automated screening systems.' },
  { icon: '', title: 'Evidence Quality', desc: 'Scores how well skills are backed by concrete achievements.' },
]

export default function EmptyState() {
  return (
    <div className="w-full rounded-3xl border border-dashed border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-6 py-6 shadow-lg">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">Upload resumes and a job description to get started</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
          Rank candidates, flag skill gaps, and identify who is safe to forward to your hiring manager.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-2xl bg-gray-50 dark:bg-slate-800 border border-gray-100 dark:border-slate-700 px-3 py-3">
            <p className="text-lg mb-1">{f.icon}</p>
            <p className="text-xs font-semibold text-gray-800 dark:text-slate-200 leading-tight">{f.title}</p>
            <p className="mt-0.5 text-[11px] text-gray-500 dark:text-slate-400 leading-snug">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}