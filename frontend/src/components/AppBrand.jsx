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
      className="group grid w-full max-w-4xl cursor-pointer grid-cols-[96px_minmax(0,1fr)] items-center gap-5 rounded-[2rem] border border-slate-200/80 bg-white/95 px-7 py-6 text-left shadow-[0_18px_55px_rgba(15,23,42,0.08)] ring-1 ring-slate-900/5 backdrop-blur transition hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(15,23,42,0.12)] dark:border-slate-700 dark:bg-slate-900/95 dark:ring-white/10"
      title="Click to restart Havells Hiring Intelligence"
    >
      <div className="flex items-center justify-center">
        <img
          src="/havells.png"
          alt="Havells logo"
          className="h-24 w-24 shrink-0 object-contain"
        />
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
