from app.services.analyzer import analyze_resume_text_against_jd
from app.services.parser import extract_resume_text


def infer_jd_title(job_description: str, analysis_result: dict, index: int) -> str:
    lines = [line.strip() for line in job_description.splitlines() if line.strip()]
    if lines:
        first = lines[0]
        if len(first) <= 100:
            return first

    required_skills = analysis_result.get("jd_requirements", {}).get("required_skills", [])
    if required_skills:
        return f"JD {index}: " + ", ".join(required_skills[:3])

    return f"JD {index}"


def _quick_recommendation_verdict(overall_score: float, critical_missing_count: int) -> str:
    """
    Lightweight recommendation label for multi-JD comparison.
    Mirrors the threshold logic in recommendation_engine._final_recommendation()
    without the full report overhead.
    """
    if overall_score >= 72 and critical_missing_count == 0:
        return "Strongly Recommended"
    elif overall_score >= 60 and critical_missing_count <= 2:
        return "Recommended"
    elif overall_score >= 45:
        return "Borderline"
    return "Not Recommended"


def compare_resume_against_multiple_jds(
    file_path: str,
    filename: str,
    job_descriptions: list[str],
) -> dict:
    resume_text = extract_resume_text(file_path, filename)

    comparisons = []
    for index, jd in enumerate(job_descriptions, start=1):
        analysis = analyze_resume_text_against_jd(
            resume_text=resume_text,
            job_description=jd,
            filename=filename,
            include_llm_explanation=False,
        )

        overall_score = analysis["scores"]["overall_score"]
        critical_missing = analysis["critical_missing_skills"]

        comparisons.append(
            {
                "jd_index": index,
                "jd_title": infer_jd_title(jd, analysis, index),
                "overall_score": overall_score,
                "fit_label": analysis["scores"]["fit_label"],
                "required_skill_score": analysis["scores"]["required_skill_score"],
                "skill_support_score": analysis["scores"]["skill_support_score"],
                "critical_missing_skills": critical_missing,
                "matched_skills": analysis["matched_skills"][:8],
                "recommendation_verdict": _quick_recommendation_verdict(overall_score, len(critical_missing)),
            }
        )

    comparisons.sort(key=lambda item: item["overall_score"], reverse=True)

    return {
        "resume_filename": filename,
        "comparisons": comparisons,
        "best_match": comparisons[0] if comparisons else None,
    }