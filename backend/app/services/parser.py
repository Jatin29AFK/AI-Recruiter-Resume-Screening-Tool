import fitz  # PyMuPDF
from docx import Document
from typing import Optional
import re
from app.services.resume_detector import evaluate_resume_document


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
    """Compatibility wrapper around the layered resume detector.

    Returns (is_likely_resume, optional_warning_message).
    - accept and accept_with_warning are treated as likely resumes
    - reject returns False with a reason
    """
    decision = evaluate_resume_document(text=text)
    is_likely = decision.get("final_label") != "reject"
    warning = decision.get("warning_message")
    return is_likely, warning
