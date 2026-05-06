import re
 
 
HTML_TAG_RE = re.compile(r"<[^>]+>")
 
SCRIPT_PATTERNS = [
    r"<script\b",
    r"</script>",
    r"function\s+\w+\s*\(",
    r"const\s+\w+\s*=",
    r"let\s+\w+\s*=",
    r"var\s+\w+\s*=",
    r"document\.",
    r"window\.",
    r"console\.log",
    r"import\s+.+\s+from\s+['\"]",
    r"export\s+default",
    r"def\s+\w+\s*\(",
    r"class\s+\w+\s*[:\(]",
    r"public\s+static\s+void\s+main",
    r"#include\s*<",
]
 
JD_HINT_PATTERNS = [
    r"job description",
    r"responsibilities",
    r"requirements",
    r"qualifications",
    r"preferred qualifications",
    r"skills",
    r"what you'll do",
    r"what you will do",
    r"about the role",
    r"experience",
    r"education",
    r"must have",
    r"nice to have",
    r"preferred",
    r"role overview",
]
 
TECH_JD_TERMS = [
    "python", "java", "c++", "c#", ".net", "sql", "react", "node.js",
    "machine learning", "deep learning", "nlp", "llm", "rag",
    "cfd", "thermal analysis", "heat transfer", "embedded", "firmware",
    "aws", "azure", "gcp", "docker", "kubernetes", "api", "fastapi",
]
 
 
def clean_jd_text(text: str) -> str:
    if not text:
        return ""
 
    cleaned = text.replace("&nbsp;", " ")
    cleaned = cleaned.replace("&amp;", "&")
    cleaned = cleaned.replace("<br>", "\n").replace("<br/>", "\n").replace("</br>", "\n")
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\r", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
 
 
def _looks_like_real_code(text: str) -> bool:
    lowered = text.lower()
    matches = 0
 
    for pattern in SCRIPT_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            matches += 1
 
    return matches >= 2
 
 
def _looks_like_job_description(text: str) -> bool:
    lowered = text.lower()
 
    jd_hint_matches = sum(
        1 for pattern in JD_HINT_PATTERNS
        if re.search(pattern, lowered, flags=re.IGNORECASE)
    )
 
    tech_matches = sum(
        1 for term in TECH_JD_TERMS
        if term in lowered
    )
 
    bullet_like_lines = len(re.findall(r"(•|\*|-)\s+\w+", text))
 
    return (
        jd_hint_matches >= 1
        or tech_matches >= 3
        or bullet_like_lines >= 3
        or len(text.split()) >= 80
    )
 
 
def validate_job_description_input(job_description: str) -> str:
    cleaned = clean_jd_text(job_description)
 
    if not cleaned:
        raise ValueError("Please paste a job description first.")
 
    if len(cleaned.split()) < 35:
        raise ValueError("The job description looks too short. Please paste a fuller JD.")
 
    if _looks_like_real_code(cleaned) and not _looks_like_job_description(cleaned):
        raise ValueError(
            "The pasted content looks like code or script text, not a job description. "
            "Please paste the actual JD content."
        )
 
    if not _looks_like_job_description(cleaned):
        raise ValueError(
            "The pasted content does not look enough like a job description yet. "
            "Please paste responsibilities, requirements, qualifications, or skills sections."
        )
 
    return cleaned
 