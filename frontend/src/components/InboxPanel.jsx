import { useEffect, useState } from 'react'
import { getInboxSummary, getInboxQueue, processInboxQueue, fetchJobs } from '../services/api'

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

const verdictColors = {
  Shortlist: 'bg-green-100 text-green-700',
  Review: 'bg-yellow-100 text-yellow-700',
  Reject: 'bg-red-100 text-red-700',
}

export default function InboxPanel({ onScreeningComplete }) {
  const [summary, setSummary] = useState([])         // per-job pending counts
  const [jobs, setJobs] = useState([])               // saved jobs list
  const [selectedJobId, setSelectedJobId] = useState(null)
  const [queueItems, setQueueItems] = useState([])   // CVs for selected job
  const [loadingQueue, setLoadingQueue] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [open, setOpen] = useState(false)

  // Load saved jobs + inbox summary on mount
  useEffect(() => {
    async function load() {
      try {
        const [jobsData, summaryData] = await Promise.all([
          fetchJobs(),
          getInboxSummary(),
        ])
        setJobs(jobsData.jobs || [])
        setSummary(summaryData.jobs || [])
      } catch {
        // silently ignore — inbox is an optional feature
      }
    }
    load()
  }, [])

  async function handleSelectJob(jobId) {
    setSelectedJobId(jobId)
    setQueueItems([])
    setError('')
    setSuccessMsg('')
    if (!jobId) return
    setLoadingQueue(true)
    try {
      const data = await getInboxQueue(jobId)
      setQueueItems(data.items || [])
    } catch (err) {
      setError(err.message || 'Failed to load inbox queue.')
    } finally {
      setLoadingQueue(false)
    }
  }

  async function handleProcess() {
    if (!selectedJobId) return
    setProcessing(true)
    setError('')
    setSuccessMsg('')
    try {
      const batchResult = await processInboxQueue(selectedJobId)
      setSuccessMsg(
        `Screening complete — ${batchResult.total_candidates} CV(s) analysed. Results loaded in Recruiter Dashboard below.`
      )
      // Refresh queue view
      const updated = await getInboxQueue(selectedJobId)
      setQueueItems(updated.items || [])
      // Refresh summary counts
      const summaryData = await getInboxSummary()
      setSummary(summaryData.jobs || [])
      // Pass result up to App so RecruiterDashboard renders it
      if (onScreeningComplete) onScreeningComplete(batchResult)
    } catch (err) {
      setError(err.message || 'Screening failed. Check that the job has a JD description.')
    } finally {
      setProcessing(false)
    }
  }

  const pendingCount = queueItems.filter((i) => i.status === 'pending').length
  const totalInbox = summary.reduce((s, j) => s + (j.pending || 0), 0)

  const jobTitle = (jobId) =>
    jobs.find((j) => j.job_id === jobId)?.title || jobId

  return (
    <div className="rounded-2xl border border-indigo-200 bg-white dark:bg-slate-900 dark:border-slate-700 shadow-lg overflow-hidden">
      {/* Header bar */}
      <button
        className="w-full flex items-center justify-between px-5 py-4 text-left focus:outline-none"
        onClick={() => setOpen((prev) => !prev)}
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">📬</span>
          <div>
            <p className="font-semibold text-gray-800 dark:text-white text-sm">
              Email Inbox — CV Screening
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              CVs forwarded to your job inbox address are listed here. Select a job and screen them.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {totalInbox > 0 && (
            <span className="rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold px-2 py-0.5">
              {totalInbox} pending
            </span>
          )}
          <span className="text-gray-400 text-sm">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-gray-100 dark:border-slate-700 pt-4">

          {/* How it works */}
          <div className="rounded-xl bg-indigo-50 dark:bg-slate-800 border border-indigo-100 dark:border-slate-600 px-4 py-3 text-xs text-indigo-800 dark:text-indigo-200 space-y-1">
            <p className="font-semibold">How to use</p>
            <ol className="list-decimal list-inside space-y-0.5">
              <li>
                In Outlook, create a forwarding rule: <em>"When subject contains
                'Application'→ forward to <strong>cvs-&#123;job_id&#125;@yourdomain.com</strong>"</em>
              </li>
              <li>CVs appear here automatically (pending).</li>
              <li>Select a job, then click <strong>Screen pending CVs</strong>.</li>
              <li>Results open in the Recruiter Dashboard below.</li>
            </ol>
          </div>

          {/* Per-job summary chips */}
          {summary.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {summary.map((s) => (
                <button
                  key={s.job_id}
                  onClick={() => handleSelectJob(s.job_id)}
                  className={`rounded-full px-3 py-1 text-xs font-medium border transition
                    ${selectedJobId === s.job_id
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 border-gray-200 dark:border-slate-500 hover:border-indigo-400'
                    }`}
                >
                  {jobTitle(s.job_id)} — {s.pending} pending
                </button>
              ))}
            </div>
          )}

          {/* Job selector */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
            <select
              className="flex-1 rounded-xl border border-gray-200 dark:border-slate-600 px-3 py-2 text-sm
                         bg-white dark:bg-slate-800 text-gray-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
              value={selectedJobId || ''}
              onChange={(e) => handleSelectJob(e.target.value || null)}
            >
              <option value="">— Select a saved job —</option>
              {jobs.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.title}
                </option>
              ))}
            </select>

            <button
              onClick={handleProcess}
              disabled={!selectedJobId || pendingCount === 0 || processing}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition whitespace-nowrap
                ${!selectedJobId || pendingCount === 0 || processing
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                }`}
            >
              {processing
                ? 'Screening…'
                : pendingCount > 0
                ? `Screen ${pendingCount} pending CV${pendingCount > 1 ? 's' : ''}`
                : 'No pending CVs'}
            </button>
          </div>

          {/* Error / success */}
          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 px-4 py-2 text-sm">
              {error}
            </div>
          )}
          {successMsg && (
            <div className="rounded-xl bg-green-50 border border-green-200 text-green-700 px-4 py-2 text-sm">
              {successMsg}
            </div>
          )}

          {/* CV list */}
          {loadingQueue && (
            <p className="text-xs text-gray-500 animate-pulse">Loading inbox…</p>
          )}

          {!loadingQueue && queueItems.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-slate-700">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 dark:bg-slate-800 text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    <th className="text-left px-3 py-2">File</th>
                    <th className="text-left px-3 py-2">From</th>
                    <th className="text-left px-3 py-2">Subject</th>
                    <th className="text-left px-3 py-2">Received</th>
                    <th className="text-left px-3 py-2">Status</th>
                    <th className="text-left px-3 py-2">Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {queueItems.map((item) => (
                    <tr
                      key={item.cv_id}
                      className="border-t border-gray-100 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800 transition"
                    >
                      <td className="px-3 py-2 font-medium text-gray-700 dark:text-gray-200 max-w-[140px] truncate">
                        {item.filename}
                      </td>
                      <td className="px-3 py-2 text-gray-500 dark:text-gray-400 max-w-[140px] truncate">
                        {item.sender}
                      </td>
                      <td className="px-3 py-2 text-gray-500 dark:text-gray-400 max-w-[160px] truncate">
                        {item.subject || '—'}
                      </td>
                      <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                        {item.received_at
                          ? new Date(item.received_at).toLocaleDateString('en-GB', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`rounded-full px-2 py-0.5 font-semibold capitalize
                            ${statusColors[item.status] || 'bg-gray-100 text-gray-600'}`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {item.shortlist_verdict ? (
                          <span
                            className={`rounded-full px-2 py-0.5 font-semibold
                              ${verdictColors[item.shortlist_verdict] || 'bg-gray-100 text-gray-600'}`}
                          >
                            {item.shortlist_verdict}
                          </span>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loadingQueue && selectedJobId && queueItems.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">
              No inbound CVs for this job yet. Forward application emails to{' '}
              <code className="bg-gray-100 dark:bg-slate-700 rounded px-1">
                cvs-{selectedJobId}@yourdomain.com
              </code>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
