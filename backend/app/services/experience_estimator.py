import re
from datetime import datetime


MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_NOW = datetime.now()
_CURRENT_YEAR: int = _NOW.year
_CURRENT_MONTH: int = _NOW.month

_PRESENT_RE = r"(?:present|current|till date|today|ongoing)"
_YEAR_RE = r"20\d{2}"
_MONTH_NAMES_RE = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)


def _month_ordinal(year: int, month: int) -> int:
    """Return a monotonic integer for (year, month): year*12 + (month-1)."""
    return year * 12 + (month - 1)


def _parse_month_name(s: str) -> int:
    """Convert a month name/abbreviation to 1-indexed month number."""
    s = s.lower().strip()
    for key, val in MONTH_MAP.items():
        if s.startswith(key):
            return val
    return 1  # default to January


def extract_month_year_ranges(text: str) -> list[tuple[int, int]]:
    """
    Extract date ranges from resume text as (start_ordinal, end_ordinal) pairs,
    where ordinal = year * 12 + (month - 1).

    Handles:
      - Mon YYYY – Mon YYYY   (e.g. "Jan 2020 – Aug 2023")
      - Mon YYYY – Present
      - Mon YYYY to Mon YYYY
      - Mon YYYY to Present
      - MM/YYYY – MM/YYYY     (e.g. "01/2022 to 10/2024")
      - MM/YYYY – Present
      - MM/YYYY to MM/YYYY    (slash-separated, "to" connector)
      - YYYY – YYYY           (assume Jan start, Dec end)
      - YYYY – Present
      - YYYY to YYYY / YYYY to Present

    Returns deduplicated, sorted list.
    """
    ranges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    # --- Pattern -1: "From Mon YYYY" / "Since Mon YYYY" (no end = present) ----
    # Common in resumes like "Data Scientist at Acme (From Sep 2024)"
    p_from_mon = re.compile(
        rf"(?:from|since)\s+({_MONTH_NAMES_RE})\s+({_YEAR_RE})\b",
        re.IGNORECASE,
    )
    for m in p_from_mon.finditer(text):
        start_month = _parse_month_name(m.group(1))
        start_year = int(m.group(2))
        start_ord = _month_ordinal(start_year, start_month)
        end_ord = _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        if end_ord >= start_ord:
            key = (start_ord, end_ord)
            if key not in seen:
                seen.add(key)
                ranges.append(key)

    # --- Pattern -0.5: "From YYYY" / "Since YYYY" (year-only, no end = present) ---
    p_from_year = re.compile(
        rf"(?:from|since)\s+({_YEAR_RE})(?!\s*(?:[\-–—]|to)\s*\d)",
        re.IGNORECASE,
    )
    for m in p_from_year.finditer(text):
        start_year = int(m.group(1))
        start_ord = _month_ordinal(start_year, 1)
        end_ord = _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        if end_ord >= start_ord:
            already_covered = any(
                _month_ordinal(start_year, 1) <= s <= _month_ordinal(start_year, 12)
                for s, _ in seen
            )
            if not already_covered:
                key = (start_ord, end_ord)
                if key not in seen:
                    seen.add(key)
                    ranges.append(key)

    # --- Pattern 0: "MM/YYYY – MM/YYYY" or "MM/YYYY – Present" ----------
    # Also handles "MM/YYYY to MM/YYYY" and "MM/YYYY to Present"
    _MM_YYYY = r"(0?[1-9]|1[0-2])/(20\d{2})"
    p_slash = re.compile(
        rf"{_MM_YYYY}\s*(?:[\-–—]+|to)\s*(?:{_MM_YYYY}|({_PRESENT_RE}))",
        re.IGNORECASE,
    )
    for m in p_slash.finditer(text):
        start_month = int(m.group(1))
        start_year = int(m.group(2))
        end_month_str = m.group(3)   # may be None if present
        end_year_str = m.group(4)    # may be None if present
        present_str = m.group(5)     # the "present/current" match

        start_ord = _month_ordinal(start_year, start_month)

        if present_str:
            end_ord = _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        elif end_month_str and end_year_str:
            end_ord = _month_ordinal(int(end_year_str), int(end_month_str))
        else:
            continue

        if end_ord >= start_ord:
            key = (start_ord, end_ord)
            if key not in seen:
                seen.add(key)
                ranges.append(key)

    # --- Pattern 1: "Mon YYYY – Mon YYYY" / "Mon YYYY to Mon YYYY" -------
    p_full = re.compile(
        rf"({_MONTH_NAMES_RE})\s+({_YEAR_RE})\s*(?:[\-–—]+|to)\s*"
        rf"(?:({_MONTH_NAMES_RE})\s+)?({_YEAR_RE}|{_PRESENT_RE})",
        re.IGNORECASE,
    )
    for m in p_full.finditer(text):
        start_month = _parse_month_name(m.group(1))
        start_year = int(m.group(2))
        end_month_str = m.group(3)
        end_str = m.group(4).strip()

        start_ord = _month_ordinal(start_year, start_month)

        if re.match(_PRESENT_RE, end_str, re.IGNORECASE):
            end_ord = _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        else:
            end_year = int(end_str)
            end_month = _parse_month_name(end_month_str) if end_month_str else 12
            end_ord = _month_ordinal(end_year, end_month)

        if end_ord >= start_ord:
            key = (start_ord, end_ord)
            if key not in seen:
                seen.add(key)
                ranges.append(key)

    # --- Pattern 2: bare "YYYY – YYYY" or "YYYY – Present" ---------------
    # Skip ranges already covered by Pattern 0 or 1 (same year-start)
    p_year = re.compile(
        rf"(?<!\d)({_YEAR_RE})\s*[\-–—]+\s*({_YEAR_RE}|{_PRESENT_RE})(?!\d)",
        re.IGNORECASE,
    )
    for m in p_year.finditer(text):
        start_year = int(m.group(1))
        end_str = m.group(2).strip()

        start_ord = _month_ordinal(start_year, 1)  # assume Jan

        if re.match(_PRESENT_RE, end_str, re.IGNORECASE):
            end_ord = _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        else:
            end_year = int(end_str)
            end_ord = _month_ordinal(end_year, 12)  # assume Dec

        if end_ord >= start_ord:
            # Only add if no month-precise range already covers this start year
            already_covered = any(
                _month_ordinal(start_year, 1) <= s <= _month_ordinal(start_year, 12)
                for s, _ in seen
            )
            if not already_covered:
                key = (start_ord, end_ord)
                if key not in seen:
                    seen.add(key)
                    ranges.append(key)

    # --- Pattern 3: "YYYY to YYYY" / "YYYY to Present" -------------------
    p_to = re.compile(
        rf"(?<!\d)({_YEAR_RE})\s+to\s+({_YEAR_RE}|{_PRESENT_RE})(?!\d)",
        re.IGNORECASE,
    )
    for m in p_to.finditer(text):
        start_year = int(m.group(1))
        end_str = m.group(2).strip()

        start_ord = _month_ordinal(start_year, 1)
        if re.match(_PRESENT_RE, end_str, re.IGNORECASE):
            end_ord = _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        else:
            end_ord = _month_ordinal(int(end_str), 12)

        if end_ord >= start_ord:
            already_covered = any(
                _month_ordinal(start_year, 1) <= s <= _month_ordinal(start_year, 12)
                for s, _ in seen
            )
            if not already_covered:
                key = (start_ord, end_ord)
                if key not in seen:
                    seen.add(key)
                    ranges.append(key)

    return sorted(ranges, key=lambda r: r[0])


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[list[int]]:
    """Merge overlapping or adjacent month-ordinal ranges."""
    if not ranges:
        return []
    merged: list[list[int]] = [[ranges[0][0], ranges[0][1]]]
    for start, end in ranges[1:]:
        if start <= merged[-1][1] + 1:  # adjacent or overlapping
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _ordinal_to_ym(ordinal: int) -> tuple[int, int]:
    """Convert ordinal back to (year, month)."""
    year = ordinal // 12
    month = (ordinal % 12) + 1
    return year, month


