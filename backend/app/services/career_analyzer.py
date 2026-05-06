"""
Career progression, achievements, and red flag analyzer
Based on recruiter feedback for better candidate assessment
"""

import re
from typing import Dict, List
from app.services.experience_estimator import (
    extract_month_year_ranges,
    extract_professional_experience_ranges,
    _merge_ranges,
    _ordinal_to_ym,
    _CURRENT_YEAR,
    _CURRENT_MONTH,
    _month_ordinal,
    _strip_education_context_lines,
)


# Leadership/initiative signals (positive indicators)
LEADERSHIP_PATTERNS = [
    r'\b(led|leading|lead)\b',
    r'\b(created|built|developed|designed|architected)\b',
    r'\b(delivered|launched|shipped|released)\b',
    r'\b(started|initiated|established|founded)\b',
    r'\b(managed|supervised|mentored|coached)\b',
    r'\b(drove|spearheaded|championed)\b',
    r'\b(own|owned|ownership)\b',
    r'\b(directed|oversaw|executed)\b',
    r'\b(transformed|revamped|restructured)\b',
    r'\b(pioneered|innovated|conceptualized)\b',
]

# Weak signals (coordinating/supporting roles)
WEAK_SIGNALS = [
    r'\b(coordinated|facilitated|supported|assisted|helped)\b',
    r'\b(participated|contributed|involved)\b',
    r'\b(responsible for|worked on|worked with)\b',
    r'\b(was part of|served as)\b',
]

# Active action verbs list (used for language quality labeling)
ACTIVE_VERBS = [
    "led", "created", "built", "launched", "delivered", "drove", "spearheaded",
    "founded", "established", "initiated", "managed", "designed", "architected",
    "executed", "owned", "directed", "oversaw", "championed", "transformed",
    "revamped", "pioneered", "innovated", "negotiated", "secured", "achieved",
    "grew", "scaled", "reduced", "improved", "increased", "generated", "won",
    "shipped", "released", "deployed", "automated", "streamlined", "optimized",
]

# Passive/weak action verbs
PASSIVE_VERBS = [
    "coordinated", "facilitated", "supported", "assisted", "helped",
    "participated", "contributed", "involved", "collaborated", "worked on",
    "responsible for", "served as", "was part of", "helped with",
]

# Achievement indicators (measurable impact)
ACHIEVEMENT_PATTERNS = [
    r'\b(\d+%)\b',  # percentages
    r'\b(increased|improved|reduced|decreased|optimized)\b.*\b(\d+)',
    r'\b(saved|generated|revenue)\b',
    r'\b(\$\d+[KkMm]?)\b',  # dollar amounts
    r'\b(\d+x)\b',  # multipliers
    r'\b(award|recognition|promoted|promotion)\b',
]

# Red flag patterns
RED_FLAG_PATTERNS = {
    'short_tenure': r'(\d+)\s*(month|mo)',  # Very short tenures
    'generic_words': [
        r'\b(various|multiple|several|many)\b.*\b(responsibilities|tasks|duties)\b',
        r'\b(responsible for)\b',
        r'\b(worked on)\b',
    ],
    'vague_descriptions': [
        r'\b(etc\.|and more|among others)\b',
        r'\b(various|miscellaneous)\b',
    ],
    'gaps_indicator': r'(?:career\s+(?:break|gap)|employment\s+gap|took\s+a\s+break|sabbatical|between\s+jobs)',
}


def analyze_leadership_signals(resume_text: str, experience_bullets: List[str]) -> List[str]:
    """
    Identify leadership and initiative signals in the resume
    Returns list of positive leadership indicators
    """
    signals = []
    combined_text = ' '.join(experience_bullets + [resume_text]).lower()
    
    for pattern in LEADERSHIP_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                signal_word = match.group(1) if match.groups() else match.group(0)
                signals.append(signal_word.capitalize())
    
    # Deduplicate and return top signals
    return list(set(signals))[:5]


