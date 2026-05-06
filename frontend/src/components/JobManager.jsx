/**
 * JobManager Component
 * ────────────────────
 * Manage saved job descriptions:
 * - Create new jobs
 * - View/edit/delete existing jobs
 * - Clone jobs
 * - Quick-load saved JDs into upload form
 */

import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { listJobs, createJob, updateJob, deleteJob, cloneJob } from '../services/api'

const emptyFormData = {
  title: '',
  description: '',
  required_skills: '',
  preferred_skills: '',
  min_experience: '',
  education_requirements: '',
  mandatory_certifications: '',
  tags: ''
}

export default function JobManager({ initialDescription = '', onSelectJob, onClose }) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingJob, setEditingJob] = useState(null)
  
  const [formData, setFormData] = useState(() => ({
    ...emptyFormData,
    description: initialDescription
  }))

  useEffect(() => {
    loadJobs()
  }, [])

  const loadJobs = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await listJobs()
      setJobs(response.jobs || [])
    } catch (error) {
      console.error('Failed to load jobs:', error)
      setError(error.message || 'Failed to load saved jobs.')
    } finally {
      setLoading(false)
    }
  }

  const openCreateForm = () => {
    setEditingJob(null)
    setFormData({
      ...emptyFormData,
      description: initialDescription
    })
    setShowCreateForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    const jobData = {
      title: formData.title,
      description: formData.description,
      required_skills: formData.required_skills.split(',').map(s => s.trim()).filter(Boolean),
      preferred_skills: formData.preferred_skills.split(',').map(s => s.trim()).filter(Boolean),
      min_experience: formData.min_experience ? parseInt(formData.min_experience) : null,
      education_requirements: formData.education_requirements.split(',').map(s => s.trim()).filter(Boolean),
      mandatory_certifications: formData.mandatory_certifications.split(',').map(s => s.trim()).filter(Boolean),
      tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean)
    }

    try {
      if (editingJob) {
        await updateJob(editingJob.job_id, jobData)
      } else {
        await createJob(jobData)
      }
      
      resetForm()
      await loadJobs()
    } catch (error) {
      alert(`Failed to ${editingJob ? 'update' : 'create'} job: ${error.message}`)
    }
  }

  const handleEdit = (job) => {
    setEditingJob(job)
    setFormData({
      title: job.title,
      description: job.description,
      required_skills: job.required_skills.join(', '),
      preferred_skills: job.preferred_skills.join(', '),
      min_experience: job.min_experience || '',
      education_requirements: (job.education_requirements || []).join(', '),
      mandatory_certifications: (job.mandatory_certifications || []).join(', '),
      tags: job.tags.join(', ')
    })
    setShowCreateForm(true)
  }

  const handleDelete = async (jobId, jobTitle) => {
    if (!confirm(`Delete "${jobTitle}"?`)) return
    
    try {
      await deleteJob(jobId)
      await loadJobs()
    } catch (error) {
      alert(`Failed to delete job: ${error.message}`)
    }
  }

  const handleClone = async (jobId) => {
    try {
      await cloneJob(jobId)
      await loadJobs()
    } catch (error) {
      alert(`Failed to clone job: ${error.message}`)
    }
  }

  const resetForm = () => {
    setFormData(emptyFormData)
    setEditingJob(null)
    setShowCreateForm(false)
  }

  const modal = (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-700 bg-slate-900 p-5">
          <div>
            <h2 className="text-lg font-bold text-white">Saved Jobs</h2>
            <p className="mt-0.5 text-xs text-slate-400">Create, manage, and quick-load job descriptions</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition"
          >
            ✕
          </button>
        </div>

        <div className="bg-slate-900 p-5 space-y-4">
          
          {/* Create/Edit Form */}
          {showCreateForm && (
            <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5">
              <h3 className="mb-4 text-sm font-bold text-white">
                {editingJob ? 'Edit Job' : 'Create New Job'}
              </h3>
              
              <form onSubmit={handleSubmit} className="space-y-3">
                <input
                  type="text"
                  placeholder="Job Title*"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
                
                <textarea
                  placeholder="Job Description*"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  rows="6"
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
                
                <input
                  type="text"
                  placeholder="Required Skills (comma-separated)"
                  value={formData.required_skills}
                  onChange={(e) => setFormData({...formData, required_skills: e.target.value})}
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
                
                <input
                  type="text"
                  placeholder="Preferred Skills (comma-separated)"
                  value={formData.preferred_skills}
                  onChange={(e) => setFormData({...formData, preferred_skills: e.target.value})}
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
                
                <input
                  type="number"
                  placeholder="Minimum Experience (years)"
                  value={formData.min_experience}
                  onChange={(e) => setFormData({...formData, min_experience: e.target.value})}
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />

                <input
                  type="text"
                  placeholder="Education Requirements (comma-separated)"
                  value={formData.education_requirements}
                  onChange={(e) => setFormData({...formData, education_requirements: e.target.value})}
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />

                <input
                  type="text"
                  placeholder="Mandatory Certifications / Licenses (comma-separated)"
                  value={formData.mandatory_certifications}
                  onChange={(e) => setFormData({...formData, mandatory_certifications: e.target.value})}
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
                
                <input
                  type="text"
                  placeholder="Tags (comma-separated)"
                  value={formData.tags}
                  onChange={(e) => setFormData({...formData, tags: e.target.value})}
                  className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
                
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="rounded-xl bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    {editingJob ? 'Update' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={resetForm}
                    className="rounded-xl border border-gray-300 dark:border-slate-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {!showCreateForm && (
            <button
              type="button"
              onClick={openCreateForm}
              className="w-full rounded-xl border-2 border-dashed border-slate-600 px-5 py-4 text-sm font-medium text-slate-400 hover:border-blue-500 hover:text-blue-400 transition"
            >
              {initialDescription ? '+ Save Current Job Description' : '+ Create New Job'}
            </button>
          )}

          {/* Jobs List */}
          {loading ? (
            <div className="text-center py-12 text-slate-400">Loading jobs...</div>
          ) : error ? (
            <div className="rounded-xl border border-red-800 bg-red-950 p-4 text-sm text-red-300">
              {error}
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 text-slate-400">No saved jobs yet. Create one above!</div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.job_id}
                  className="rounded-2xl border border-slate-700 bg-slate-800 p-4 hover:border-slate-500 transition-all"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-white">{job.title}</h3>
                      <p className="mt-1 text-xs text-slate-400 line-clamp-2">
                        {job.description}
                      </p>
                      
                      {job.tags && job.tags.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {job.tags.map((tag, i) => (
                            <span
                              key={i}
                              className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-300"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          onSelectJob(job)
                          onClose()
                        }}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition"
                      >
                        Use
                      </button>
                      <button
                        type="button"
                        onClick={() => handleEdit(job)}
                        className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleClone(job.job_id)}
                        className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                      >
                        Clone
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(job.job_id, job.title)}
                        className="rounded-lg border border-red-800 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-950 hover:text-red-300 transition"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
