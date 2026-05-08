"""
Certification Coverage Analyzer
================================
Answers: "Does the candidate hold any certificate relevant to the skills
required / preferred by this JD?"

Approach
--------
1. Extract all certification lines from the resume (certifications section +
   any line containing known credential keywords across the full resume text).
2. For each JD required/preferred skill, check whether one or more extracted
   cert lines relate to that skill.
3. Return a structured report with:
   - `certs_found`   — de-duplicated list of cert/credential lines
   - `jd_skill_cert_map` — per-JD-skill: matched cert lines (or empty list)
   - `covered_skills` — JD skills that have at least one cert
   - `uncovered_skills` — JD skills with no cert evidence
   - `coverage_pct`  — % of JD skills with cert support (informational only)
"""

import re
from typing import NamedTuple


# ── Cert line detection ────────────────────────────────────────────────────────

_CERT_TRIGGER = re.compile(
    r"\b(certificat(?:e|ion|ed)|certified|certification|"
    r"aws\s+certif|azure\s+certif|google\s+cloud\s+certif|"
    r"gcp\s+certif|comptia|cisco|ccna|ccnp|ccie|"
    r"pmp|scrum|agile\s+certif|prince2|six\s+sigma|"
    r"tensorflow\s+certif|coursera|udemy|edx|"
    r"microsoft\s+certified|oracle\s+certified|"
    r"red\s*hat|rhce|rhcsa|linux\s+certif|"
    r"az-\d{3}|dp-\d{3}|ai-\d{3}|sc-\d{3}|"
    r"aws\s+saa|aws\s+sap|aws\s+dva|aws\s+sol|aws\s+mls|aws\s+acp|"
    r"professional\s+certif|associate\s+certif)\b",
    re.IGNORECASE,
)

_HEADING_LIKE = re.compile(
    r"^(certifications?|certificates?|credentials?|licenses?|"
    r"professional\s+certifications?|achievements?)\s*[:\-–]?\s*$",
    re.IGNORECASE,
)


def _extract_cert_lines(resume_text: str, certifications_section: str) -> list[str]:
    """
    Return a de-duplicated list of lines that look like certification entries.
    Priority: dedicated certifications section first, then scan full resume.
    """
    seen: set[str] = set()
    results: list[str] = []

    def _add(line: str) -> None:
        cleaned = re.sub(r"\s+", " ", line).strip()
        # strip bullet/dash prefix
        cleaned = re.sub(r"^[\-•*▪◦●>]+\s*", "", cleaned).strip()
        if not cleaned or len(cleaned) < 6:
            return
        norm = cleaned.lower()
        if norm not in seen:
            seen.add(norm)
            results.append(cleaned)

    # From the certifications section
    for line in certifications_section.splitlines():
        stripped = line.strip()
        if not stripped or _HEADING_LIKE.match(stripped):
            continue
        _add(stripped)

    # Full resume scan (only lines that contain a known cert keyword)
    for line in resume_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _CERT_TRIGGER.search(stripped):
            # Skip very long lines (likely prose descriptions, not cert entries)
            if len(stripped) <= 200:
                _add(stripped)

    return results


# ── Skill → cert keyword mapping ───────────────────────────────────────────────
# For each canonical skill we list regex fragments that plausibly appear in a
# cert name when that cert is relevant.  Only loosely coupled — we never claim
# a cert proves the skill; we surface it so the recruiter can verify.

