import re

from app.services.career_analyzer import check_education_fit
from app.services.extractor import normalize_skill
from app.services.jd_parser import classify_jd_line, parse_jd_requirements, split_jd_lines


_CREDENTIAL_KEYWORDS = (
    "certification",
    "certifications",
    "certificate",
    "certified",
    "license",
    "licenses",
    "licence",
    "licensed",
    "registration",
    "registered",
)

_CERT_MANDATORY_PATTERNS = (
    r"\brequired\b",
    r"\bmandatory\b",
    r"\bmust\s*have\b",
    r"\bmust\s*be\b",
    r"\bessential\b",
    r"\bminimum\s+qualification(?:s)?\b",
)

_CERT_OPTIONAL_PATTERNS = (
    r"\bpreferred\b",
    r"\bgood\s+to\s+have\b",
    r"\bnice\s+to\s+have\b",
    r"\boptional\b",
    r"\bplus\b",
    r"\bnot\s+required\b",
)


def _normalize_phrase(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[\.\-_,;:()\[\]/]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains_phrase(haystack: str, needle: str) -> bool:
    normalized_needle = _normalize_phrase(needle)
    if not normalized_needle:
        return False
    return normalized_needle in _normalize_phrase(haystack)


def _resume_certification_text(analysis: dict) -> str:
    sections = analysis.get("resume_sections", {})
    chunks = [
        sections.get("certifications", ""),
        sections.get("education", ""),
        sections.get("summary", ""),
        analysis.get("raw_resume_text", ""),
    ]
    return "\n".join(chunk for chunk in chunks if chunk)


def _extract_explicit_required_credentials(job_description: str) -> list[str]:
    credentials: list[str] = []

    for line in split_jd_lines(job_description):
        lowered = line.lower()
        if not any(keyword in lowered for keyword in _CREDENTIAL_KEYWORDS):
            continue

        if any(re.search(pattern, lowered) for pattern in _CERT_OPTIONAL_PATTERNS):
            continue

        if not any(re.search(pattern, lowered) for pattern in _CERT_MANDATORY_PATTERNS):
            continue

        credentials.append(line.strip())

    return credentials


def _evaluate_required_skills(
    analysis: dict,
    required_skills: list[str],
    required_skill_groups: list[list[str]] | None,
    domain_name: str | None,
    hard_fail: bool,
) -> tuple[list[str], list[str]]:
    hard_reject_reasons: list[str] = []
    review_flags: list[str] = []

    if not required_skills:
        return hard_reject_reasons, review_flags

    resume_skill_set = {
        normalize_skill(skill, domain_name)
        for skill in analysis.get("resume_skills", [])
    }
    normalized_groups = [
        [normalize_skill(skill, domain_name) for skill in group if skill]
        for group in (required_skill_groups or [])
        if group
    ]
    grouped_skills = {skill for group in normalized_groups for skill in group}

    missing = []
    for skill in required_skills:
        normalized = normalize_skill(skill, domain_name)
        if normalized in grouped_skills:
            continue
        if normalized not in resume_skill_set:
            missing.append(skill)

    missing_groups = []
    for group in normalized_groups:
        if not any(skill in resume_skill_set for skill in group):
            missing_groups.append(group)

    if not missing and not missing_groups:
        return hard_reject_reasons, review_flags

    messages = []
    if missing:
        reason = (
            "Missing required skill"
            if len(missing) == 1
            else "Missing required skills"
        )
        messages.append(f"{reason}: {', '.join(missing[:6])}")
    for group in missing_groups:
        preview = ", ".join(group[:4])
        suffix = ", ..." if len(group) > 4 else ""
        messages.append(f"Missing at least one required skill from group ({preview}{suffix})")

    for message in messages:
        if hard_fail:
            hard_reject_reasons.append(message)
        else:
            review_flags.append(message + " — verify whether equivalent experience is present under different wording.")

    return hard_reject_reasons, review_flags


def _evaluate_min_experience(
    analysis: dict,
    min_experience: int | None,
    hard_fail: bool,
) -> tuple[list[str], list[str]]:
    hard_reject_reasons: list[str] = []
    review_flags: list[str] = []

    if min_experience is None:
        return hard_reject_reasons, review_flags

    estimated = analysis.get("experience_estimate", {}).get("estimated_years")
    if estimated is None:
        review_flags.append(
            f"Minimum experience is {min_experience}y, but resume dates were not clear enough to verify automatically."
        )
        return hard_reject_reasons, review_flags

    if estimated >= min_experience:
        return hard_reject_reasons, review_flags

    message = f"Estimated experience {estimated}y is below the required minimum of {min_experience}y."
    if hard_fail:
        hard_reject_reasons.append(message)
    else:
        review_flags.append(message + " Review manually before screening out.")

    return hard_reject_reasons, review_flags


def _education_is_confidently_missing(analysis: dict) -> bool:
    sections = analysis.get("resume_sections", {})
    education_text = (sections.get("education") or "").strip()
    certifications_text = (sections.get("certifications") or "").strip()
    return len(education_text) >= 20 or len(certifications_text) >= 20


def _evaluate_education(
    analysis: dict,
    education_requirements: list[str],
    hard_fail: bool,
) -> tuple[list[str], list[str]]:
    hard_reject_reasons: list[str] = []
    review_flags: list[str] = []

    if not education_requirements:
        return hard_reject_reasons, review_flags

    result = check_education_fit(analysis.get("resume_sections", {}), education_requirements)
    if result.get("meets_requirement") is True:
        return hard_reject_reasons, review_flags

    message = (
        "Required education not clearly evidenced: "
        + ", ".join(education_requirements[:4])
    )
    if hard_fail and _education_is_confidently_missing(analysis):
        hard_reject_reasons.append(message)
    else:
        review_flags.append(message + " — verify manually before making a final decision.")

    return hard_reject_reasons, review_flags


def _evaluate_certifications(
    analysis: dict,
    mandatory_certifications: list[str],
    hard_fail: bool,
) -> tuple[list[str], list[str]]:
    hard_reject_reasons: list[str] = []
    review_flags: list[str] = []

    if not mandatory_certifications:
        return hard_reject_reasons, review_flags

    cert_text = _resume_certification_text(analysis)
    missing = [
        requirement for requirement in mandatory_certifications
        if not _contains_phrase(cert_text, requirement)
    ]

    if not missing:
        return hard_reject_reasons, review_flags

    message = (
        "Required certification/license not evidenced: "
        + "; ".join(missing[:4])
    )
    if hard_fail:
        hard_reject_reasons.append(message)
    else:
        review_flags.append(message + " — JD appears to mention this explicitly, but resume evidence is unclear.")

    return hard_reject_reasons, review_flags


def _extract_academic_marks(edu_text: str) -> dict:
    """Extract simple numeric marks for 10th, 12th and bachelor if present.

    Returns percents as floats when possible, keys: '10', '12', 'btech'.
    """
    text = edu_text.lower()
    marks = {}

    # percent like 85% or 85.5%
    for level_keywords, key in [
        (r'(?:10th|class\s*10|ssc|secondary)', '10'),
        (r'(?:12th|class\s*12|hsc|senior\s*secondary)', '12'),
        (r'(?:b\.tech|btech|bachelor|b\.e|be\b)', 'btech'),
    ]:
        # search for nearby percentage or cgpa
        pattern_percent = rf'({level_keywords}).{{0,60}}?(\d{{1,2}}(?:\.\d+)?\s*%)'
        m = re.search(pattern_percent, text, re.IGNORECASE)
        if m:
            try:
                marks[key] = float(m.group(2).replace('%', '').strip())
                continue
            except Exception:
                pass

        # cgpa patterns like 8.5/10 or 3.6/4 or 8.5 cgpa
        pattern_cgpa = rf'({level_keywords}).{{0,60}}?(\d(?:\.\d+)?)(?:\s*/\s*(\d(?:\.\d+)?))?\s*(?:cgpa|grade|gpa)?'
        m2 = re.search(pattern_cgpa, text, re.IGNORECASE)
        if m2:
            try:
                val = float(m2.group(2))
                denom = m2.group(3)
                if denom:
                    denom_f = float(denom)
                    # convert to percent
                    if denom_f > 4:
                        # assume scale 100: already percent
                        percent = (val / denom_f) * 100
                    else:
                        percent = (val / denom_f) * 100
                else:
                    # assume CGPA out of 10
                    percent = val * 10 if val <= 10 else val
                marks[key] = float(round(percent, 2))
            except Exception:
                pass

    return marks


def _evaluate_academic_marks(
    analysis: dict,
    min_marks: dict,
    hard_fail: bool,
) -> tuple[list[str], list[str]]:
    """Evaluate 10th/12th/btech marks against provided minimums.

    min_marks: dict with optional keys 'min_10_marks','min_12_marks','min_btech_marks' (percent floats)
    """
    hard_reject_reasons: list[str] = []
    review_flags: list[str] = []

    if not min_marks:
        return hard_reject_reasons, review_flags

    sections = analysis.get("resume_sections", {})
    edu_text = ' '.join([
        sections.get('education', ''),
        sections.get('summary', ''),
        sections.get('other', ''),
        analysis.get('raw_resume_text', ''),
    ])

    extracted = _extract_academic_marks(edu_text)

    mapping = [
        ('min_10_marks', '10', "10th/SSC"),
        ('min_12_marks', '12', "12th/HSC"),
        ('min_btech_marks', 'btech', "B.Tech/Bachelor") ,
    ]

    for cfg_key, extracted_key, label in mapping:
        if cfg_key not in min_marks or min_marks.get(cfg_key) is None:
            continue
        required = float(min_marks.get(cfg_key))
        found = extracted.get(extracted_key)
        if found is None:
            # can't verify
            review_flags.append(f"{label} minimum {required}% specified but not clearly found in resume.")
            continue
        if found < required:
            message = f"{label} marks {found}% are below required minimum of {required}%"
            if hard_fail:
                hard_reject_reasons.append(message)
            else:
                review_flags.append(message + " — verify manually before screening out.")

    return hard_reject_reasons, review_flags


def evaluate_non_negotiables(
    analysis: dict,
    job_description: str,
    saved_job: dict | None = None,
) -> dict:
    active_domain = (
        analysis.get("analysis_meta", {})
        .get("active_domain", {})
        .get("domain")
    )
    jd_info = parse_jd_requirements(job_description, active_domain)

    saved_required_skills = list((saved_job or {}).get("required_skills") or [])
    saved_education = list((saved_job or {}).get("education_requirements") or [])
    saved_certs = list((saved_job or {}).get("mandatory_certifications") or [])
    saved_min_experience = (saved_job or {}).get("min_experience")
    saved_min_10 = (saved_job or {}).get("min_10_marks")
    saved_min_12 = (saved_job or {}).get("min_12_marks")
    saved_min_btech = (saved_job or {}).get("min_btech_marks")

    fallback_required_skills = jd_info.get("required_skills", [])
    fallback_min_experience = jd_info.get("experience_requirements", {}).get("min_years_experience")
    fallback_education = jd_info.get("education_requirements", [])
    fallback_certs = _extract_explicit_required_credentials(job_description)
    explicit_required = jd_info.get("has_explicit_required_section", False)

    rules = {
        "source": "saved_job" if saved_job else "parsed_jd",
        "required_skills": saved_required_skills or fallback_required_skills,
        "required_skill_groups": [] if saved_job else jd_info.get("required_skill_groups", []),
        "min_experience": saved_min_experience if saved_job else fallback_min_experience,
        "education_requirements": saved_education or fallback_education,
        "min_academic_marks": {
            "min_10_marks": saved_min_10,
            "min_12_marks": saved_min_12,
            "min_btech_marks": saved_min_btech,
        },
        "mandatory_certifications": saved_certs or fallback_certs,
        "explicit_required_section": explicit_required,
    }

    hard_reject_reasons: list[str] = []
    review_flags: list[str] = []

    skill_hard_fail = bool(saved_job or explicit_required)
    exp_hard_fail = bool(saved_job or explicit_required)
    edu_hard_fail = bool(saved_job and saved_education)
    cert_hard_fail = bool(saved_job and saved_certs)
    acad_hard_fail = bool(saved_job and any([saved_min_10, saved_min_12, saved_min_btech]))

    for reasons, flags in [
        _evaluate_required_skills(
            analysis,
            rules["required_skills"],
            rules["required_skill_groups"],
            active_domain,
            skill_hard_fail,
        ),
        _evaluate_min_experience(analysis, rules["min_experience"], exp_hard_fail),
        _evaluate_education(analysis, rules["education_requirements"], edu_hard_fail),
        _evaluate_certifications(analysis, rules["mandatory_certifications"], cert_hard_fail),
        _evaluate_academic_marks(analysis, rules.get("min_academic_marks", {}), acad_hard_fail),
    ]:
        hard_reject_reasons.extend(reasons)
        review_flags.extend(flags)

    if hard_reject_reasons:
        verdict = "reject"
    elif review_flags:
        verdict = "review"
    else:
        verdict = "pass"

    return {
        "hard_reject": verdict == "reject",
        "hard_reject_reasons": hard_reject_reasons,
        "review_flags": review_flags,
        "non_negotiable_verdict": verdict,
        "evaluated_rules": rules,
    }
