export default function AppBrand({ onClick }) {
  const handleClick = () => {
    if (typeof onClick === 'function') {
      onClick()
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="group grid w-full max-w-5xl cursor-pointer grid-cols-[72px_minmax(0,1fr)] items-center gap-5 rounded-[2rem] border border-slate-200 bg-white px-8 py-6 text-left shadow-[0_18px_55px_rgba(15,23,42,0.08)] ring-1 ring-slate-900/5 transition hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(15,23,42,0.12)] dark:border-slate-700 dark:bg-slate-900 dark:ring-white/10"
      title="Click to restart HireFit"
    >
      <div className="flex justify-center">
        <div className="rounded-3xl bg-slate-950 p-2.5 shadow-lg shadow-slate-950/15 dark:bg-white">
          <img
            src="/favicon.svg"
            alt="HireFit logo"
            className="h-14 w-14 shrink-0 rounded-2xl object-contain"
          />
        </div>
      </div>

      <div className="flex flex-col items-center justify-center text-center">
        <p className="mb-1 text-[10px] font-black uppercase tracking-[0.32em] text-slate-500 dark:text-slate-400">
          AI Hiring Intelligence
        </p>
        <h1 className="text-4xl font-black tracking-[-0.05em] text-slate-950 sm:text-5xl dark:text-white">
          HireFit
        </h1>
        <p className="mt-2 text-sm font-semibold text-slate-500 group-hover:text-slate-700 sm:text-lg dark:text-slate-300 dark:group-hover:text-white">
          AI-powered recruiter screening · rank candidates · shortlist with evidence
        </p>
      </div>
    </button>
  )
}
