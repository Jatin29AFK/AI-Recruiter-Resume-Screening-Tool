from app.services.parser import extract_resume_text, is_likely_resume_text
from app.services.preprocess import clean_text, lemmatize_text
from app.services.extractor import (
    extract_skills_from_text,
    categorize_extracted_skills,
    extract_skills_from_sections,
)
from app.services.section_parser import split_resume_into_sections
from app.services.jd_parser import parse_jd_requirements, extract_seniority_level
from app.services.domain_detector import detect_domain, choose_active_domain, build_reliability_meta
from app.services.matcher_engine import (
    exact_skill_match,
    missing_skill_match,
    fuzzy_skill_match,
    semantic_text_similarity,
    detect_critical_missing_skills,
    detect_preferred_missing_skills,
)
from app.services.evidence_validator import (
    validate_matched_skills_evidence,
    summarize_evidence_strength,
)
from app.services.experience_estimator import (
    estimate_total_experience_years,
    compare_with_jd_experience_requirement,
)
from app.services.scorer import calculate_match_score
from app.services.suggester import generate_resume_suggestions
from app.services.llm.llm_service import get_llm_provider
from app.services.llm.mock_llm import MockLLMProvider
from app.services.resume_structurer import structure_resume_for_tailoring
from app.services.ats_auditor import build_ats_audit
from app.services.keyword_coverage import build_keyword_coverage_report
from app.services.shortlist_simulator import simulate_shortlist_outcome
from app.services.recommendation_engine import build_recommendation
from app.services.career_analyzer import (
    analyze_leadership_signals,
    analyze_achievements,
    analyze_career_progression,
    detect_red_flags,
    analyze_industry_fit,
    analyze_language_quality,
    detect_over_tailoring,
    check_education_fit,
    analyze_timeline_gaps,
)
from app.services.cert_coverage_analyzer import build_certification_coverage_report


def _generate_llm_explanation(payload: dict) -> dict:
    try:
        llm_provider = get_llm_provider()
        return llm_provider.generate_explanation(payload)
    except Exception:
        fallback_provider = MockLLMProvider()
        return fallback_provider.generate_explanation(payload)


