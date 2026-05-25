function normalizeJobDescription(text = '') {
  return text
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\r/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
 
function looksLikeRealCode(text) {
  const lowered = text.toLowerCase()
 
  const patterns = [
    /<script\b/,
    /<\/script>/,
    /function\s+\w+\s*\(/,
    /const\s+\w+\s*=/,
    /let\s+\w+\s*=/,
    /var\s+\w+\s*=/,
    /document\./,
    /window\./,
    /console\.log/,
    /import\s+.+\s+from\s+['"]/,
    /export\s+default/,
    /def\s+\w+\s*\(/,
    /class\s+\w+\s*[:(]/,
    /public\s+static\s+void\s+main/,
    /#include\s*</,
  ]
 
  let matches = 0
  for (const pattern of patterns) {
    if (pattern.test(lowered)) matches += 1
  }
 
  return matches >= 2
}
 
function looksLikeJobDescription(text) {
  const lowered = text.toLowerCase()
 
  const jdHints = [
    'job description',
    'responsibilities',
    'requirements',
    'qualifications',
    'preferred qualifications',
    'skills',
    "what you'll do",
    'what you will do',
    'about the role',
    'experience',
    'education',
    'must have',
    'nice to have',
    'preferred',
    'role overview',
  ]
 
  const techTerms = [
    'python', 'java', 'c++', 'c#', '.net', 'sql', 'react', 'node.js',
    'machine learning', 'deep learning', 'nlp', 'llm', 'rag',
    'cfd', 'thermal analysis', 'heat transfer', 'embedded', 'firmware',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'api', 'fastapi',
  ]

  const roleTerms = [
    'engineer', 'developer', 'analyst', 'manager', 'architect', 'specialist',
    'intern', 'associate', 'lead', 'consultant', 'designer', 'administrator',
  ]
 
  const jdHintMatches = jdHints.filter((item) => lowered.includes(item)).length
  const techMatches = techTerms.filter((item) => lowered.includes(item)).length
  const roleMatches = roleTerms.filter((item) => lowered.includes(item)).length
  const bulletMatches = (text.match(/(•|\*|-)\s+\w+/g) || []).length
  const wordCount = text.split(/\s+/).filter(Boolean).length

  const conciseJdSignal =
    roleMatches >= 1 &&
    techMatches >= 1 &&
    (jdHintMatches >= 1 || lowered.includes('responsibil') || lowered.includes('requirement') || lowered.includes('qualification'))
 
  return (
    conciseJdSignal ||
    jdHintMatches >= 1 ||
    techMatches >= 3 ||
    bulletMatches >= 3 ||
    wordCount >= 80
  )
}
 
export function sanitizeJobDescriptionInput(value) {
  return normalizeJobDescription(value)
}
 
export function validateResumeFile(file) {
  if (!file) return 'Please upload a resume file.'
  const validExtensions = ['pdf', 'docx']
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!validExtensions.includes(ext)) {
    return 'Only PDF and DOCX resumes are supported.'
  }
  return ''
}
 
export function validateJobDescriptionInput(value) {
  const cleaned = normalizeJobDescription(value)
 
  if (!cleaned) {
    return 'Please paste a job description first.'
  }
 
  if (looksLikeRealCode(cleaned) && !looksLikeJobDescription(cleaned)) {
    return 'The pasted content looks like code or script text, not a job description.'
  }

  const wordCount = cleaned.split(/\s+/).filter(Boolean).length
  if (wordCount < 20 && !looksLikeJobDescription(cleaned)) {
    return 'The job description looks too short. Please paste a fuller JD.'
  }
 
  if (!looksLikeJobDescription(cleaned)) {
    return 'The pasted content does not look enough like a job description yet.'
  }
 
  return ''
}
 