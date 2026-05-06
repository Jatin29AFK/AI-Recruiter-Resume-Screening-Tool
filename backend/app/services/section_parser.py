import re


SECTION_PATTERNS = {
    "skills": [
        r"\bskills\b",
        r"\btechnical skills\b",
        r"\bcore competencies\b",
        r"\btech stack\b",
        r"\bkey skills\b",
        r"\barea of expertise\b",
        r"\btechnologies\b",
        r"\btools\b",
    ],
    "experience": [
        r"\bexperience\b",
        r"\bwork experience\b",
        r"\bprofessional experience\b",
        r"\bemployment history\b",
        r"\bwork history\b",
        r"\bcareer history\b",
        r"\bjob history\b",
        r"\bpositions held\b",
        r"\brelevant experience\b",
    ],
    "projects": [
        r"\bprojects\b",
        r"\bpersonal projects\b",
        r"\bacademic projects\b",
        r"\bkey projects\b",
        r"\bportfolio\b",
    ],
    "education": [
        r"\beducation\b",
        r"\bacademic background\b",
        r"\bqualifications\b",
        r"\bacademic qualifications\b",
        r"\bdegrees?\b",
        r"\beducational background\b",
        r"\bschooling\b",
    ],
    "certifications": [
        r"\bcertifications\b",
        r"\bcertificates\b",
        r"\blicenses\b",
        r"\bcredentials\b",
        r"\baccreditations\b",
    ],
    "summary": [
        r"\bsummary\b",
        r"\bprofessional summary\b",
        r"\bprofile\b",
        r"\bobjective\b",
        r"\bcareer objective\b",
        r"\babout\b",
        r"\bpersonal statement\b",
        r"\bexecutive summary\b",
    ],
}


INLINE_SECTION_PREFIXES = {
    "summary": [
        "profile summary",
        "professional summary",
        "executive summary",
        "career summary",
        "summary",
        "objective",
        "career objective",
        "about",
        "personal statement",
    ],
    "experience": [
        "work",
        "work experience",
        "professional experience",
        "experience",
        "employment history",
        "work history",
        "career history",
        "job history",
        "relevant experience",
    ],
    "education": [
        "education",
        "academic background",
        "qualifications",
        "academic qualifications",
        "degrees",
        "educational background",
        "schooling",
    ],
    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "key projects",
        "portfolio",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "tech stack",
        "key skills",
        "area of expertise",
        "technologies",
        "tools",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "credentials",
        "accreditations",
    ],
}


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())


def _looks_like_section_header(raw_line: str) -> bool:
    """
    Extra guard so content lines don't get mistaken for section headers.
    Real headers are: short, have no date ranges, no emails, no company dashes,
    no bullet markers, and contain no opening parentheses with years.
    """
    line = raw_line.strip()
    # Too long to be a plain section header
    if len(line) > 55:
        return False
    # Date ranges: "(Jan 2020 – Present)", "2020 – 2023", etc.
    if re.search(r'\d{4}', line):
        return False
    # Email or phone — definitely content, not a header
    if re.search(r'@|\+\d{2}|\(\d{3}\)', line):
        return False
    # Bullet points or list markers
    if re.match(r'^[\-•▪◦●*]', line):
        return False
    # Job-title style: "Something – Something" (em/en dash between words → company names)
    if re.search(r'\b\w+\s*[–—]\s*\w+', line):
        return False
    # URL-like content
    if re.search(r'https?://|www\.', line, re.IGNORECASE):
        return False
    return True


def detect_section_name(line: str) -> str | None:
    lowered = normalize_line(line)

    if lowered == "academic":
        return "projects"

    # Sidebar/table-style resumes often extract as:
    # "Education      Master of Technology..." or "Work      Data Scientist..."
    # Treat these as section starts even when the line is longer than a plain
    # heading, but require a clear label/content separator to avoid matching
    # normal sentences like "work with Python".
    if len(line.strip()) <= 180:
        raw = line.strip()
        for section, prefixes in INLINE_SECTION_PREFIXES.items():
            for prefix in sorted(prefixes, key=len, reverse=True):
                pattern = rf"^{re.escape(prefix)}(?:\s{{2,}}|[:|])"
                if re.match(pattern, raw, re.IGNORECASE):
                    return section

    # Inline-prefix check: "Skills: Python, SQL" → section=skills, content=rest.
    # Guard: only treat as a header if the line is short enough to be a heading
    # (avoids matching "Experienced engineer with 5 years..." as experience header)
    if len(line.strip()) <= 60:
        for section, prefixes in INLINE_SECTION_PREFIXES.items():
            for prefix in prefixes:
                # Require the prefix to match as a whole word at the start —
                # the char immediately after prefix must be end-of-string, space,
                # colon, dash or other non-alpha character (not "experienced" etc.)
                if lowered.startswith(prefix):
                    after = lowered[len(prefix):]
                    if not after or not after[0].isalpha():
                        return section

    if not _looks_like_section_header(line):
        return None

    normalized = lowered

    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return section

    return None


def _strip_inline_section_prefix(line: str, section: str) -> str:
    lowered = line.strip().lower()
    for prefix in INLINE_SECTION_PREFIXES.get(section, []):
        if lowered.startswith(prefix):
            remainder = line.strip()[len(prefix):].lstrip(" :-–—\t")
            return remainder.strip()
    return ""


def split_resume_into_sections(text: str) -> dict[str, str]:
    """
    Split resume text into likely sections using heading detection.
    """
    lines = text.splitlines()
    sections = {}
    current_section = "other"
    buffer = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        detected_section = detect_section_name(line)

        if detected_section:
            if buffer:
                existing_text = sections.get(current_section, "")
                combined = (existing_text + "\n" + "\n".join(buffer)).strip()
                sections[current_section] = combined
                buffer = []

            current_section = detected_section
            inline_content = _strip_inline_section_prefix(line, detected_section)
            if inline_content:
                buffer.append(inline_content)
        else:
            buffer.append(line)

    if buffer:
        existing_text = sections.get(current_section, "")
        combined = (existing_text + "\n" + "\n".join(buffer)).strip()
        sections[current_section] = combined

    return sections