def analyze_resume_text_against_jd(
    resume_text: str,
    job_description: str,
    filename: str = "resume.txt",
    include_llm_explanation: bool = True,
) -> dict:
    # Quick resume-detection heuristic to surface non-resume uploads early
    is_likely_resume, resume_file_warning = is_likely_resume_text(resume_text)

    resume_sections = split_resume_into_sections(resume_text)

    cleaned_resume = clean_text(resume_text)
    cleaned_jd = clean_text(job_description)

    lemmatized_resume = lemmatize_text(cleaned_resume)
    lemmatized_jd = lemmatize_text(cleaned_jd)

    resume_domain = detect_domain(cleaned_resume)
    jd_domain = detect_domain(cleaned_jd)
    active_domain = choose_active_domain(resume_domain, jd_domain)
    active_domain_name = active_domain.get("domain")

    resume_skills = extract_skills_from_text(cleaned_resume, active_domain_name)

    jd_info = parse_jd_requirements(job_description, active_domain_name)
    required_skills = jd_info["required_skills"]
    preferred_skills = jd_info["preferred_skills"]
    general_skills = jd_info["general_skills"]
    jd_skills = jd_info["all_jd_skills"]
    experience_requirements = jd_info["experience_requirements"]
    education_requirements = jd_info["education_requirements"]

    # Include any 'one-of' required groups in the JD skills used for matching
    required_skill_groups = jd_info.get("required_skill_groups") or []
    flat_group_skills = [s for g in required_skill_groups for s in g] if required_skill_groups else []
    jd_skills_for_matching = sorted(set(jd_skills + flat_group_skills))

    categorized_resume_skills = categorize_extracted_skills(resume_skills, active_domain_name)
    categorized_jd_skills = categorize_extracted_skills(jd_skills, active_domain_name)

    cleaned_section_map = {
        section: clean_text(text)
        for section, text in resume_sections.items()
    }
    section_skill_map = extract_skills_from_sections(cleaned_section_map, active_domain_name)

    matched_skills = exact_skill_match(resume_skills, jd_skills_for_matching)
    missing_skills = missing_skill_match(resume_skills, jd_skills_for_matching)
    fuzzy_matches = fuzzy_skill_match(resume_skills, jd_skills_for_matching)

    semantic_score = semantic_text_similarity(lemmatized_resume, lemmatized_jd)

    critical_missing_skills = detect_critical_missing_skills(
        required_skills,
        missing_skills,
        required_skill_groups=required_skill_groups,
    )
    preferred_missing_skills = detect_preferred_missing_skills(preferred_skills, missing_skills)

    skill_evidence_map = validate_matched_skills_evidence(matched_skills, resume_sections)
    evidence_summary = summarize_evidence_strength(skill_evidence_map)

    experience_text = resume_sections.get("experience", "")
    experience_estimate = estimate_total_experience_years(
        experience_text,
        full_resume_text=resume_text,
        summary_text=resume_sections.get("summary", ""),
    )
    experience_comparison = compare_with_jd_experience_requirement(
        estimated_resume_years=experience_estimate["estimated_years"],
        min_required_years=experience_requirements.get("min_years_experience"),
        max_required_years=experience_requirements.get("max_years_experience"),
    )


    # Always define structured_resume, even if resume parsing fails
    try:
        structured_resume = structure_resume_for_tailoring({
            "resume_sections": resume_sections,
            "resume_skills": resume_skills,
            "raw_resume_text": resume_text,
        })
    except Exception:
        structured_resume = {"experience_bullets": [], "project_bullets": []}

    # New recruiter-focused analysis
    experience_bullets = structured_resume.get("experience_bullets", [])
    project_bullets = structured_resume.get("project_bullets", [])

    seniority_level = jd_info.get("seniority_level", "mid")

    leadership_signals = analyze_leadership_signals(resume_text, experience_bullets)
    achievements_analysis = analyze_achievements(experience_bullets, project_bullets)
    career_progression = analyze_career_progression(
        resume_text,
        experience_estimate.get("estimated_years") or 0,
        experience_section=resume_sections.get("experience", ""),
    )
    red_flags = detect_red_flags(
        resume_text,
        experience_bullets,
        experience_section=resume_sections.get("experience", ""),
        education_section=resume_sections.get("education", ""),
    )
    timeline_analysis = analyze_timeline_gaps(
        resume_sections.get("experience", ""),
        resume_sections.get("education", ""),
    )
    industry_fit = analyze_industry_fit(resume_text, active_domain_name, matched_skills, jd_skills)
    language_quality = analyze_language_quality(resume_text, experience_bullets, seniority_level)
    education_fit = check_education_fit(resume_sections, education_requirements)

    cert_coverage = build_certification_coverage_report(
        jd_required_skills=required_skills,
        jd_preferred_skills=preferred_skills,
        resume_sections=resume_sections,
        raw_resume_text=resume_text,
    )

    # Get scoring weights from JD requirements if available
    scoring_weights = None
    if jd_info.get("scoring_weights"):
        scoring_weights = {
            'must_have_match': jd_info["scoring_weights"].get("must_have_match", 0.40),
            'relevant_experience': jd_info["scoring_weights"].get("relevant_experience", 0.20),
            'preferred_skills': jd_info["scoring_weights"].get("preferred_skills", 0.15),
            'achievements_impact': jd_info["scoring_weights"].get("achievements_impact", 0.10),
            'industry_fit': jd_info["scoring_weights"].get("industry_fit", 0.10),
            'career_progression': jd_info["scoring_weights"].get("career_progression", 0.05),
        }

    scores = calculate_match_score(
        matched_skills=matched_skills,
        semantic_score=semantic_score,
        section_skill_map=section_skill_map,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        general_skills=general_skills,
        critical_missing_skills=critical_missing_skills,
        skill_support_score=evidence_summary["skill_support_score"],
        career_progression_score=career_progression["score"],
        achievements_score=achievements_analysis["score"],
        industry_fit_score=industry_fit["score"],
        scoring_weights=scoring_weights,
        required_skill_groups=jd_info.get("required_skill_groups"),
    )

    suggestions = generate_resume_suggestions(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        critical_missing_skills=critical_missing_skills,
        preferred_missing_skills=preferred_missing_skills,
        scores=scores,
        section_skill_map=section_skill_map,
        experience_requirements=experience_requirements,
        education_requirements=education_requirements,
        evidence_summary=evidence_summary,
        experience_comparison=experience_comparison,
    )

    ats_audit = build_ats_audit(
        structured_resume,
        critical_missing_skills=critical_missing_skills,
        filename=filename,
    )

    keyword_coverage = build_keyword_coverage_report(
        jd_requirements={
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "general_skills": general_skills,
        },
        evidence_summary=evidence_summary,
        skill_evidence_map=skill_evidence_map,
        missing_skills=missing_skills,
    )

    shortlist_simulation = simulate_shortlist_outcome(
        scores=scores,
        critical_missing_skills=critical_missing_skills,
        preferred_missing_skills=preferred_missing_skills,
        experience_comparison=experience_comparison,
        ats_audit=ats_audit,
        keyword_coverage=keyword_coverage,
    )

    analysis_meta = build_reliability_meta(
        resume_domain=resume_domain,
        jd_domain=jd_domain,
        resume_skills_count=len(resume_skills),
        jd_skills_count=len(jd_skills),
    )
    analysis_meta["active_domain"] = active_domain

    llm_explanation = None
    if include_llm_explanation:
        llm_explanation = _generate_llm_explanation(
            {
                "filename": filename,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "critical_missing_skills": critical_missing_skills,
                "preferred_missing_skills": preferred_missing_skills,
                "scores": scores,
                "jd_requirements": {
                    "required_skills": required_skills,
                    "preferred_skills": preferred_skills,
                    "general_skills": general_skills,
                    "experience_requirements": experience_requirements,
                    "education_requirements": education_requirements,
                },
                "suggestions": suggestions,
                "analysis_meta": analysis_meta,
            }
        )

    recommendation = build_recommendation(
        scores=scores,
        matched_skills=matched_skills,
        critical_missing_skills=critical_missing_skills,
        evidence_summary=evidence_summary,
        experience_comparison=experience_comparison,
        ats_audit=ats_audit,
        keyword_coverage=keyword_coverage,
    )

    # Add recruiter-focused signals to scores for easier access
    scores["leadership_signals"] = leadership_signals
    scores["red_flags"] = red_flags
    scores["over_tailoring_flag"] = detect_over_tailoring(
        required_skill_score=scores.get("required_skill_score", 0),
        overall_score=scores.get("overall_score", 0),
        resume_text=resume_text,
    )
    scores["language_quality"] = language_quality

    # Non-negotiable advisory flags (informational only, do not auto-reject)
    non_negotiable_flags: list[str] = []
    req_score = scores.get("required_skill_score", 0)
    if required_skills and req_score == 0:
        non_negotiable_flags.append(
            "No required skills matched — verify if relevant experience exists under different terminology."
        )
    elif required_skills and len(critical_missing_skills) > len(required_skills) // 2 and len(critical_missing_skills) >= 3:
        non_negotiable_flags.append(
            f"{len(critical_missing_skills)} of {len(required_skills)} required skills not matched "
            "— review for unlisted equivalents before rejecting."
        )
    if experience_comparison.get("meets_requirement") is False:
        gap = abs(experience_comparison.get("gap_years") or 0)
        if gap >= 2:
            non_negotiable_flags.append(
                experience_comparison.get("message", f"Experience ~{gap}y below JD minimum")
                + " — confirm whether depth/intensity of work compensates for years."
            )
    if education_fit.get("meets_requirement") is False and education_requirements:
        non_negotiable_flags.append(
            f"Education: JD requires {', '.join(education_requirements[:3])} "
            "— not clearly evidenced in resume. Verify manually."
        )

    return {
        "filename": filename,
        "raw_resume_text": resume_text,
        "resume_sections": resume_sections,
        "structured_resume": structured_resume,
        "section_skill_map": section_skill_map,
        "resume_skills": resume_skills,
        "jd_requirements": {
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "general_skills": general_skills,
            "required_skill_groups": jd_info.get("required_skill_groups"),
            "experience_requirements": experience_requirements,
            "education_requirements": education_requirements,
        },
        "categorized_resume_skills": categorized_resume_skills,
        "categorized_jd_skills": categorized_jd_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "critical_missing_skills": critical_missing_skills,
        "preferred_missing_skills": preferred_missing_skills,
        "fuzzy_matches": fuzzy_matches,
        "skill_evidence_map": skill_evidence_map,
        "evidence_summary": evidence_summary,
        "experience_estimate": experience_estimate,
        "experience_comparison": experience_comparison,
        "scores": scores,
        "suggestions": suggestions,
        "llm_explanation": llm_explanation,
        "ats_audit": ats_audit,
        "keyword_coverage": keyword_coverage,
        "shortlist_simulation": shortlist_simulation,
        "analysis_meta": analysis_meta,
        "resume_domain": resume_domain,
        "jd_domain": jd_domain,
        "recommendation": recommendation,
        "education_fit": education_fit,
        "non_negotiable_flags": non_negotiable_flags,
        "seniority_level": seniority_level,
        "timeline_analysis": timeline_analysis,
        "is_likely_resume": is_likely_resume,
        "resume_file_warning": resume_file_warning,
        "cert_coverage": cert_coverage,
    }


def analyze_resume_against_jd(
    file_path: str,
    filename: str,
    job_description: str,
    include_llm_explanation: bool = True,
) -> dict:
    resume_text = extract_resume_text(file_path, filename)
    return analyze_resume_text_against_jd(
        resume_text=resume_text,
        job_description=job_description,
        filename=filename,
        include_llm_explanation=include_llm_explanation,
    )
