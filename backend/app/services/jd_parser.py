import re
from app.services.extractor import extract_skills_from_text, normalize_skill


REQUIRED_PATTERNS = [
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?required(?:\s+skills?)?\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?must have\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?mandatory\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?essential\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?minimum qualifications\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?basic qualifications\b",
]

PREFERRED_PATTERNS = [
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?preferred(?:\s+skills?|\s+qualifications)?\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?good to have\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?most preferred\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?plus\b",
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?preferred qualifications\b",
]

NICE_TO_HAVE_PATTERNS = [
    r"^(?:[•*\-]\s*|[a-zA-Z]\s+)?nice to have\b",
]

EDUCATION_PATTERNS = [
    r"\bbachelor(?:'s)?\b",
    r"\bmaster(?:'s)?\b",
    r"\bm\.?tech\b",
    r"\bb\.?tech\b",
    r"\bbe\b",
    r"\bbsc\b",
    r"\bmsc\b",
    r"\bphd\b",
    r"\bcomputer science\b",
    r"\binformation technology\b",
    r"\bengineering\b",
    r"\bmechanical\b",
    r"\baerospace\b",
    r"\belectrical\b",
    r"\belectronics\b",
]

def split_jd_lines(job_description: str) -> list[str]:
    return [line.strip() for line in job_description.splitlines() if line.strip()]


def _extract_after_colon(line: str) -> str:
    if ":" not in line:
        return ""
    return line.split(":", 1)[1].strip()


def _is_nested_letter_sub_bullet(line: str) -> bool:
    return re.match(r"^[a-zA-Z]\s+", line.strip()) is not None


def _looks_like_required_group_intro(line: str) -> bool:
    return re.search(
        r"listed below|programming languages|frameworks|languages listed|languages and frameworks",
        line.lower(),
    ) is not None


def _looks_like_example_group(line: str) -> bool:
    return re.search(r"\bsuch as\b|\be\.g\.\b|\bfor example\b", line.lower()) is not None


def classify_jd_line(line: str) -> str:
    lower_line = line.lower()

    for pattern in REQUIRED_PATTERNS:
        if re.search(pattern, lower_line):
            return "required_header"

    for pattern in PREFERRED_PATTERNS:
        if re.search(pattern, lower_line):
            return "preferred_header"

    for pattern in NICE_TO_HAVE_PATTERNS:
        if re.search(pattern, lower_line):
            return "nice_to_have_header"

    return "content"


