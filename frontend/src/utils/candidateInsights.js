export const HIRING_STAGE_OPTIONS = [
  'New',
  'Screening',
  'Phone Screen',
  'Interview',
  'Technical Round',
  'Offer',
  'Hired',
  'On Hold',
  'Rejected',
]

export function getCandidateId(candidate) {
  if (candidate?.candidate_id) return candidate.candidate_id
  return `${candidate.filename}-${candidate.candidate_index || 0}`
}

export function getCandidateStage(candidate) {
  return candidate.status || 'New'
}

export function isCandidateRejected(candidate) {
  return (
    candidate.shortlist_verdict === 'Reject' ||
    getCandidateStage(candidate) === 'Rejected'
  )
}

export function getRejectionExplanation(candidate) {
  const reasons = []

  if ((candidate.non_negotiable_reasons?.length ?? 0) > 0) {
    reasons.push(...candidate.non_negotiable_reasons.map((reason) => reason.toLowerCase()))
  }

  if (candidate._rule_note) {
    reasons.push(candidate._rule_note.toLowerCase())
  }

  if ((candidate.critical_missing_skills?.length ?? 0) > 0) {
    const skills = candidate.critical_missing_skills.slice(0, 4).join(', ')
    const more = candidate.critical_missing_skills.length > 4
      ? ` and ${candidate.critical_missing_skills.length - 4} more`
      : ''
    reasons.push(`the resume is missing critical JD requirements: ${skills}${more}`)
  }

  if ((candidate.required_skill_score ?? 0) < 50) {
    reasons.push(`required skill coverage is low at ${candidate.required_skill_score}%`)
  }

  if (candidate.experience_meets_requirement === false) {
    reasons.push('detected experience appears below the JD minimum')
  }

  if ((candidate.skill_support_score ?? 0) < 45) {
    reasons.push(`claimed skills are not strongly backed by evidence (${candidate.skill_support_score} evidence score)`)
  }

  if ((candidate.ats_score ?? 0) < 60) {
    reasons.push(`ATS formatting/keyword readiness is weak (${candidate.ats_score} ATS score)`)
  }

  if ((candidate.keyword_missing_count ?? 0) > 0) {
    reasons.push(`${candidate.keyword_missing_count} important JD keyword${candidate.keyword_missing_count === 1 ? ' is' : 's are'} missing`)
  }

  if (candidate.education_meets_requirement === false) {
    reasons.push('the required education or certification is not clearly evidenced')
  }

  if ((candidate.red_flags?.length ?? 0) > 0) {
    reasons.push(`recruiter risk flags were detected: ${candidate.red_flags.slice(0, 2).join(', ')}`)
  }

  if (reasons.length === 0) {
    reasons.push('the overall match is below the recruiter threshold for this job')
  }

  return reasons.slice(0, 4)
}