_SKILL_CERT_HINTS: dict[str, list[str]] = {
    # Cloud
    "aws":          [r"aws", r"amazon web services", r"cloud practitioner", r"solutions architect",
                     r"developer\s+associate", r"sysops", r"devops\s+engineer", r"machine learning\s+specialty"],
    "azure":        [r"azure", r"microsoft certified", r"az-\d{3}"],
    "gcp":          [r"gcp", r"google cloud", r"associate cloud engineer", r"professional cloud"],
    "google cloud": [r"gcp", r"google cloud"],
    "docker":       [r"docker", r"container"],
    "kubernetes":   [r"kubernetes", r"cka", r"ckad", r"cks"],
    "linux":        [r"linux", r"rhce", r"rhcsa", r"lpic", r"comptia linux"],
    # Data / ML
    "machine learning": [r"machine learning", r"aws\s+mls", r"tensorflow\s+developer",
                          r"professional data\s+scientist", r"databricks"],
    "deep learning":    [r"deep learning", r"tensorflow", r"pytorch", r"neural"],
    "tensorflow":       [r"tensorflow"],
    "data science":     [r"data scientist", r"data science", r"ibm\s+data"],
    "python":           [r"python\s+certif", r"pcep", r"pcap"],
    "sql":              [r"sql\s+certif", r"oracle\s+(database|certified)", r"microsoft\s+(sql|data)"],
    "databricks":       [r"databricks"],
    # Networking / Security
    "networking":       [r"ccna", r"ccnp", r"ccie", r"comptia network"],
    "security":         [r"cissp", r"ceh", r"comptia security", r"sc-\d{3}", r"sscp", r"cism"],
    "cloud security":   [r"cissp", r"ccsp", r"sc-\d{3}", r"aws security"],
    # Dev / DevOps
    "devops":           [r"devops", r"aws devops", r"azure devops", r"cka", r"docker"],
    "ci/cd":            [r"devops", r"jenkins certif", r"gitlab certif"],
    "terraform":        [r"terraform\s+certif", r"hashicorp"],
    "git":              [r"git\s+certif"],
    # PM / Agile
    "agile":            [r"scrum", r"pmp", r"csm", r"psm", r"safe\s+(agilist|practitioner)", r"prince2"],
    "project management": [r"pmp", r"prince2", r"pmi", r"scrum"],
    # Generative AI / LLMs
    "generative ai":    [r"generative ai", r"llm", r"aws\s+certif.*ai", r"azure\s+ai"],
    "nlp":              [r"nlp\s+certif", r"tensorflow\s+developer"],
    # Java / Spring
    "java":             [r"oracle\s+certified.*java", r"ocajp", r"ocpjp", r"ocp\s+java"],
    "spring":           [r"spring\s+certif", r"vmware\s+spring"],
    # JavaScript
    "node.js":          [r"node.*certif"],
    # BI / Analytics
    "power bi":         [r"power bi", r"microsoft\s+certified.*power"],
    "tableau":          [r"tableau\s+certif", r"tableau\s+desktop"],
    # Testing
    "selenium":         [r"selenium\s+certif"],
    "testing":          [r"istqb", r"ctfl", r"cste", r"test\s+certif"],
}


def _skill_matches_cert(skill: str, cert_line: str) -> bool:
    """Return True if cert_line plausibly references a cert for `skill`."""
    lower_skill = skill.lower().strip()
    lower_cert = cert_line.lower()

    # First try the curated mapping
    hints = _SKILL_CERT_HINTS.get(lower_skill, [])
    for hint in hints:
        if re.search(hint, lower_cert, re.IGNORECASE):
            return True

    # Generic fallback: the skill keyword itself appears in the cert line
    # Only trigger this if the cert line is "short" (looks like a cert entry,
    # not a job description sentence that happens to mention the skill).
    if len(cert_line) <= 120:
        # escape the skill for regex use
        escaped = re.escape(lower_skill)
        if re.search(rf"\b{escaped}\b", lower_cert):
            return True

    return False


# ── Public API ─────────────────────────────────────────────────────────────────

def build_certification_coverage_report(
    jd_required_skills: list[str],
    jd_preferred_skills: list[str],
    resume_sections: dict[str, str],
    raw_resume_text: str,
) -> dict:
    """
    Build a certification-vs-JD-skills coverage report.

    Returns
    -------
    {
      "certs_found": [...],              # all cert lines extracted from resume
      "jd_skill_cert_map": {            # per JD skill → list of cert lines
        "aws": ["AWS Certified Solutions Architect – Associate"],
        "python": [],
        ...
      },
      "covered_skills": [...],          # skills with at least one cert
      "uncovered_skills": [...],        # skills with no cert evidence
      "coverage_pct": 42,               # int, 0-100
      "has_any_certs": True | False,
    }
    """
    certifications_section = resume_sections.get("certifications", "")
    certs_found = _extract_cert_lines(raw_resume_text, certifications_section)

    # Combine required + preferred, deduplicate, keep order
    jd_skills_seen: set[str] = set()
    jd_skills: list[str] = []
    for skill in jd_required_skills + jd_preferred_skills:
        norm = skill.lower().strip()
        if norm and norm not in jd_skills_seen:
            jd_skills_seen.add(norm)
            jd_skills.append(skill)

    skill_cert_map: dict[str, list[str]] = {}
    for skill in jd_skills:
        matched = [c for c in certs_found if _skill_matches_cert(skill, c)]
        skill_cert_map[skill] = matched

    covered = [s for s, certs in skill_cert_map.items() if certs]
    uncovered = [s for s, certs in skill_cert_map.items() if not certs]

    total = len(jd_skills)
    coverage_pct = round(len(covered) * 100 / total) if total > 0 else 0

    return {
        "certs_found": certs_found,
        "jd_skill_cert_map": skill_cert_map,
        "covered_skills": covered,
        "uncovered_skills": uncovered,
        "coverage_pct": coverage_pct,
        "has_any_certs": len(certs_found) > 0,
    }
