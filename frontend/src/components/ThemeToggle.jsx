export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === 'dark'
  const nextMode = isDark ? 'Light' : 'Dark'

  return (
    <button
      type="button"
      onClick={onToggle}
      className="group flex items-center gap-3 rounded-full border border-slate-200/80 bg-white/90 px-3 py-2 text-slate-900 shadow-[0_14px_35px_rgba(15,23,42,0.08)] backdrop-blur transition hover:-translate-y-0.5 hover:border-slate-400 hover:shadow-[0_18px_42px_rgba(15,23,42,0.14)] dark:border-slate-700 dark:bg-slate-900/90 dark:text-white"
      title={`Switch to ${nextMode} mode`}
      aria-label={`Switch to ${nextMode} mode`}
    >
      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.24em] text-slate-500 dark:bg-slate-800 dark:text-slate-300">
        {isDark ? 'Dark' : 'Light'}
      </span>
      <span className="relative flex h-8 w-14 items-center rounded-full border border-slate-200 bg-slate-100 px-1 dark:border-slate-700 dark:bg-slate-800" aria-hidden="true">
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-full bg-white text-[11px] shadow-sm transition duration-300 dark:bg-slate-950 ${
            isDark ? 'translate-x-6' : 'translate-x-0'
          }`}
        >
          {isDark ? '☾' : '☀'}
        </span>
      </span>
      <span className="hidden text-xs font-black uppercase tracking-[0.22em] text-slate-500 sm:inline dark:text-slate-300">
        Switch to {nextMode}
      </span>
    </button>
  )
}
