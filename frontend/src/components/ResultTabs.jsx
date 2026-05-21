import { useEffect, useState } from 'react'

function dotClass(status) {
  if (status === 'good') return 'bg-green-500'
  if (status === 'warning') return 'bg-yellow-500'
  if (status === 'danger') return 'bg-red-500'
  if (status === 'info') return 'bg-blue-500'
  return 'bg-gray-400'
}

export default function ResultTabs({
  tabs,
  defaultTabKey,
  activeTabKey,
  onTabChange,
  renderContent = true,
}) {
  const initialKey = defaultTabKey || (tabs?.length ? tabs[0].key : '')
  const [internalActiveTab, setInternalActiveTab] = useState(initialKey)

  const isControlled = activeTabKey !== undefined && activeTabKey !== null
  const activeTab = isControlled ? activeTabKey : internalActiveTab

  useEffect(() => {
    const nextKey = defaultTabKey || (tabs?.length ? tabs[0].key : '')
    if (!isControlled) {
      setInternalActiveTab(nextKey)
    }
  }, [defaultTabKey, tabs, isControlled])

  const handleTabClick = (tabKey) => {
    if (!isControlled) {
      setInternalActiveTab(tabKey)
    }
    if (typeof onTabChange === 'function') {
      onTabChange(tabKey)
    }
  }

  const activeContent = tabs.find((tab) => tab.key === activeTab)?.content

  return (
    <div className="w-full space-y-5">
      <div className="sticky top-3 z-20 w-full rounded-3xl border border-gray-200 bg-white/95 p-3 shadow-lg backdrop-blur-sm">
        <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key
            const badge = tab.badge

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => handleTabClick(tab.key)}
                className={`group flex h-full w-full items-center justify-center gap-3 rounded-2xl border px-4 py-3 text-sm font-medium transition-all ${
                  isActive
                    ? 'border-black bg-black text-white shadow-md'
                    : 'border-transparent bg-gray-100 text-gray-700 hover:border-gray-200 hover:bg-white hover:shadow-sm'
                }`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${dotClass(tab.status)} ${
                    isActive ? 'ring-2 ring-white/30' : ''
                  }`}
                  aria-hidden="true"
                />

                <span className="truncate font-semibold">{tab.label}</span>

                {badge !== undefined && badge !== null && badge !== '' && (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      isActive
                        ? 'bg-white/15 text-white'
                        : 'bg-white text-gray-800'
                    }`}
                  >
                    {badge}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {renderContent && <div className="rounded-3xl">{activeContent}</div>}
    </div>
  )
}
