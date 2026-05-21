export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === 'dark'
  const nextMode = isDark ? 'Light' : 'Dark'

  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex h-12 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 text-slate-900 shadow-lg shadow-slate-950/10 ring-1 ring-slate-900/5 transition hover:-translate-y-0.5 hover:border-slate-400 hover:shadow-xl dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:ring-white/10"
      title={`Switch to ${nextMode} mode`}
      aria-label={`Switch to ${nextMode} mode`}
    >
      <span className="relative h-5 w-5 rounded-full border-2 border-current" aria-hidden="true">
        <span
          className={`absolute inset-1 rounded-full bg-current transition ${
            isDark ? 'scale-50' : 'scale-100'
          }`}
        />
      </span>
      <span className="hidden text-xs font-black uppercase tracking-wide sm:inline">
        {isDark ? 'Dark' : 'Light'}
      </span>
      <span className="hidden rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-500 sm:inline dark:bg-slate-800 dark:text-slate-300">
        
      </span>
    </button>
  )
}
