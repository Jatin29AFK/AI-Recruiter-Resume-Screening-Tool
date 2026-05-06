import { useEffect, useState } from 'react'

export default function CollapsibleSection({
  title,
  hint,
  children,
  defaultOpen = true,
}) {
  const [open, setOpen] = useState(defaultOpen)

  useEffect(() => {
    setOpen(defaultOpen)
  }, [defaultOpen, title])

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 shadow-lg border border-gray-100 dark:border-slate-800">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-6 py-5 text-left group"
      >
        <div className="min-w-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
          {hint && (
            <p className="mt-0.5 text-xs text-gray-400 dark:text-slate-500 group-hover:text-gray-500 transition-colors">
              {hint}
            </p>
          )}
        </div>
        <span className="ml-4 flex-shrink-0 rounded-lg bg-gray-100 dark:bg-slate-800 px-3 py-1 text-xs font-semibold text-gray-500 dark:text-slate-400 group-hover:bg-gray-200 dark:group-hover:bg-slate-700 transition">
          {open ? '▲ Hide' : '▼ Show'}
        </span>
      </button>

      {open && <div className="px-6 pb-6">{children}</div>}
    </div>
  )
}