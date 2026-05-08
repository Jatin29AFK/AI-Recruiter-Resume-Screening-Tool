import fitz  # PyMuPDF
from docx import Document
from typing import Optional
import re


def extract_text_from_pdf(file_path: str) -> str:
    text = []
    annotation_urls: list[str] = []
    pdf = fitz.open(file_path)
    for page in pdf:
        text.append(page.get_text("text", sort=True))
        for link in page.get_links():
            uri = link.get("uri", "")
            if uri and uri.startswith(("http://", "https://")):
                annotation_urls.append(uri)
    pdf.close()
    base = "\n".join(text).strip()
    # Append any annotation URLs not already present in the text so that
    # the downstream LinkedIn/GitHub regex can always find the full URL.
    unique_urls = []
    for url in dict.fromkeys(annotation_urls):   # deduplicate, preserve order
        if url not in base:
            unique_urls.append(url)
    if unique_urls:
        base = base + "\n" + "\n".join(unique_urls)
    return base


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    text = [para.text for para in doc.paragraphs if para.text.strip()]
    base = "\n".join(text).strip()
    # Also collect hyperlinks stored in the document relationships (e.g. LinkedIn
    # clickable links whose display text is just an icon or the word "LinkedIn").
    try:
        rels = doc.part.rels
        annotation_urls = [
            rel.target_ref
            for rel in rels.values()
            if rel.reltype.endswith("/hyperlink")
            and rel.target_ref.startswith(("http://", "https://"))
            and rel.target_ref not in base
        ]
        if annotation_urls:
            base = base + "\n" + "\n".join(dict.fromkeys(annotation_urls))
    except Exception:
        pass
    return base


def extract_resume_text(file_path: str, filename: str) -> str:
    filename = filename.lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Only PDF and DOCX are allowed.")


def is_likely_resume_text(text: str) -> tuple[bool, Optional[str]]:
    """Strict heuristic: a file is accepted as a resume ONLY when:
      1. At least 2 of the 3 required section headings (Experience, Education,
         Skills) appear as STANDALONE short lines (not inside sentences).
      2. Contact info (email OR phone number) is present somewhere in the file.

    Returns (is_likely_resume, optional_warning_message).
    No length-only fallback — that was the source of false positives.
    """
    if not text or not text.strip():
        return False, (
            "Uploaded file appears empty or contains no readable text. "
            "Please upload a PDF or DOCX resume."
        )

    # ── Contact info ────────────────────────────────────────────────────────
    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    # phone: must have at least 10 actual digits (filters out year ranges like 2020-2022)
    def _has_phone(t: str) -> bool:
        for m in re.finditer(r"(?<!\d)(\+?\d[\d\s\-\(\)\.]{6,20}\d)(?!\d)", t):
            if len(re.sub(r"\D", "", m.group())) >= 10:
                return True
        return False
    contact_present = bool(email_match or _has_phone(text))

    # ── Standalone heading detection ─────────────────────────────────────────
    # A resume section heading is a SHORT line (≤ 55 chars) that IS the heading,
    # not a sentence that merely contains the word.
    # Also strip leading bullet/dash/hash chars before matching.
    heading_patterns = {
        "experience": re.compile(
            r"^(work\s+|professional\s+|relevant\s+|employment\s+)?experience[s]?(\s*[:\-\|].*)?$",
            re.IGNORECASE,
        ),
        "education": re.compile(
            r"^(academic\s+|educational?\s+)?education(al)?(\s+background)?(\s*[:\-\|].*)?$",
            re.IGNORECASE,
        ),
        "skills": re.compile(
            r"^(technical\s+|key\s+|core\s+|professional\s+|hard\s+|soft\s+)?skills?(\s*[&/\-\|:].*)?$",
            re.IGNORECASE,
        ),
    }

    _STRIP_LEADING = re.compile(r"^[\s\-\*\•\#\>]+")

    found_headings: set[str] = set()
    for raw_line in text.splitlines():
        stripped = _STRIP_LEADING.sub("", raw_line).strip()
        # Heading lines must be short — long lines are sentences, not headings
        if not stripped or len(stripped) > 55:
            continue
        for hk, pattern in heading_patterns.items():
            if pattern.match(stripped):
                found_headings.add(hk)

    headings_found = len(found_headings)

    parsed_section_names: set[str] = set()
    try:
        from app.services.section_parser import split_resume_into_sections

        parsed_sections = split_resume_into_sections(text)
        for section_name in ("experience", "education", "skills", "projects", "certifications"):
            section_text = parsed_sections.get(section_name, "").strip()
            min_len = 40 if section_name in {"experience", "education", "skills"} else 80
            if len(section_text) >= min_len:
                parsed_section_names.add(section_name)
    except Exception:
        parsed_section_names = set()

    # ── Decision ─────────────────────────────────────────────────────────────
    # All three headings + contact  →  clear resume
    # Two of three headings + contact  →  likely resume (some resumes omit one)
    if headings_found >= 2 and contact_present:
        return True, None

    has_core_resume_sections = (
        "experience" in parsed_section_names
        and (
            "skills" in parsed_section_names
            or "education" in parsed_section_names
            or "projects" in parsed_section_names
        )
    )
    if contact_present and (len(parsed_section_names) >= 3 or has_core_resume_sections):
        return True, None

    # Build a specific, actionable message
    if headings_found >= 2 and not contact_present:
        return False, (
            "Uploaded file looks like it may be a resume, but it is missing "
            "contact information (email or phone number). Please add your "
            "contact details and re-upload."
        )

    missing_headings = {"Experience", "Education", "Skills"} - {h.title() for h in found_headings}
    if missing_headings and not contact_present:
        return False, (
            "Uploaded file does not appear to be a resume. "
            f"Missing section headings: {', '.join(sorted(missing_headings))}. "
            "Also add contact information (email or phone). "
            "Please upload a proper PDF or DOCX resume."
        )

    return False, (
        "Uploaded file does not appear to be a resume. "
        f"Could not find clear section headings for: "
        f"{', '.join(sorted(missing_headings or {'Experience', 'Education', 'Skills'}))}. "
        "Resumes must have standalone headings for Experience, Education, and Skills "
        "plus contact details (email or phone)."
    )