def analyze_achievements(experience_bullets: List[str], project_bullets: List[str]) -> Dict:
    """
    Score resume based on measurable achievements and impact
    Returns achievement score (0-100) and list of achievement indicators
    """
    all_bullets = experience_bullets + project_bullets
    achievement_count = 0
    achievement_examples = []
    
    for bullet in all_bullets:
        for pattern in ACHIEVEMENT_PATTERNS:
            matches = re.findall(pattern, bullet, re.IGNORECASE)
            if matches:
                achievement_count += 1
                # Extract a snippet showing the achievement
                snippet = bullet[:100] + '...' if len(bullet) > 100 else bullet
                achievement_examples.append(snippet)
                break  # Count each bullet once
    
    total_bullets = len(all_bullets) if all_bullets else 1
    achievement_ratio = achievement_count / total_bullets
    
    # Score: 0-100 based on ratio of achievement bullets
    # ≥40% achievements = 100 score, linear scale below that
    score = min(100, (achievement_ratio / 0.40) * 100)
    
    return {
        'score': round(score, 2),
        'count': achievement_count,
        'examples': achievement_examples[:3],  # Top 3 examples
    }


def analyze_career_progression(resume_text: str, estimated_years: float, experience_section: str = "") -> Dict:
    """
    Analyze career progression, stability, and tenure quality from the experience section.
    Uses month-level date ranges for accuracy.
    Returns progression score and indicators.
    """
    score = 50.0  # Base score
    indicators = []

    # ── Progression keywords ──────────────────────────────────────────────────
    progression_keywords = [
        r'promoted',
        r'senior|lead|principal|staff',
        r'team lead|technical lead|manager',
        r'architect',
    ]
    for kp in progression_keywords:
        if re.search(kp, resume_text, re.IGNORECASE):
            score += 10
            indicators.append(f"Progression indicator: {kp.replace('|', '/')}")

    # ── Month-level tenure analysis ───────────────────────────────────────────
    source_text = experience_section if experience_section.strip() else resume_text
    ranges = [
        tuple(r)
        for r in _merge_ranges(
            sorted(extract_professional_experience_ranges(source_text), key=lambda r: r[0])
        )
    ]

    if ranges:
        tenures_months = [end - start for start, end in ranges]
        avg_tenure_months = sum(tenures_months) / len(tenures_months)
        avg_tenure_years = avg_tenure_months / 12

        if avg_tenure_years >= 3:
            score += 20
            indicators.append(f"Stable tenure: avg {avg_tenure_years:.1f} yr/role")
        elif avg_tenure_years >= 2:
            score += 10
            indicators.append(f"Moderate tenure: avg {avg_tenure_years:.1f} yr/role")
        elif avg_tenure_years >= 1:
            indicators.append(f"Short-to-moderate tenure: avg {avg_tenure_years:.1f} yr/role")
        else:
            score -= 10
            indicators.append(f"Short average tenure: {int(avg_tenure_months)} months/role (review carefully)")

    score = min(100, max(0, score))
    return {'score': round(score, 2), 'indicators': indicators}


def analyze_timeline_gaps(experience_section: str, education_section: str = "") -> Dict:
    """
    Analyse date ranges from the experience and education sections with month precision.

    Career gaps are reported in exactly two categories:
      1. edu_work_gap   — gap between the end of education and the first job start.
      2. gaps           — month differences between leaving one role and joining the next.

    Education section date ranges are extracted ONLY from education_section so that
    degree / GPA year rows never contaminate the work-experience timeline.
    Experience section is pre-cleaned to strip any lines that look like education
    entries (GPA, college, degree keywords) before date parsing.
    """
    # Clean education-context lines from experience section before parsing
    clean_exp = _strip_education_context_lines(experience_section) if experience_section.strip() else ""
    exp_ranges = extract_professional_experience_ranges(clean_exp) if clean_exp.strip() else []

    # Education end dates come exclusively from the education section
    edu_ranges = extract_month_year_ranges(education_section) if education_section.strip() else []

    sorted_exp = [tuple(r) for r in _merge_ranges(sorted(exp_ranges, key=lambda r: r[0]))]

    tenures: list[dict] = []
    gaps: list[dict] = []
    short_tenure_flags: list[str] = []

    for i, (start, end) in enumerate(sorted_exp):
        dur = end - start
        sy, sm = _ordinal_to_ym(start)
        ey, em = _ordinal_to_ym(end)
        tenures.append({
            "role_index": i + 1,
            "start": f"{sm:02d}/{sy}",
            "end": f"{em:02d}/{ey}",
            "months": dur,
        })
        if dur < 12:
            short_tenure_flags.append(
                f"Role {i + 1} ({sm:02d}/{sy} – {em:02d}/{ey}): only {dur} month{'s' if dur != 1 else ''}"
            )

    # ── Career gap type 2: between leaving one org and joining the next ───────
    for i in range(1, len(sorted_exp)):
        prev_end = sorted_exp[i - 1][1]
        curr_start = sorted_exp[i][0]
        gap_months = curr_start - prev_end
        if gap_months > 1:
            py, pm_end = _ordinal_to_ym(prev_end)
            cy, cm_start = _ordinal_to_ym(curr_start)
            gaps.append({
                "after_role": i,
                "from": f"{pm_end:02d}/{py}",
                "to": f"{cm_start:02d}/{cy}",
                "months": gap_months,
            })

    # ── Career gap type 1: education end → first job start ───────────────────
    edu_work_gap = None
    if edu_ranges and sorted_exp:
        latest_edu_end = max(end for _, end in edu_ranges)
        earliest_work_start = sorted_exp[0][0]
        gap = earliest_work_start - latest_edu_end
        if gap > 3:  # only flag if > 3 months
            ey2, em2 = _ordinal_to_ym(latest_edu_end)
            wy, wm = _ordinal_to_ym(earliest_work_start)
            edu_work_gap = {
                "from": f"{em2:02d}/{ey2}",
                "to": f"{wm:02d}/{wy}",
                "months": gap,
            }

    return {
        "tenures": tenures,
        "gaps": gaps,
        "short_tenure_flags": short_tenure_flags,
        "edu_work_gap": edu_work_gap,
    }