# ── Education-context line filter ─────────────────────────────────────────────
_EDU_CONTEXT_RE = re.compile(
    r"\b(gpa|cgpa|grade|percentage|marks|university|college|institute|school|"
    r"batch|graduation|graduated|btech|b\.tech|mtech|m\.tech|bsc|b\.sc|"
    r"msc|m\.sc|degree|diploma|pursuing|semester|semester|honours|honor)\b",
    re.IGNORECASE,
)

_NON_WORK_DATE_CONTEXT_RE = re.compile(
    r"\b(gpa|cgpa|grade|percentage|marks|university|college|institute|school|"
    r"batch|graduation|graduated|btech|b\.tech|mtech|m\.tech|bsc|b\.sc|"
    r"msc|m\.sc|degree|diploma|pursuing|semester|honours|honor|"
    r"project|projects|academic project|personal project|certification|certifications|"
    r"certificate|certificates|course|courses|bootcamp|class|udemy|coursera|"
    r"high school|higher secondary|bachelor|bachelors|master|masters)\b",
    re.IGNORECASE,
)

_WORK_CONTEXT_RE = re.compile(
    r"\b(work experience|professional experience|employment history|career history|"
    r"engineer|developer|analyst|scientist|consultant|specialist|manager|lead|"
    r"architect|intern|trainee|associate|officer|executive|tata elxsi|"
    r"technologies|solutions|systems|software|labs|pvt|private limited|inc|llc|ltd)\b",
    re.IGNORECASE,
)

