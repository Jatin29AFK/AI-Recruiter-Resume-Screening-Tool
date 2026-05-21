from __future__ import annotations

import re
from typing import Optional

from app.utils.constants import (
    RESUME_DETECTION_GRACE_BAND,
    RESUME_DETECTION_MIN_TEXT_CHARS,
    RESUME_DETECTION_NEGATIVE_WEIGHTS,
    RESUME_DETECTION_POSITIVE_WEIGHTS,
    RESUME_DETECTION_REJECT_MARGIN,
    SKILL_ALIASES,
    SKILL_CATEGORIES,
)

_SECTION_HINTS = (
    "education",
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "skills",
    "projects",
    "certifications",
    "summary",
    "profile",
)

_RESUME_HEADING_PATTERNS = (
    "summary",
    "profile",
    "professional summary",
    "career objective",
    "objective",
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "education",
    "skills",
    "technical skills",
    "projects",
    "certifications",
    "achievements",
)

_DATE_PATTERNS = [
    re.compile(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b"),
    re.compile(r"\b(19|20)\d{2}\s*[-–]\s*(present|current)\b", re.IGNORECASE),
    re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{4}\b", re.IGNORECASE),
]

_LEGAL_TERMS = (
    "terms and conditions",
    "hereby agree",
    "indemnify",
    "liability",
    "governing law",
)

_ACADEMIC_TERMS = (
    "references",
    "methodology",
    "abstract",
    "literature review",
    "doi",
)

_ESSAY_MARKERS = (
    "once upon a time",
    "in conclusion",
    "the story",
)

_INVOICE_TERMS = (
    "gst",
    "invoice",
    "bill to",
    "total amount",
    "subtotal",
    "tax",
)

_TRAVEL_BOOKING_TERMS = (
    "booking confirmation",
    "booking reference",
    "reservation",
    "itinerary",
    "pnr",
    "passenger",
    "boarding pass",
    "flight number",
    "departure",
    "arrival",
    "terminal",
    "gate",
    "check-in",
    "check in",
    "check-out",
    "check out",
    "hotel booking",
    "room type",
    "guest name",
    "nights",
    "fare",
    "ticket number",
    "e-ticket",
    "airline",
)

_INSTALLATION_GUIDE_TERMS = (
    "setup guide",
    "installation guide",
    "installation and troubleshooting guide",
    "step-by-step installation",
    "prerequisites",
    "folder structure",
    "troubleshooting",
    "common issues",
    "make it executable",
    "clone the repository",
    "config file",
    "configuration file",
    "restart ",
    "launch it once",
    "run the following command",
    "example command",
    "download the",
    "install ",
    "installed and able to launch",
)

_LEARNING_CONTENT_TERMS = (
    "what is",
    "what type of",
    "how does",
    "how it works",
    "let's start",
    "lets start",
    "core features",
    "for example",
    "example 1",
    "example 2",
    "semantic search",
    "foundation model",
    "large language model",
    "retrieval augmented generation",
    "fine tuning",
    "finetuning",
    "hallucination",
    "vector db",
    "embeddings",
    "chunks",
    "query",
    "question answering",
    "chatbot",
    "tutorial",
    "course",
)

_FEEDBACK_DOCUMENT_TERMS = (
    "feedback",
    "shortlisting pointers",
    "recruiter's pov",
    "recruiter pov",
    "hr usually looks for",
    "for a scoring system",
    "scoring can be",
    "the tool should answer",
    "must-have match",
    "preferred skills",
    "red flags",
    "positive signals",
    "non-negotiables",
    "sliding scale",
    "can we add option",
    "would be helpful",
    "candidate match the job",
    "human review is still important",
)

_FORM_TEMPLATE_TERMS = (
    "student evaluation",
    "student name",
    "student id",
    "roll number",
    "roll no",
    "instructor",
    "grade",
    "rubric",
    "course code",
    "assignment",
    "semester",
    "term",
    "evaluation form",
    "overall performance",
    "date of submission",
    "problem statement",
    "approach / methodology",
    "methodology",
    "objective",
    "objectives",
    "submission",
    "do not change the sequence",
    "submit as a pdf",
)

_STRONG_FORM_TERMS = (
    "student evaluation form",
    "student id",
    "student name:",
    "evaluation form",
)

# If key student/form markers co-occur (student name/roll + date/submission or problem statement),
# treat as strong form template match.
_STRONG_CO_OCCURRENCE_PAIRS = (
    ("student name", "date of submission"),
    ("roll number", "date of submission"),
    ("student id", "date of submission"),
    ("student name", "problem statement"),
    ("roll number", "problem statement"),
)

_NOTES_TERMS = (
    "notes",
    "meeting notes",
    "minutes",
    "action items",
    "next steps",
    "todo",
    "to do",
    "memo",
    "lecture notes",
    "lab notes",
    "notes:",
    "checklist",
)

_CODE_TERMS = (
    "import ",
    "def ",
    "function ",
    "class ",
    "{",
    "}",
    "=>",
)

_AGENT_CHANGE_LOG_TERMS = (
    "created todos",
    "starting:",
    "completed:",
    "read , lines",
    "searched for text",
    "searched for regex",
    "replacing ",
    "ran terminal command",
    "now update",
    "now find and replace",
)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def detect_language_hint(text: str) -> str:
    if not text:
        return ""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return ""
    ascii_letters = [ch for ch in letters if ord(ch) < 128]
    ascii_ratio = len(ascii_letters) / len(letters)
    return "en" if ascii_ratio >= 0.6 else "multi"


def _compute_positive_signals(text: str, text_lower: str) -> dict[str, float]:
    text_len = len(text)
    text_length_score = min(1.0, text_len / 2400.0)

    section_hits = sum(1 for k in _SECTION_HINTS if re.search(rf"\b{re.escape(k)}\b", text_lower))
    section_keyword_score = min(1.0, section_hits / 4.0)

    date_hits = sum(len(pattern.findall(text)) for pattern in _DATE_PATTERNS)
    date_density_score = min(1.0, date_hits / 8.0)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullet_lines = [ln for ln in lines if ln.startswith(("-", "*", "•")) or re.match(r"^\d+[\.)]\s", ln)]
    bullet_format_score = _safe_ratio(len(bullet_lines), max(12, len(lines))) * 3.0
    bullet_format_score = min(1.0, bullet_format_score)

    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+.#-]*\b", text)
    title_case_words = [w for w in words if len(w) > 2 and w[0].isupper()]
    noun_density_score = min(1.0, _safe_ratio(len(title_case_words), max(1, len(words))) * 4.0)

    all_skills = set()
    for skills in SKILL_CATEGORIES.values():
        all_skills.update(skills)
    all_skills.update(SKILL_ALIASES.keys())
    skill_hits = sum(1 for s in all_skills if re.search(rf"\b{re.escape(s)}\b", text_lower))
    skill_overlap_score = min(1.0, skill_hits / 10.0)

    return {
        "text_length": round(text_length_score, 4),
        "section_keywords": round(section_keyword_score, 4),
        "date_density": round(date_density_score, 4),
        "skill_overlap": round(skill_overlap_score, 4),
        "bullet_format": round(bullet_format_score, 4),
        "noun_density": round(noun_density_score, 4),
    }


def _compute_resume_identity_signals(text: str, text_lower: str) -> dict[str, float]:
    email_hits = len(re.findall(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", text))
    phone_candidates = re.findall(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)", text)
    phone_hits = sum(
        1
        for candidate in phone_candidates
        if "." not in candidate and 8 <= len(re.sub(r"\D", "", candidate)) <= 15
    )
    profile_link_hits = sum(
        1
        for marker in ("linkedin.com", "github.com", "portfolio", "behance.net")
        if marker in text_lower
    )
    contact_info = min(1.0, (email_hits + phone_hits + profile_link_hits) / 2.0)

    heading_hits = 0
    for line in text_lower.splitlines():
        normalized = re.sub(r"[^a-z\s]", " ", line).strip()
        normalized = re.sub(r"\s+", " ", normalized)
        if normalized in _RESUME_HEADING_PATTERNS:
            heading_hits += 1
    resume_headings = min(1.0, heading_hits / 3.0)

    work_date_hits = sum(len(pattern.findall(text)) for pattern in _DATE_PATTERNS)
    role_language_hits = len(
        re.findall(
            r"\b(?:engineer|developer|analyst|manager|designer|consultant|specialist|intern|lead|architect)\b",
            text_lower,
        )
    )
    employment_language = min(1.0, (work_date_hits + min(role_language_hits, 4)) / 5.0)

    return {
        "contact_info": round(contact_info, 4),
        "resume_headings": round(resume_headings, 4),
        "employment_language": round(employment_language, 4),
    }


def _compute_negative_signals(text: str, text_lower: str) -> dict[str, float]:
    legal_hits = sum(1 for t in _LEGAL_TERMS if t in text_lower)
    legal_language = min(1.0, legal_hits / 2.0)

    academic_hits = sum(1 for t in _ACADEMIC_TERMS if t in text_lower)
    citation_like = len(re.findall(r"\[[0-9]{1,3}\]", text))
    academic_paper = min(1.0, (academic_hits + min(citation_like, 4)) / 5.0)

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    long_paragraphs = [p for p in paragraphs if len(p.split()) >= 90]
    essay_markers_hits = sum(1 for t in _ESSAY_MARKERS if t in text_lower)
    essay_style = min(1.0, _safe_ratio(len(long_paragraphs), max(1, len(paragraphs))) + 0.25 * essay_markers_hits)

    invoice_hits = sum(1 for t in _INVOICE_TERMS if t in text_lower)
    currency_hits = len(re.findall(r"(₹|\$|€)\s?\d+", text))
    invoice_receipt = min(1.0, (invoice_hits + min(currency_hits, 3)) / 4.0)

    travel_hits = sum(1 for t in _TRAVEL_BOOKING_TERMS if t in text_lower)
    route_hits = len(re.findall(r"\b[A-Z]{3}\s*[-→]\s*[A-Z]{3}\b", text))
    travel_booking = min(1.0, (travel_hits + min(route_hits, 2)) / 4.0)

    guide_hits = sum(1 for t in _INSTALLATION_GUIDE_TERMS if t in text_lower)
    shell_command_hits = len(
        re.findall(r"(?m)^\s*(cd|chmod|git clone|mkdir|cp|ls|cat|nano|curl|source|uvx?|python|pip|npm)\b", text_lower)
    )
    path_hits = len(re.findall(r"(/home/|~/|\.config/|\.local/|\.json\b|\.appimage\b)", text_lower))
    installation_guide = min(1.0, (guide_hits + min(shell_command_hits, 5) + min(path_hits, 5)) / 8.0)

    learning_hits = sum(1 for t in _LEARNING_CONTENT_TERMS if t in text_lower)
    question_heading_hits = len(re.findall(r"(?m)^\s*(what|how|why|when)\b.+\?\s*$", text_lower))
    learning_notes = min(1.0, (learning_hits + min(question_heading_hits, 4)) / 8.0)

    feedback_hits = sum(1 for t in _FEEDBACK_DOCUMENT_TERMS if t in text_lower)
    chat_timestamp_hits = len(
        re.findall(r"\[\w*(?:day)?\s*\d{1,2}:\d{2}\s*(?:am|pm)\]", text_lower)
    )
    feedback_document = min(1.0, (feedback_hits + min(chat_timestamp_hits, 3)) / 5.0)

    code_hits = sum(text.count(t) for t in _CODE_TERMS)
    semicolons = text.count(";")
    code_heavy = min(1.0, (code_hits + min(semicolons, 20) / 5.0) / 20.0)

    agent_log_hits = sum(1 for t in _AGENT_CHANGE_LOG_TERMS if t in text_lower)
    agent_change_log = min(1.0, agent_log_hits / 3.0)

    form_hits = sum(1 for t in _FORM_TEMPLATE_TERMS if t in text_lower)
    form_template = min(1.0, form_hits / 3.0)

    return {
        "legal_language": round(legal_language, 4),
        "academic_paper": round(academic_paper, 4),
        "essay_style": round(essay_style, 4),
        "invoice_receipt": round(invoice_receipt, 4),
        "travel_booking": round(travel_booking, 4),
        "installation_guide": round(installation_guide, 4),
        "learning_notes": round(learning_notes, 4),
        "feedback_document": round(feedback_document, 4),
        "code_heavy": round(code_heavy, 4),
        "agent_change_log": round(agent_change_log, 4),
        "form_template": round(form_template, 4),
    }


def _weighted_total(scores: dict[str, float], weights: dict[str, float]) -> float:
    total = 0.0
    for key, weight in weights.items():
        total += scores.get(key, 0.0) * weight
    return round(total, 4)


def evaluate_resume_document(
    *,
    text: str,
    filename: Optional[str] = None,
    min_text_chars: int = RESUME_DETECTION_MIN_TEXT_CHARS,
) -> dict:
    lower_name = (filename or "").lower()
    allowed_type = (not lower_name) or lower_name.endswith((".pdf", ".docx"))

    text = (text or "").strip()
    language = detect_language_hint(text)

    layer_1_fail_reasons: list[str] = []
    if not allowed_type:
        layer_1_fail_reasons.append("Only PDF and DOCX files are supported.")
    if len(text) < min_text_chars:
        layer_1_fail_reasons.append(
            f"Document contains too little readable text ({len(text)} chars). Minimum is {min_text_chars}."
        )
    if not language:
        layer_1_fail_reasons.append("Could not detect document language from extracted text.")

    if layer_1_fail_reasons:
        return {
            "layer_1_pass": False,
            "layer_1_fail_reasons": layer_1_fail_reasons,
            "language": language,
            "text_length": len(text),
            "positive_signals": {},
            "negative_signals": {},
            "positive_resume_score": 0.0,
            "negative_score": 1.0,
            "confidence": 1.0,
            "final_label": "reject",
            "hard_reject": True,
            "decision_reason": "layer_1_sanity_failed",
            "warning_message": layer_1_fail_reasons[0],
        }

    text_lower = text.lower()
    positive_signals = _compute_positive_signals(text, text_lower)
    identity_signals = _compute_resume_identity_signals(text, text_lower)
    negative_signals = _compute_negative_signals(text, text_lower)
    positive_score = _weighted_total(positive_signals, RESUME_DETECTION_POSITIVE_WEIGHTS)
    negative_score = _weighted_total(negative_signals, RESUME_DETECTION_NEGATIVE_WEIGHTS)
    has_resume_identity = (
        identity_signals.get("contact_info", 0.0) >= 0.5
        or identity_signals.get("resume_headings", 0.0) >= 0.5
        or (
            identity_signals.get("employment_language", 0.0) >= 0.6
            and positive_signals.get("date_density", 0.0) > 0.0
        )
    )

    score_delta = positive_score - negative_score
    hard_reject = negative_score > (positive_score + RESUME_DETECTION_REJECT_MARGIN)
    # Strong template indicators should force reject for typical form templates
    if any(t in text_lower for t in _STRONG_FORM_TERMS):
        hard_reject = True

    if negative_signals.get("agent_change_log", 0.0) >= 0.67:
        hard_reject = True

    if (
        negative_signals.get("travel_booking", 0.0) >= 0.5
        and positive_signals.get("section_keywords", 0.0) <= 0.25
    ):
        hard_reject = True

    if (
        negative_signals.get("installation_guide", 0.0) >= 0.5
        and positive_signals.get("section_keywords", 0.0) <= 0.25
        and positive_signals.get("date_density", 0.0) == 0.0
    ):
        hard_reject = True

    if (
        negative_signals.get("code_heavy", 0.0) >= 0.85
        and positive_signals.get("section_keywords", 0.0) <= 0.25
        and positive_signals.get("date_density", 0.0) == 0.0
    ):
        hard_reject = True

    if (
        negative_signals.get("form_template", 0.0) >= 0.8
        and positive_signals.get("section_keywords", 0.0) <= 0.25
        and positive_signals.get("date_density", 0.0) == 0.0
    ):
        hard_reject = True

    if negative_signals.get("learning_notes", 0.0) >= 0.5 and not has_resume_identity:
        hard_reject = True

    if negative_signals.get("feedback_document", 0.0) >= 0.5 and not has_resume_identity:
        hard_reject = True

    if (
        not has_resume_identity
        and positive_signals.get("date_density", 0.0) == 0.0
        and len(text) >= 1200
        and positive_signals.get("section_keywords", 0.0) <= 0.25
    ):
        hard_reject = True

    # Co-occurrence rules: if student identifiers + date/problem appear together, force reject
    for a, b in _STRONG_CO_OCCURRENCE_PAIRS:
        if a in text_lower and b in text_lower:
            hard_reject = True
            break

    if hard_reject:
        final_label = "reject"
        if negative_signals.get("agent_change_log", 0.0) >= 0.67:
            warning_message = "Uploaded file appears to be a code-change or agent activity log rather than a resume."
            decision_reason = "agent_change_log_match"
        elif negative_signals.get("travel_booking", 0.0) >= 0.5:
            warning_message = "Uploaded file appears to be a travel receipt, booking confirmation, or itinerary rather than a resume."
            decision_reason = "travel_booking_match"
        elif negative_signals.get("installation_guide", 0.0) >= 0.5:
            warning_message = "Uploaded file appears to be an installation guide, manual, or troubleshooting document rather than a resume."
            decision_reason = "installation_guide_match"
        elif negative_signals.get("learning_notes", 0.0) >= 0.5:
            warning_message = "Uploaded file appears to be tutorial, course, or concept notes rather than a resume."
            decision_reason = "learning_notes_match"
        elif negative_signals.get("feedback_document", 0.0) >= 0.5:
            warning_message = "Uploaded file appears to be feedback, chat notes, or resume-screening guidance rather than a candidate resume."
            decision_reason = "feedback_document_match"
        elif negative_signals.get("code_heavy", 0.0) >= 0.85:
            warning_message = "Uploaded file appears to contain code or implementation notes rather than a resume."
            decision_reason = "code_heavy_without_resume_structure"
        elif negative_signals.get("form_template", 0.0) >= 0.8:
            warning_message = (
                "Uploaded file appears to be a form or evaluation template rather than a resume."
            )
            decision_reason = "strong_form_template_match"
        elif not has_resume_identity:
            warning_message = "Uploaded file does not contain enough resume identity signals such as contact info, resume headings, or work history dates."
            decision_reason = "missing_resume_identity"
        else:
            warning_message = (
                "Uploaded file appears to be a form or evaluation template rather than a resume."
            )
            decision_reason = "strong_form_template_match"
        return {
            "layer_1_pass": True,
            "layer_1_fail_reasons": [],
            "language": language,
            "text_length": len(text),
            "positive_signals": positive_signals,
            "resume_identity_signals": identity_signals,
            "negative_signals": negative_signals,
            "positive_resume_score": positive_score,
            "negative_score": negative_score,
            "confidence": 1.0,
            "final_label": final_label,
            "hard_reject": True,
            "decision_reason": decision_reason,
            "warning_message": warning_message,
        }

    # Additional rule: common notes/minutes/memo documents should be rejected
    # detect explicit note-like phrases
    notes_hits = sum(1 for t in _NOTES_TERMS if t in text_lower)
    notes_score = min(1.0, notes_hits / 3.0)
    if notes_score >= 0.5 and positive_score < 0.35:
        return {
            "layer_1_pass": True,
            "layer_1_fail_reasons": [],
            "language": language,
            "text_length": len(text),
            "positive_signals": positive_signals,
            "resume_identity_signals": identity_signals,
            "negative_signals": {**negative_signals, "notes": round(notes_score,4)},
            "positive_resume_score": positive_score,
            "negative_score": negative_score + round(notes_score,4),
            "confidence": 1.0,
            "final_label": "reject",
            "hard_reject": True,
            "decision_reason": "notes_template_match",
            "warning_message": "Uploaded file appears to be notes or meeting minutes rather than a resume.",
        }
    grace_hit = abs(score_delta) <= RESUME_DETECTION_GRACE_BAND

    if hard_reject:
        final_label = "reject"
        warning_message = (
            "Uploaded file strongly resembles a non-resume document (e.g., legal/invoice/code/academic content)."
        )
        decision_reason = "negative_signals_dominate"
    elif grace_hit:
        final_label = "accept_with_warning"
        warning_message = "This file looks unusual; results may be less accurate."
        decision_reason = "grace_zone"
    else:
        final_label = "accept"
        warning_message = None
        decision_reason = "resume_like_signals_sufficient"

    confidence = min(1.0, abs(score_delta) + 0.4)

    return {
        "layer_1_pass": True,
        "layer_1_fail_reasons": [],
        "language": language,
        "text_length": len(text),
        "positive_signals": positive_signals,
        "resume_identity_signals": identity_signals,
        "negative_signals": negative_signals,
        "positive_resume_score": positive_score,
        "negative_score": negative_score,
        "confidence": round(confidence, 4),
        "final_label": final_label,
        "hard_reject": hard_reject,
        "decision_reason": decision_reason,
        "warning_message": warning_message,
    }