def extract_experience_requirements(job_description: str) -> dict:
    """Parse experience requirements from a JD and return min/max bounds.

    Handles:
      - Range:       "3-8 years", "3 to 8 years", "3–8 years of experience"
      - Minimum:     "5+ years", "minimum 3 years", "at least 4 years"
      - Plain:       "5 years of experience"
      - Approximate: "~3 years", "around 2 years"

    For a range (e.g. "3-8 years"), min_years_experience = 3, max_years_experience = 8.
    For a plain/minimum value, max_years_experience = None (no upper bound).
    """
    text = job_description.lower()

    # ── Range patterns (capture both ends) ──────────────────────────────────
    range_patterns = [
        # "3-8 years", "3–8 years of experience", "~3-8 yrs"
        re.compile(r"~?\s*(\d+)\s*[-–—to]+\s*(\d+)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE),
    ]

    # ── Single-value patterns ────────────────────────────────────────────────
    single_patterns = [
        # "5+ years of experience", "5 years experience"
        re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+)?(?:work\s+)?experience", re.IGNORECASE),
        # "minimum 3 years", "at least 4 years", "min. 3 years"
        re.compile(r"(?:minimum|min\.?|at\s+least|at\s+minimum)\s+(\d+)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE),
        # "experience of 5 years", "experience of over 5 years"
        re.compile(r"experience\s+(?:of\s+)?(?:over\s+|more\s+than\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE),
        # "over 5 years", "more than 3 years", "~5 years"
        re.compile(r"(?:over|more\s+than|~|around|approximately)\s+(\d+)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE),
        # plain "5 years"
        re.compile(r"(?<!\d)(\d+)\s*\+?\s*(?:years?|yrs?)(?!\s*[-–—]\s*\d)", re.IGNORECASE),
    ]

    # Try range patterns first
    for p in range_patterns:
        m = p.search(text)
        if m:
            lo = int(m.group(1))
            hi = int(m.group(2))
            if lo > hi:
                lo, hi = hi, lo
            if 0 < lo <= 50 and 0 < hi <= 50:
                return {
                    "min_years_experience": lo,
                    "max_years_experience": hi,
                }

    # Fall back to single-value patterns (first match wins)
    for p in single_patterns:
        m = p.search(text)
        if m:
            val = int(m.group(1))
            if 0 < val <= 50:
                return {
                    "min_years_experience": val,
                    "max_years_experience": None,
                }

    return {
        "min_years_experience": None,
        "max_years_experience": None,
    }


def extract_education_requirements(job_description: str) -> list[str]:
    lower_text = job_description.lower()
    found = set()

    for pattern in EDUCATION_PATTERNS:
        matches = re.findall(pattern, lower_text)
        for match in matches:
            found.add(match.lower())

    return sorted(found)


def extract_seniority_level(job_description: str) -> str:
    """
    Infer role seniority level from JD text.
    Returns: 'junior' | 'mid' | 'senior' | 'lead'
    """
    text = job_description.lower()

    lead_signals = [r'\bteam lead\b', r'\btech lead\b', r'\btechnical lead\b', r'\bengineering manager\b', r'\bmanager\b']
    senior_signals = [r'\bsenior\b', r'\bsr\b', r'\bstaff engineer\b', r'\bprincipal\b', r'\barchitect\b', r'\bdirector\b']
    junior_signals = [r'\bjunior\b', r'\bjr\b', r'\bentry.level\b', r'\bfresher\b', r'\b0.1 year\b', r'\brecent graduate\b', r'\bnew grad\b', r'\btrainee\b']

    if any(re.search(kw, text) for kw in lead_signals):
        return 'lead'
    if any(re.search(kw, text) for kw in senior_signals):
        return 'senior'
    if any(re.search(kw, text) for kw in junior_signals):
        return 'junior'
    return 'mid'


def parse_jd_requirements(job_description: str, domain_name: str | None = None) -> dict:
    lines = split_jd_lines(job_description)

    required_lines = []
    preferred_lines = []
    general_lines = []
    required_skill_groups: list[list[str]] = []
    _next_group_is_one_of = False
    has_explicit_required_section = False
    has_explicit_preferred_section = False

    current_mode = "general"

    for line in lines:
        line_type = classify_jd_line(line)
        inline_text = _extract_after_colon(line)
        is_nested_sub_bullet = _is_nested_letter_sub_bullet(line)

        if line_type == "required_header":
            current_mode = "required"
            has_explicit_required_section = True
            # Extract any skills listed inline after a colon on the same line
            # e.g. "Required Skills: Java, Kafka, Docker" — don't discard the skills part
            if inline_text:
                required_lines.append(inline_text)
            continue
        elif line_type == "preferred_header":
            # Nested lines such as "o Most preferred: ..." often sit inside a
            # larger "Must have" section. Keep them attached to the required
            # block so later bullets are not downgraded into preferred/general.
            if current_mode == "required" and required_lines:
                last_required = required_lines[-1]
                if _looks_like_required_group_intro(last_required) or _next_group_is_one_of or is_nested_sub_bullet:
                    if inline_text:
                        required_lines.append(inline_text)
                        if _next_group_is_one_of or _looks_like_required_group_intro(last_required):
                            group_skills = [
                                normalize_skill(skill, domain_name)
                                for skill in extract_skills_from_text(inline_text, domain_name)
                            ]
                            if group_skills:
                                required_skill_groups.append(sorted(set(group_skills)))
                                _next_group_is_one_of = False
                    continue

            current_mode = "preferred"
            has_explicit_preferred_section = True
            if inline_text:
                preferred_lines.append(inline_text)
            continue
        elif line_type == "nice_to_have_header":
            if current_mode == "required" and is_nested_sub_bullet:
                if inline_text:
                    preferred_lines.append(inline_text)
                continue
            current_mode = "general"
            if inline_text:
                general_lines.append(inline_text)
            continue

        if current_mode == "required":
            # Detect a cue that the next bulleted list is an "one-of" group
            if re.search(r"at least one|one of the|any of the following|any of these", line.lower()):
                _next_group_is_one_of = True
            if _looks_like_example_group(line):
                group_skills = [
                    normalize_skill(skill, domain_name)
                    for skill in extract_skills_from_text(line, domain_name)
                ]
                required_lines.append(line)
                if group_skills:
                    required_skill_groups.append(sorted(set(group_skills)))
                continue
            # If the previous line set the next list as a one-of group and this
            # line looks like the inline list (commas or 'and'), capture it as
            # a group and reset the flag.
            if _next_group_is_one_of and ("," in line or " and " in line):
                # Extract skills from this line and add as a group
                group_skills = [normalize_skill(s, domain_name) for s in extract_skills_from_text(line, domain_name)]
                if group_skills:
                    required_skill_groups.append(sorted(set(group_skills)))
                    _next_group_is_one_of = False
                else:
                    required_lines.append(line)
            else:
                required_lines.append(line)
        elif current_mode == "preferred":
            preferred_lines.append(line)
        else:
            general_lines.append(line)

    required_text = "\n".join(required_lines)
    preferred_text = "\n".join(preferred_lines)
    general_text = "\n".join(general_lines)

    required_skills = [normalize_skill(skill, domain_name) for skill in extract_skills_from_text(required_text, domain_name)]
    preferred_skills = [normalize_skill(skill, domain_name) for skill in extract_skills_from_text(preferred_text, domain_name)]
    general_skills = [normalize_skill(skill, domain_name) for skill in extract_skills_from_text(general_text, domain_name)]

    all_jd_skills = sorted(set(required_skills + preferred_skills + general_skills))

    if not all_jd_skills:
        fallback_skills = [
            normalize_skill(skill, domain_name)
            for skill in extract_skills_from_text(job_description, domain_name)
        ]
        general_skills = sorted(set(fallback_skills))
        all_jd_skills = sorted(set(general_skills))

    return {
        "required_skills": sorted(set(required_skills)),
        "preferred_skills": sorted(set(preferred_skills)),
        "general_skills": sorted(set(general_skills)),
        "required_skill_groups": required_skill_groups,
        "all_jd_skills": all_jd_skills,
        "experience_requirements": extract_experience_requirements(job_description),
        "education_requirements": extract_education_requirements(job_description),
        "seniority_level": extract_seniority_level(job_description),
        "has_explicit_required_section": has_explicit_required_section,
        "has_explicit_preferred_section": has_explicit_preferred_section,
    }