_DATEISH_LINE_RE = re.compile(
    rf"^\s*(?:{_MONTH_NAMES_RE}\s+)?(?:{_YEAR_RE})(?:\s*(?:[\-–—]+|to)\s*(?:{_MONTH_NAMES_RE}\s+)?(?:{_YEAR_RE}|{_PRESENT_RE}))?\s*$",
    re.IGNORECASE,
)


def _strip_education_context_lines(text: str) -> str:
    """
    Remove lines that look like education entries so their year ranges
    (e.g. '2019 – 2022  GPA: 8.5') don't get counted as work experience.
    """
    return "\n".join(
        line for line in text.splitlines()
        if not _EDU_CONTEXT_RE.search(line)
    )


def _line_has_date_range(line: str) -> bool:
    return bool(extract_month_year_ranges(line))


def _has_date_column_cluster(lines: list[str]) -> bool:
    """
    Detect PDF text extraction where visual columns collapse into a vertical date
    stack. In that layout, project/course/education dates may sit beside one real
    work row, so treating every range as employment creates fake job hopping.
    """
    current = 0
    best = 0
    for line in lines:
        if _DATEISH_LINE_RE.match(line.strip()):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best >= 4


def extract_professional_experience_ranges(experience_text: str) -> list[tuple[int, int]]:
    """
    Extract likely employment date ranges from an experience section.

    Unlike extract_month_year_ranges(), this intentionally rejects ranges that
    appear to belong to education, projects, or certifications. It also handles
    PDF column extraction where many unrelated date rows are dumped under
    "Work Experience" by choosing the strongest ongoing employment range.
    """
    if not experience_text or not experience_text.strip():
        return []

    cleaned_exp = _strip_education_context_lines(experience_text)
    lines = [line.strip() for line in cleaned_exp.splitlines() if line.strip()]
    line_ranges: list[tuple[int, tuple[int, int]]] = []

    for idx, line in enumerate(lines):
        for date_range in extract_month_year_ranges(line):
            line_ranges.append((idx, date_range))

    if not line_ranges:
        return []

    if _has_date_column_cluster(lines):
        present_ranges = [
            date_range
            for _, date_range in line_ranges
            if date_range[1] >= _month_ordinal(_CURRENT_YEAR, _CURRENT_MONTH)
        ]
        if present_ranges and _WORK_CONTEXT_RE.search(cleaned_exp):
            # In a collapsed date column, the actual job is usually the longest
            # ongoing range; shorter ongoing rows are often active projects.
            longest = max(present_ranges, key=lambda r: r[1] - r[0])
            return [longest]

    accepted: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    for idx, date_range in line_ranges:
        context = "\n".join(lines[max(0, idx - 3): min(len(lines), idx + 4)])
        has_work_context = bool(_WORK_CONTEXT_RE.search(context))
        has_non_work_context = bool(_NON_WORK_DATE_CONTEXT_RE.search(context))

        if has_work_context and not (has_non_work_context and not re.search(r"\b(work experience|professional experience|engineer|developer|analyst|intern|manager|consultant)\b", context, re.IGNORECASE)):
            if date_range not in seen:
                seen.add(date_range)
                accepted.append(date_range)

    if accepted:
        return sorted(accepted, key=lambda r: r[0])

    # Conservative fallback: only use all ranges if the section itself strongly
    # looks like employment and does not look like project/cert/education text.
    if _WORK_CONTEXT_RE.search(cleaned_exp) and not _NON_WORK_DATE_CONTEXT_RE.search(cleaned_exp):
        return extract_month_year_ranges(cleaned_exp)

    return []


