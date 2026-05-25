import { useState, useEffect } from 'react'

// ImportantBanner
// Props:
// - children: content
// - className: extra classes
// - muted: boolean — when true, uses subtle styles (less attention-seeking)
// - dismissKey: optional string key to persist dismissal in localStorage
export default function ImportantBanner({ children, className = '', muted = true, dismissKey = null }) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    if (dismissKey) {
      try {
        const v = localStorage.getItem(`bannerDismissed:${dismissKey}`)
        if (v === '1') setVisible(false)
      } catch (e) {
        // ignore storage errors
      }
    }
  }, [dismissKey])

  function dismiss() {
    try {
      if (dismissKey) localStorage.setItem(`bannerDismissed:${dismissKey}`, '1')
    } catch (e) {}
    setVisible(false)
  }

  if (!visible) return null

  const base = muted
    ? 'rounded-md border border-slate-200 bg-slate-50 dark:bg-transparent px-3 py-2 text-slate-700 dark:text-slate-300'
    : 'rounded-xl border-2 border-amber-300 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-amber-900 dark:text-amber-200'

  return (
    <div className={`${base} ${className}`}>
      <div className="flex items-start gap-3">
        <div className={muted ? 'text-lg opacity-80' : 'text-2xl leading-none'}>{muted ? 'ℹ️' : '⚠️'}</div>
        <div className="text-sm flex-1">
          {children}
        </div>
        {dismissKey !== null && (
          <button onClick={dismiss} title="Dismiss" className="ml-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 focus:outline-none">
            ×
          </button>
        )}
      </div>
    </div>
  )
}