def detect_red_flags(
    resume_text: str,
    experience_bullets: List[str],
    experience_section: str = "",
    education_section: str = "",
) -> List[str]:
    """
    Identify potential red flags in the resume using month-level timeline analysis.
    Returns list of red flag descriptions for recruiter review.
    """
    flags = []
    combined_text = ' '.join(experience_bullets).lower()

    # ── Month-level short tenure and gap detection ────────────────────────────
    # Pass only the dedicated sections — do NOT fall back to full resume_text
    # as that would mix education/project dates into the work timeline.
    timeline = analyze_timeline_gaps(experience_section, education_section)

    short_tenures = timeline["short_tenure_flags"]
    gaps = timeline["gaps"]
    edu_work_gap = timeline["edu_work_gap"]

    if len(short_tenures) >= 2:
        flags.append(
            f"Possible job hopping: {len(short_tenures)} role(s) under 12 months — "
            + "; ".join(short_tenures[:3])
            + " — verify if contracts or internships before screening out"
        )
    elif len(short_tenures) == 1:
        flags.append(
            f"Short-tenure role detected: {short_tenures[0]} — "
            "check if contract/internship or an early exit"
        )

    significant_gaps = [g for g in gaps if g["months"] >= 3]
    if significant_gaps:
        gap_strs = [
            f"{g['months']} month{'s' if g['months'] != 1 else ''} gap "
            f"({g['from']} – {g['to']})"
            for g in significant_gaps[:3]
        ]
        flags.append(
            "Employment gap(s) detected between roles: " + "; ".join(gap_strs)
            + " — ask candidate for context (upskilling, caregiving, relocation, etc.)"
        )

    if edu_work_gap and edu_work_gap["months"] >= 6:
        flags.append(
            f"Gap of {edu_work_gap['months']} months between education end "
            f"({edu_work_gap['from']}) and first work entry ({edu_work_gap['to']}) — verify reason"
        )

    # ── Also catch explicit career gap keywords in text ───────────────────────
    if re.search(RED_FLAG_PATTERNS['gaps_indicator'], resume_text, re.IGNORECASE):
        if not significant_gaps:  # avoid duplicate flag if already detected above
            flags.append(
                "Career gap mentioned in resume — ask candidate for context "
                "(sabbatical, caregiving, upskilling, etc.)"
            )

    # ── Vague / generic language ──────────────────────────────────────────────
    generic_count = 0
    for pattern in RED_FLAG_PATTERNS['generic_words']:
        if re.search(pattern, combined_text, re.IGNORECASE):
            generic_count += 1
    vague_count = 0
    for pattern in RED_FLAG_PATTERNS['vague_descriptions']:
        if re.search(pattern, combined_text, re.IGNORECASE):
            vague_count += 1

    if generic_count + vague_count >= 3:
        flags.append(
            "Resume uses generic/vague language (e.g. 'responsible for', 'worked on various') — "
            "hard to assess actual impact; recommend human review"
        )
    elif generic_count + vague_count >= 2:
        flags.append(
            "Some generic phrasing detected — ask candidate for specific examples in the interview"
        )

    # ── Passive vs active language imbalance ─────────────────────────────────
    weak_count = sum(1 for pattern in WEAK_SIGNALS if re.search(pattern, combined_text, re.IGNORECASE))
    strong_count = sum(1 for pattern in LEADERSHIP_PATTERNS if re.search(pattern, combined_text, re.IGNORECASE))

    if weak_count > strong_count * 1.5 and weak_count >= 3:
        flags.append(
            "More support/coordination language than ownership/initiative — "
            "may reflect limited decision-making scope; verify role seniority"
        )

    return flags