# ── Explicit "X years of experience" extractor ────────────────────────────────
_YRS_EXP_PATTERNS = [
    # "5+ years of experience", "5 years experience", "5+ yrs of work experience"
    re.compile(
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)"
        r"[\s\w]{0,25}(?:experience|exp\b)",
        re.IGNORECASE,
    ),
    # "experience of 5 years", "experience of over 5 years"
    re.compile(
        r"experience\s+(?:of\s+)?(?:over\s+|more\s+than\s+)?"
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        re.IGNORECASE,
    ),
    # "over 5 years' experience", "more than 5 years experience"
    re.compile(
        r"(?:over|more\s+than|~|around|approximately)\s+"
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)"
        r"[\s\w]{0,20}(?:experience|exp\b)",
        re.IGNORECASE,
    ),
]


def extract_years_from_text(text: str) -> float | None:
    """
    Return the explicitly stated years of experience found in *text*,
    or None if no such statement exists.

    Tries patterns like:
      "5+ years of experience", "over 3 years experience",
      "experience of 7 years", "~2 years of work experience"
    """
    if not text:
        return None
    for pattern in _YRS_EXP_PATTERNS:
        m = pattern.search(text)
        if m:
            val = float(m.group(1))
            if 0 < val <= 50:  # sanity-check
                return val
    return None


def _duration_str(total_months: int) -> str:
    yrs = total_months // 12
    mos = total_months % 12
    if mos == 0:
        return f"{yrs} year{'s' if yrs != 1 else ''}"
    return f"{yrs} year{'s' if yrs != 1 else ''} {mos} month{'s' if mos != 1 else ''}"


