import re


EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"(\+?\d[\d\s\-\(\)]{8,}\d)"
LINKEDIN_REGEX = r"(https?://(?:www\.)?linkedin\.com/[^\s,;\"'<>]+|(?:www\.)?linkedin\.com/in/[^\s,;\"'<>]+)"
GITHUB_REGEX = r"(https?://(?:www\.)?github\.com/[^\s,;\"'<>]+|(?:www\.)?github\.com/[^\s,;\"'<>]+)"

_TRAILING_PUNCT = re.compile(r"[.,;\"'>\)\]]+$")


def get_non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_first_match(pattern: str, text: str, clean_url: bool = False) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    result = match.group(0).strip()
    if clean_url:
        result = _TRAILING_PUNCT.sub("", result)
    return result


def looks_like_contact_line(line: str) -> bool:
    lowered = line.lower()
    return (
        bool(re.search(EMAIL_REGEX, line))
        or bool(re.search(PHONE_REGEX, line))
        or "linkedin" in lowered
        or "github" in lowered
        or "@" in line
        or "http" in lowered
    )


def infer_name(lines: list[str]) -> str:
    if not lines:
        return ""

    first = lines[0].strip()
    if looks_like_contact_line(first):
        return ""

    return first


def infer_title(lines: list[str], inferred_name: str) -> str:
    for line in lines[1:6]:
        if line == inferred_name:
            continue
        if looks_like_contact_line(line):
            continue
        if len(line.split()) <= 12:
            return line.strip()
    return ""


def infer_location(lines: list[str]) -> str:
    for line in lines[:8]:
        lowered = line.lower()
        if looks_like_contact_line(line):
            continue
        if len(line) > 60:
            continue
        if "," in line or "india" in lowered:
            return line.strip()
    return ""


def is_bullet_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(("•", "*", "- "))


def clean_bullet_prefix(line: str) -> str:
    return line.strip().lstrip("•").lstrip("*").lstrip("-").strip()


def looks_like_date_line(line: str) -> bool:
    value = line.strip().lower()
    return bool(
        re.search(r"\b(19|20)\d{2}\b", value)
        or "present" in value
        or re.search(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
            value,
        )
    )


def looks_like_location_line(line: str) -> bool:
    value = line.strip()
    lowered = value.lower()
    if len(value) > 60:
        return False
    return (
        "," in value
        or "india" in lowered
        or any(city in lowered for city in ["noida", "pune", "gurugram", "bangalore", "hyderabad", "delhi", "punjab"])
    )


def looks_like_short_header(line: str) -> bool:
    value = line.strip()
    if not value or len(value) > 90:
        return False
    if value.endswith("."):
        return False
    if looks_like_date_line(value) or looks_like_location_line(value):
        return False
    if looks_like_contact_line(value):
        return False
    return True


def merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]

        should_merge = (
            not is_bullet_line(line)
            and not is_bullet_line(prev)
            and not looks_like_short_header(line)
            and not looks_like_date_line(line)
            and not looks_like_location_line(line)
            and not prev.endswith(".")
            and not prev.endswith(":")
        )

        if should_merge:
            merged[-1] = f"{prev} {line}".strip()
        else:
            merged.append(line)

    return merged


def split_section_into_bullets(text: str, section_name: str = "") -> list[str]:
    if not text:
        return []

    raw_lines = get_non_empty_lines(text)
    lines = merge_wrapped_lines(raw_lines)

    bullets = []
    pending_meta = []

    for line in lines:
        cleaned = clean_bullet_prefix(line)

        if not cleaned or looks_like_contact_line(cleaned):
            continue

        if looks_like_date_line(cleaned) or looks_like_location_line(cleaned):
            pending_meta.append(cleaned)
            continue

        if is_bullet_line(line):
            bullets.append(f"* {cleaned}")
            continue

        if looks_like_short_header(cleaned):
            if pending_meta:
                meta_suffix = " | ".join(pending_meta)
                bullets.append(f"– {cleaned} | {meta_suffix}")
                pending_meta = []
            else:
                bullets.append(f"– {cleaned}")
            continue

        bullets.append(f"* {cleaned}")

    cleaned_output = []
    for item in bullets:
        normalized = re.sub(r"\s+", " ", item).strip()
        if normalized and normalized not in cleaned_output:
            cleaned_output.append(normalized)

    return cleaned_output


def structure_resume_for_tailoring(analysis_result: dict) -> dict:
    resume_sections = analysis_result.get("resume_sections", {})
    resume_skills = analysis_result.get("resume_skills", [])
    raw_resume_text = analysis_result.get("raw_resume_text", "")

    summary_text = resume_sections.get("summary", "").strip()
    experience_text = resume_sections.get("experience", "").strip()
    projects_text = resume_sections.get("projects", "").strip()
    education_text = resume_sections.get("education", "").strip()
    certifications_text = resume_sections.get("certifications", "").strip()

    lines = get_non_empty_lines(raw_resume_text)

    full_name = infer_name(lines)
    current_title = infer_title(lines, full_name)
    email = extract_first_match(EMAIL_REGEX, raw_resume_text)
    phone = extract_first_match(PHONE_REGEX, raw_resume_text)
    # Prefer the full https:// URL (from PDF annotations injected at end of text);
    # fall back to bare domain version found in the text stream.
    _li_https = r"https?://(?:www\.)?linkedin\.com/[^\s,;\"'<>]+"
    _li_bare = r"(?:www\.)?linkedin\.com/in/[^\s,;\"'<>]+"
    linkedin = (
        extract_first_match(_li_https, raw_resume_text, clean_url=True)
        or extract_first_match(_li_bare, raw_resume_text, clean_url=True)
    )
    _gh_https = r"https?://(?:www\.)?github\.com/[^\s,;\"'<>]+"
    _gh_bare = r"(?:www\.)?github\.com/[^\s,;\"'<>]+"
    github = (
        extract_first_match(_gh_https, raw_resume_text, clean_url=True)
        or extract_first_match(_gh_bare, raw_resume_text, clean_url=True)
    )
    location = infer_location(lines)

    headline = current_title
    if not headline and summary_text:
        first_sentence = re.split(r"(?<=[.!?])\s+", summary_text)[0].strip()
        headline = first_sentence[:120]

    return {
        "full_name": full_name,
        "current_title": current_title,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "location": location,
        "headline": headline,
        "summary": summary_text,
        "skills": resume_skills,
        "experience_bullets": split_section_into_bullets(experience_text, "experience"),
        "project_bullets": split_section_into_bullets(projects_text, "projects"),
        "education": education_text,
        "certifications": certifications_text,
    }