def analyze_industry_fit(resume_text: str, domain: str, matched_skills: List[str], total_skills: List[str]) -> Dict:
    """
    Analyze how well the candidate fits the industry/domain
    Returns industry fit score
    """
    # Domain relevance based on skill match
    if not total_skills:
        skill_ratio = 0
    else:
        skill_ratio = len(matched_skills) / len(total_skills)
    
    # Base score from skill match
    score = skill_ratio * 70  # Up to 70 points from skills
    
    # Domain keywords in resume (additional 30 points)
    domain_keywords = {
        'software': ['software', 'development', 'engineering', 'coding', 'programming'],
        'data': ['data', 'analytics', 'ml', 'machine learning', 'ai', 'statistics'],
        'devops': ['devops', 'cloud', 'infrastructure', 'deployment', 'ci/cd'],
        'web': ['web', 'frontend', 'backend', 'full stack', 'api'],
    }
    
    relevant_keywords = domain_keywords.get(domain.lower(), [])
    keyword_matches = sum(1 for kw in relevant_keywords if kw in resume_text.lower())
    
    keyword_bonus = min(30, (keyword_matches / max(1, len(relevant_keywords))) * 30)
    score += keyword_bonus
    
    return {
        'score': round(min(100, score), 2),
        'domain': domain,
    }


# Degree-level keywords for education fit check
_DEGREE_LEVEL_TERMS = [
    'phd', 'doctorate', 'master', 'mtech', 'm.tech', 'msc', 'm.sc', 'mba', 'pgdm',
    'bachelor', 'btech', 'b.tech', 'be ', 'b.e', 'bsc', 'b.sc', 'b.e.',
    'bca', 'mca', 'degree', 'graduate', 'postgraduate', 'undergraduate',
]

# Synonyms / equivalences so resume terms match JD terms that may be phrased differently
_EDU_SYNONYMS: dict[str, list[str]] = {
    'engineering': ['b.tech', 'btech', 'be ', 'b.e', 'b.e.', 'm.tech', 'mtech', 'engineer', 'engg'],
    'computer science': ['cse', 'cs', 'computer engineering', 'computer applications', 'information technology', 'it ', 'b.tech', 'btech', 'bca', 'mca'],
    'information technology': ['it ', 'cse', 'cs', 'computer science', 'computer applications', 'b.tech', 'btech', 'bca', 'mca'],
    'bachelor': ['bachelors', "bachelor's", 'bachelor degree', 'bachelors degree', 'b.tech', 'btech', 'be ', 'b.e', 'bsc', 'b.sc', 'bca', 'ba ', 'bba', 'undergraduate'],
    'master': ['masters', "master's", 'master degree', 'masters degree', 'm.tech', 'mtech', 'msc', 'm.sc', 'mca', 'mba', 'pgdm', 'postgraduate', 'pg '],
    'b.tech': ['btech', 'bachelor of technology', 'b tech', 'engineering'],
    'btech': ['b.tech', 'bachelor of technology', 'b tech', 'engineering'],
    'be': ['b.e', 'b.e.', 'bachelor of engineering', 'engineering'],
    'b.e': ['be ', 'b.e.', 'bachelor of engineering', 'engineering'],
    'bsc': ['b.sc', 'bachelor of science', 'b sc', 'bachelor'],
    'b.sc': ['bsc', 'bachelor of science', 'b sc', 'bachelor'],
    'bca': ['bachelor of computer applications', 'bachelor'],
    'mca': ['master of computer applications', 'master'],
    'mtech': ['m.tech', 'master of technology', 'm tech'],
    'm.tech': ['mtech', 'master of technology', 'm tech'],
    'msc': ['m.sc', 'master of science', 'm sc', 'master'],
    'm.sc': ['msc', 'master of science', 'm sc', 'master'],
    'mba': ['master of business', 'pgdm', 'postgraduate diploma'],
    'phd': ['doctorate', 'doctoral', 'ph.d', 'doctor of'],
}