def estimate_total_experience_years(
    experience_text: str,
    full_resume_text: str = "",
    summary_text: str = "",
) -> dict:
    """
    Estimate total professional experience. Priority order:

    1. If *summary_text* contains an explicit "X years of experience" statement,
       use that value directly — candidates often state their total tenure here.
    2. Otherwise parse month-level date ranges from *experience_text*, after
       stripping lines that look like education entries (GPA, degree, college…)
       so academic year ranges don't inflate the work-experience count.
    """
    # ── Step 1: explicit statement in the summary / profile section ───────────
    if summary_text and summary_text.strip():
        yrs_stated = extract_years_from_text(summary_text)
        if yrs_stated is not None:
            total_months = round(yrs_stated * 12)
            return {
                "estimated_years": yrs_stated,
                "estimated_months": total_months,
                "ranges_found": [],
                "note": f"Stated in summary/profile section: ~{_duration_str(total_months)}.",
                "source": "summary",
            }

    # Some PDF resumes extract "PROFILE SUMMARY ..." into the catch-all body
    # instead of the summary section. Prefer this explicit statement over noisy
    # date math when available.
    if full_resume_text and full_resume_text.strip():
        yrs_stated = extract_years_from_text(full_resume_text)
        if yrs_stated is not None:
            total_months = round(yrs_stated * 12)
            return {
                "estimated_years": yrs_stated,
                "estimated_months": total_months,
                "ranges_found": [],
                "note": f"Stated in resume profile/body: ~{_duration_str(total_months)}.",
                "source": "explicit_resume_text",
            }

    # ── Step 2: date-range calculation from the experience section ────────────
    if not experience_text or not experience_text.strip():
        return {
            "estimated_years": None,
            "estimated_months": None,
            "ranges_found": [],
            "note": "No experience section detected in the resume.",
            "source": "none",
        }

    ranges = extract_professional_experience_ranges(experience_text)

    if not ranges:
        return {
            "estimated_years": None,
            "estimated_months": None,
            "ranges_found": [],
            "note": "Could not find date ranges in the experience section.",
            "source": "none",
        }

    merged = _merge_ranges(ranges)
    total_months = sum(end - start for start, end in merged)
    total_years = round(total_months / 12, 1)

    # Build display-friendly (start_year, end_year) pairs
    display_ranges = []
    for start, end in ranges:
        sy, _ = _ordinal_to_ym(start)
        ey, _ = _ordinal_to_ym(end)
        display_ranges.append((sy, ey))

    return {
        "estimated_years": total_years,
        "estimated_months": total_months,
        "ranges_found": display_ranges,
        "note": f"Calculated from {len(merged)} work period(s): {_duration_str(total_months)} total.",
        "source": "experience_section",
    }


def compare_with_jd_experience_requirement(
    estimated_resume_years: float | None,
    min_required_years: int | None,
    max_required_years: int | None = None,
) -> dict:
    """Compare candidate experience against JD requirement.

    Handles three cases:
    - Range (e.g. 3-8 yrs): candidate meets requirement if min ≤ yrs ≤ max.
      Over-qualified (above max) is flagged as advisory, not a hard fail.
    - Minimum only (e.g. 5+ yrs): candidate meets requirement if yrs ≥ min.
    - No requirement: returns None.
    """
    if min_required_years is None:
        return {
            "meets_requirement": None,
            "gap_years": None,
            "message": "No explicit minimum experience requirement found in the JD.",
        }

    if estimated_resume_years is None:
        return {
            "meets_requirement": None,
            "gap_years": None,
            "message": "Could not confidently estimate experience from the resume.",
        }

    est = estimated_resume_years

    # ── Range case ───────────────────────────────────────────────────────────
    if max_required_years is not None:
        if est < min_required_years:
            gap = round(est - min_required_years, 1)
            return {
                "meets_requirement": False,
                "gap_years": gap,
                "message": (
                    f"Estimated {est}y experience is below the JD range "
                    f"of {min_required_years}–{max_required_years} years."
                ),
            }
        if est > max_required_years:
            return {
                "meets_requirement": True,   # still qualifies — over-qualified is advisory, not a fail
                "gap_years": round(est - max_required_years, 1),
                "message": (
                    f"Estimated {est}y experience exceeds the JD range "
                    f"of {min_required_years}–{max_required_years} years. "
                    "Candidate may be over-qualified — verify role fit."
                ),
            }
        return {
            "meets_requirement": True,
            "gap_years": 0.0,
            "message": (
                f"Estimated {est}y experience is within the JD range "
                f"of {min_required_years}–{max_required_years} years."
            ),
        }

    # ── Minimum-only case ────────────────────────────────────────────────────
    gap = round(est - min_required_years, 1)
    return {
        "meets_requirement": gap >= 0,
        "gap_years": gap,
        "message": (
            f"Estimated {est}y experience meets the JD minimum of {min_required_years} years."
            if gap >= 0
            else f"Estimated {est}y experience is below the JD minimum of {min_required_years} years."
        ),
    }
