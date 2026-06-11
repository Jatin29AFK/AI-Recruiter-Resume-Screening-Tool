import ImportantBanner from './ImportantBanner'

const FEATURES = [
  { stat: '01', title: 'Candidate Ranking', desc: 'Automatically ranks every uploaded candidate by JD-fit score.' },
  { stat: '02', title: 'Shortlist / Review / Reject', desc: 'Buckets resumes into clear hiring decisions recruiters can act on.' },
  { stat: '03', title: 'Skill Gap Detection', desc: 'Flags critical missing skills and one-of requirement coverage.' },
  { stat: '04', title: 'ATS Audit', desc: 'Checks whether resumes survive automated screening systems.' },
  { stat: '05', title: 'Evidence Quality', desc: 'Scores whether skills are backed by real project or work evidence.' },
]

export default function EmptyState({ onOpenEmailIntake }) {
  return (
    <div className="w-full rounded-[2rem] border border-slate-200/80 bg-white/95 px-6 py-7 shadow-[0_18px_55px_rgba(15,23,42,0.08)] ring-1 ring-slate-900/5 backdrop-blur dark:border-slate-700 dark:bg-slate-900/95 dark:ring-white/10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400">
            Recruiter Screening Console
          </p>
          <h2 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white">
            Upload resumes and a job description to get started
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Rank candidates, flag skill gaps, validate evidence, and identify who is safe to forward to your hiring manager.
          </p>
        </div>

        <div className="flex flex-wrap items-stretch justify-end gap-3">
          <button
            type="button"
            onClick={onOpenEmailIntake}
            className="min-w-[180px] rounded-[1.75rem] border border-blue-200 bg-gradient-to-br from-blue-600 via-sky-600 to-cyan-500 px-5 py-4 text-left text-white shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl dark:border-blue-500/40"
          >
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] opacity-80">Email intake</p>
            <p className="mt-1 text-lg font-black">Open intake</p>
            <p className="mt-1 text-xs opacity-80">Review inbox candidates</p>
          </button>

          <div className="min-w-[180px] rounded-[1.75rem] border border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-700 px-5 py-4 text-right text-white shadow-lg dark:border-slate-700 dark:from-white dark:via-slate-100 dark:to-slate-200 dark:text-slate-950">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] opacity-70">Batch-ready</p>
            <p className="mt-1 text-lg font-black">100 resumes</p>
            <p className="mt-1 text-xs opacity-70">Ready for recruiter screening</p>
          </div>
        </div>
      </div>

      <ImportantBanner className="mb-6 w-full rounded-[1.5rem] border-slate-200 bg-slate-50/90 px-4 py-4 dark:border-slate-700 dark:bg-slate-800/70">
        <strong>Scores are AI estimates.</strong> When the system is unsure about a candidate's experience, skills, or fit, it flags the item for your review rather than making a definitive claim. <span className="font-medium">Always verify borderline or flagged candidates manually before making hiring decisions.</span>
      </ImportantBanner>

      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="group min-h-[132px] rounded-3xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white px-4 py-4 shadow-sm transition duration-300 hover:-translate-y-1 hover:border-slate-300 hover:shadow-lg dark:border-slate-700 dark:bg-gradient-to-b dark:from-slate-800 dark:to-slate-900 dark:hover:border-slate-600"
          >
            <div className="mb-5 flex items-center justify-between">
              <span className="rounded-full bg-slate-950 px-2.5 py-1 text-[10px] font-black tracking-wider text-white dark:bg-white dark:text-slate-950">
                {f.stat}
              </span>
              <span className="h-1.5 w-8 rounded-full bg-slate-300 transition group-hover:w-12 group-hover:bg-slate-950 dark:bg-slate-600 dark:group-hover:bg-white" />
            </div>
            <p className="text-sm font-black leading-tight text-slate-900 dark:text-white">{f.title}</p>
            <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