def _normalise_edu_text(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[\.\-_,;:()\[\]]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains_edu_phrase(haystack: str, needle: str) -> bool:
    needle = _normalise_edu_text(needle)
    if not needle:
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack))


def _split_education_alternatives(req: str) -> list[str]:
    parts = re.split(r"\s*(?:/|\bor\b|\||,)\s*", req, flags=re.IGNORECASE)
    return [part.strip() for part in parts if part.strip()]


def _has_any_degree_evidence(edu_text: str) -> bool:
    return any(_contains_edu_phrase(edu_text, term) for term in _DEGREE_LEVEL_TERMS)


def _edu_text_matches(req: str, edu_text: str) -> bool:
    """Return True if `req` or any synonym is found in `edu_text`."""
    req_lower = req.lower().strip()
    req_norm = _normalise_edu_text(req_lower)
    edu_norm = _normalise_edu_text(edu_text)

    alternatives = _split_education_alternatives(req)
    if len(alternatives) > 1:
        return any(_edu_text_matches(alt, edu_norm) for alt in alternatives)

    if _contains_edu_phrase(edu_norm, req_norm):
        return True

    # Generic JD wording such as "degree", "graduate", or "bachelor degree"
    # should match concrete resume degrees like MCA, BSc, B.Tech, etc.
    if req_norm in {"degree", "degrees", "graduate", "graduation"}:
        return _has_any_degree_evidence(edu_norm)
    if re.search(r"\bbachelors?\b|\bbachelor s\b", req_norm):
        return (
            _contains_edu_phrase(edu_norm, "bachelor")
            or any(_contains_edu_phrase(edu_norm, term) for term in _EDU_SYNONYMS["bachelor"])
        )
    if re.search(r"\bmasters?\b|\bmaster s\b", req_norm):
        return (
            _contains_edu_phrase(edu_norm, "master")
            or any(_contains_edu_phrase(edu_norm, term) for term in _EDU_SYNONYMS["master"])
        )

    # Check synonyms
    for key, synonyms in _EDU_SYNONYMS.items():
        key_norm = _normalise_edu_text(key)
        synonym_norms = [_normalise_edu_text(syn) for syn in synonyms]
        # If req matches a synonym key
        if req_norm == key_norm:
            for syn in synonym_norms:
                if _contains_edu_phrase(edu_norm, syn):
                    return True
        # If req matches a synonym value
        if req_norm in synonym_norms:
            if _contains_edu_phrase(edu_norm, key_norm):
                return True
    return False


def check_education_fit(resume_sections: dict, education_requirements: list[str]) -> dict:
    """
    Compare resume education section against JD education requirements.
    Returns a dict with meets_requirement, matched, missing, and message.
    """
    if not education_requirements:
        return {
            'meets_requirement': None,
            'matched': [],
            'missing': [],
            'message': 'No specific education requirement stated in the JD.',
        }

    # Build text to search — education + certifications + summary + other sections
    # Also include the full resume text (passed via 'other' fallback) for robustness
    edu_text = ' '.join([
        resume_sections.get('education', ''),
        resume_sections.get('certifications', ''),
        resume_sections.get('summary', ''),
        resume_sections.get('other', ''),
    ]).lower()

    # If education section is essentially empty, broaden to whole resume text
    if len(edu_text.strip()) < 30:
        # Use all section texts
        edu_text = ' '.join(resume_sections.values()).lower()

    matched = []
    missing = []
    for req in education_requirements:
        if _edu_text_matches(req, edu_text):
            matched.append(req)
        else:
            missing.append(req)

    # A pass means at least one degree-level keyword from the JD is evidenced
    degree_reqs = [
        r for r in education_requirements
        if any(d in r.lower().replace('.', '') for d in _DEGREE_LEVEL_TERMS)
    ]
    degree_matched = [r for r in degree_reqs if r in matched]

    if degree_reqs:
        meets = len(degree_matched) > 0
    else:
        # Only field/domain requirements (e.g. "computer science") — soft check
        meets = len(matched) > 0 if education_requirements else None

    if meets is True:
        message = f"Resume education matches JD requirement ({', '.join((matched or education_requirements)[:3])})."
    elif meets is False:
        message = (
            f"JD requires: {', '.join(education_requirements[:3])}. "
            "Not clearly evidenced in resume — verify manually before rejecting."
        )
    else:
        message = 'Education requirement check inconclusive — review manually.'

    return {
        'meets_requirement': meets,
        'matched': matched,
        'missing': missing,
        'message': message,
    }


def analyze_language_quality(resume_text: str, experience_bullets: List[str], seniority_level: str = 'mid') -> Dict:
    """
    Analyze the quality of language used in the resume.
    Measures active (initiative-showing) vs passive (support-role) verb usage.
    Calibrates quality label against expected role seniority level.
    Returns quality score, counts, and lists of verbs found.
    """
    combined_text = ' '.join(experience_bullets + [resume_text]).lower()

    found_active = []
    found_passive = []

    for verb in ACTIVE_VERBS:
        pattern = r'\b' + re.escape(verb) + r'\b'
        if re.search(pattern, combined_text, re.IGNORECASE):
            found_active.append(verb.capitalize())

    for verb in PASSIVE_VERBS:
        pattern = r'\b' + re.escape(verb) + r'\b'
        if re.search(pattern, combined_text, re.IGNORECASE):
            found_passive.append(verb.capitalize())

    active_count = len(found_active)
    passive_count = len(found_passive)
    total = active_count + passive_count

    ratio = round(active_count / total * 100) if total > 0 else 0

    # Calibrate thresholds and labels to role seniority
    if seniority_level in ('senior', 'lead'):
        # Senior/lead roles: expect strong ownership language
        if ratio >= 70:
            quality_label = "Strong — ownership & initiative language expected at this level ✓"
            quality_level = "strong"
        elif ratio >= 45:
            quality_label = "Mixed — senior/lead roles typically need stronger ownership language"
            quality_level = "mixed"
        else:
            quality_label = "Passive — ownership language is critical for senior/lead roles"
            quality_level = "weak"
    elif seniority_level == 'junior':
        # Junior/entry roles: support language is acceptable
        if ratio >= 50:
            quality_label = "Strong — good initiative language for an early-career profile"
            quality_level = "strong"
        elif ratio >= 30:
            quality_label = "Mixed — some support language is expected at junior level"
            quality_level = "mixed"
        else:
            quality_label = "Passive — mostly coordination language; acceptable for junior roles"
            quality_level = "weak"
    else:
        # Mid-level (default)
        if ratio >= 70:
            quality_label = "Strong — ownership & initiative language dominates"
            quality_level = "strong"
        elif ratio >= 45:
            quality_label = "Mixed — some initiative, some support language"
            quality_level = "mixed"
        else:
            quality_label = "Passive — mostly coordination/support language"
            quality_level = "weak"

    return {
        'active_count': active_count,
        'passive_count': passive_count,
        'active_ratio': ratio,
        'active_verbs': found_active[:8],
        'passive_verbs': found_passive[:6],
        'quality_label': quality_label,
        'quality_level': quality_level,
        'seniority_level': seniority_level,
    }


def detect_over_tailoring(
    required_skill_score: float,
    overall_score: float,
    resume_text: str,
) -> bool:
    """
    Flag if the resume appears over-tailored to this specific JD.
    A resume with near-perfect required skill coverage AND a very high overall
    score can be a red flag — it may have been keyword-stuffed or reverse-engineered
    from the job description rather than reflecting genuine experience.
    Also checks for suspiciously dense JD-language repetition.
    """
    # Threshold: required skills >95% AND overall >88 is suspicious
    score_based_flag = required_skill_score >= 95 and overall_score >= 88

    # Additional check: unusually high keyword density (sign of keyword stuffing)
    # Count generic buzzwords used excessively
    buzzwords = [
        'synergy', 'leverage', 'dynamic', 'result-oriented', 'team player',
        'self-starter', 'proactive', 'go-getter', 'passionate', 'enthusiastic',
        'detail-oriented', 'fast-paced', 'innovative', 'strategic',
    ]
    buzzword_count = sum(
        1 for bw in buzzwords
        if re.search(r'\b' + re.escape(bw) + r'\b', resume_text, re.IGNORECASE)
    )
    buzzword_flag = buzzword_count >= 5

    return score_based_flag or buzzword_flag
