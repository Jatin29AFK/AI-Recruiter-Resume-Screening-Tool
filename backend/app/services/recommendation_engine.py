"""
recommendation_engine.py
────────────────────────
Produces a structured recruiter recommendation:
  - section-wise scores with short explanations
  - key strengths  (3–5 bullet points)
  - relevant gaps / risks  (only material ones)
  - final recommendation  (Strongly Recommended / Recommended / Borderline / Not Recommended)
  - 2–3 line justification that is consistent with the score + decision

Scoring philosophy (aligned with the prompt requirements):
  • Transferable skills and real-world domain relevance are rewarded.
  • Minor missing tools do NOT trigger a gap note.
  • A "Recommended" verdict is possible even with a moderate overall score
    if the candidate has strong core skills and zero critical blockers.
"""

from __future__ import annotations


# ─────────────────────────────────────────────────────────────────────────────
# Section-wise scores
# ─────────────────────────────────────────────────────────────────────────────

def _section_scores(
    scores: dict,
    ats_audit: dict,
    evidence_summary: dict,
    experience_comparison: dict,
    critical_missing_skills: list[str],
) -> list[dict]:
    """Return a list of {name, score, explanation} dicts for the 5 key sections."""

    required_s = scores.get("required_skill_score", 0)
    semantic_s = scores.get("semantic_score", 0)
    evidence_s = scores.get("skill_support_score", 0)
    ats_s = ats_audit.get("score", 0)

    # Experience section score
    if experience_comparison.get("meets_requirement") is True:
        exp_score = min(100, 70 + max(0, 30 - len(critical_missing_skills) * 5))
        exp_note = "Estimated experience meets or exceeds the JD requirement."
    elif experience_comparison.get("meets_requirement") is False:
        gap_yrs = experience_comparison.get("gap_years") or 0
        exp_score = max(20, 55 - gap_yrs * 8)
        exp_note = f"Estimated experience appears {gap_yrs}y below the JD requirement — review work history for unlisted tenure."
    else:
        exp_score = 60
        exp_note = "Experience requirement could not be confirmed from the resume; review work dates manually."

    # Skills section score (required + preferred blend)
    preferred_s = scores.get("preferred_skill_score", 0)
    skills_score = round(0.70 * required_s + 0.30 * preferred_s)
    if len(critical_missing_skills) == 0:
        skills_note = "Covers the required JD skills well with no critical gaps."
    elif len(critical_missing_skills) <= 2:
        skills_note = f"Mostly covers required skills; {len(critical_missing_skills)} must-have gap(s): {', '.join(critical_missing_skills[:2])}."
    else:
        skills_note = f"{len(critical_missing_skills)} required skills absent — verify if transferable equivalents exist before rejecting."

    # Evidence / Content section
    strong_n = len(evidence_summary.get("strong_evidence_skills", []))
    medium_n = len(evidence_summary.get("medium_evidence_skills", []))
    if evidence_s >= 70:
        ev_note = f"{strong_n} skills backed by concrete project/work evidence — resume is well evidenced."
    elif evidence_s >= 45:
        ev_note = f"{strong_n} strongly evidenced, {medium_n} partially evidenced skills. Resume shows practical exposure."
    else:
        ev_note = "Skills are mostly listed without project/outcome context. Look for implied experience in the text before discounting."

    # Domain / Semantic fit
    if semantic_s >= 65:
        sem_note = "Resume language aligns closely with the JD domain — candidate is likely from a relevant background."
    elif semantic_s >= 45:
        sem_note = "Partial domain alignment; candidate may have transferable experience worth probing in interview."
    else:
        sem_note = "Resume language differs significantly from the JD. May be a domain switcher — assess core transferable skills."

    return [
        {"name": "Skills Coverage", "score": int(round(skills_score)), "explanation": skills_note},
        {"name": "Evidence & Impact", "score": int(round(evidence_s)), "explanation": ev_note},
        {"name": "Domain / Semantic Fit", "score": int(round(semantic_s)), "explanation": sem_note},
        {"name": "Experience Alignment", "score": int(round(exp_score)), "explanation": exp_note},
        {"name": "ATS Formatting", "score": int(round(ats_s)), "explanation": (
            "Resume passes ATS checks with minimal formatting issues." if ats_s >= 75
            else "Some ATS formatting issues present; content still evaluable." if ats_s >= 55
            else "Significant ATS formatting problems — manual review recommended to avoid false negatives."
        )},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Key strengths
# ─────────────────────────────────────────────────────────────────────────────

def _key_strengths(
    matched_skills: list[str],
    scores: dict,
    evidence_summary: dict,
    experience_comparison: dict,
    ats_audit: dict,
    critical_missing_skills: list[str],
) -> list[str]:
    strengths: list[str] = []

    strong_skills = evidence_summary.get("strong_evidence_skills", [])
    if strong_skills:
        strengths.append(
            f"Strong, evidenced skills: {', '.join(strong_skills[:5])}."
        )

    if scores.get("required_skill_score", 0) >= 65:
        strengths.append("Covers the majority of must-have JD requirements.")
    elif scores.get("required_skill_score", 0) >= 45 and len(critical_missing_skills) <= 1:
        strengths.append("Core required skills are present; only minor gaps.")

    if scores.get("semantic_score", 0) >= 55:
        strengths.append("Domain language closely matches the JD — candidate speaks the role's vocabulary.")

    if experience_comparison.get("meets_requirement") is True:
        strengths.append("Experience level meets or exceeds the JD requirement.")
    elif experience_comparison.get("meets_requirement") is None and experience_comparison.get("gap_years") is None:
        pass  # can't confirm — skip

    if ats_audit.get("score", 0) >= 75:
        strengths.append("Resume is clean and ATS-friendly — minimal formatting friction.")

    if scores.get("skill_support_score", 0) >= 65:
        strengths.append("Skills are backed by concrete project or work outcomes — not just listed.")

    if scores.get("general_skill_score", 0) >= 60:
        strengths.append("Broad general skill breadth relevant to the role.")

    # Ensure at least 2
    if len(strengths) < 2:
        if matched_skills:
            strengths.insert(0, f"Matches {len(matched_skills)} JD skill(s): {', '.join(matched_skills[:4])}.")
        if not strengths:
            strengths.append("Candidate has some domain-relevant experience worth exploring in interview.")

    return strengths[:5]


# ─────────────────────────────────────────────────────────────────────────────
# Gaps / Risks (material only)
# ─────────────────────────────────────────────────────────────────────────────

def _relevant_gaps(
    critical_missing_skills: list[str],
    scores: dict,
    experience_comparison: dict,
    ats_audit: dict,
    keyword_coverage: dict,
) -> list[str]:
    gaps: list[str] = []

    # Only flag critical skill gaps — not minor tools
    if len(critical_missing_skills) >= 3:
        gaps.append(
            f"Multiple must-have skills absent from resume: {', '.join(critical_missing_skills[:5])}. "
            "Verify whether equivalent hands-on experience exists."
        )
    elif len(critical_missing_skills) == 1:
        gaps.append(
            f"One required skill not evidenced: {critical_missing_skills[0]}. "
            "Confirm whether this was used but not listed."
        )
    elif len(critical_missing_skills) == 2:
        gaps.append(
            f"Two required skills not evidenced: {', '.join(critical_missing_skills)}. "
            "Worth clarifying in screening call."
        )

    if experience_comparison.get("meets_requirement") is False:
        gap_yrs = experience_comparison.get("gap_years") or 0
        if gap_yrs >= 2:
            gaps.append(
                f"Experience estimate is ~{gap_yrs}y below JD minimum. "
                "Review for unlisted tenure or equivalent intensity of work."
            )
        else:
            gaps.append(
                "Experience may be slightly below JD requirement — borderline; consider the depth of relevant work."
            )

    if scores.get("skill_support_score", 0) < 40:
        gaps.append(
            "Skills are mostly listed without supporting project/outcome context. "
            "Recommend asking for examples during interview."
        )

    if ats_audit.get("score", 0) < 50:
        gaps.append(
            "Resume has notable ATS formatting issues — content may not parse correctly in automated systems."
        )

    # Do NOT add minor tool gaps or preferred skill gaps — those are not material

    return gaps[:4]


# ─────────────────────────────────────────────────────────────────────────────
# Final recommendation
# ─────────────────────────────────────────────────────────────────────────────

def _final_recommendation(
    overall_score: float,
    critical_missing_skills: list[str],
    scores: dict,
    experience_comparison: dict,
    strengths: list[str],
    gaps: list[str],
) -> dict:
    """
    Returns {label, badge_color, justification} where label is one of:
      Strongly Recommended / Recommended / Borderline / Not Recommended

    Rule: the label MUST be consistent with overall_score.
    """
    required_s = scores.get("required_skill_score", 0)
    support_s = scores.get("skill_support_score", 0)
    n_critical = len(critical_missing_skills)
    exp_ok = experience_comparison.get("meets_requirement")

    # ── Decision logic ──────────────────────────────────────────────────────
    if overall_score >= 72 and n_critical == 0:
        label = "Strongly Recommended"
        badge = "green"
        just = (
            f"Strong overall match ({overall_score:.0f}%) with no critical skill gaps. "
            "The candidate covers the must-have JD requirements and demonstrates relevant domain experience. "
            "Recommend proceeding directly to a technical interview."
        )

    elif overall_score >= 60 and n_critical <= 2:
        label = "Recommended"
        badge = "green"
        reason_parts = []
        if n_critical == 0:
            reason_parts.append("covers all required skills")
        else:
            reason_parts.append(f"has {n_critical} minor required skill gap(s) that may be bridgeable")
        if support_s >= 55:
            reason_parts.append("skills backed by project evidence")
        just = (
            f"Good overall match ({overall_score:.0f}%). "
            f"Candidate {' and '.join(reason_parts)}. "
            "Suitable for a screening call to validate experience depth."
        )

    elif overall_score >= 45:
        label = "Borderline"
        badge = "yellow"
        if n_critical >= 3:
            reason = f"{n_critical} required skills are absent but the candidate shows {overall_score:.0f}% overall alignment"
        elif overall_score >= 55:
            reason = f"Score of {overall_score:.0f}% is decent but some required skills need verification"
        else:
            reason = f"Moderate match ({overall_score:.0f}%) — core skills present but coverage is incomplete"

        if exp_ok is False:
            reason += "; experience may fall short of JD minimum"

        extra = ""
        if required_s >= 50 and n_critical <= 2:
            extra = " Core required skills are largely present — interview could reveal compensating depth."
        elif support_s >= 55:
            extra = " Skills are evidenced well; gaps may be quickly learnable on the job."
        else:
            extra = " Recommend a brief phone screen to assess real-world experience before deciding."

        just = f"{reason}.{extra}"

    else:
        label = "Not Recommended"
        badge = "red"
        if n_critical >= 4:
            blocker = f"{n_critical} must-have skills are absent from the resume"
        elif required_s < 35:
            blocker = "required skill coverage is too low for this role"
        else:
            blocker = f"overall match of {overall_score:.0f}% is below the acceptable threshold"

        just = (
            f"Candidate does not meet the minimum bar — {blocker}. "
            "Unless there is a strong contextual reason to reconsider (e.g., exceptional referral), "
            "we suggest declining at this stage."
        )

    return {"label": label, "badge_color": badge, "justification": just}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_recommendation(
    scores: dict,
    matched_skills: list[str],
    critical_missing_skills: list[str],
    evidence_summary: dict,
    experience_comparison: dict,
    ats_audit: dict,
    keyword_coverage: dict,
) -> dict:
    """
    Build a full recruiter recommendation block.

    Returns:
        {
          section_scores: list[{name, score, explanation}],
          key_strengths: list[str],
          gaps_and_risks: list[str],
          final_recommendation: {label, badge_color, justification},
        }
    """
    overall = scores.get("overall_score", 0)

    section_scores = _section_scores(
        scores=scores,
        ats_audit=ats_audit,
        evidence_summary=evidence_summary,
        experience_comparison=experience_comparison,
        critical_missing_skills=critical_missing_skills,
    )

    strengths = _key_strengths(
        matched_skills=matched_skills,
        scores=scores,
        evidence_summary=evidence_summary,
        experience_comparison=experience_comparison,
        ats_audit=ats_audit,
        critical_missing_skills=critical_missing_skills,
    )

    gaps = _relevant_gaps(
        critical_missing_skills=critical_missing_skills,
        scores=scores,
        experience_comparison=experience_comparison,
        ats_audit=ats_audit,
        keyword_coverage=keyword_coverage,
    )

    recommendation = _final_recommendation(
        overall_score=overall,
        critical_missing_skills=critical_missing_skills,
        scores=scores,
        experience_comparison=experience_comparison,
        strengths=strengths,
        gaps=gaps,
    )

    return {
        "section_scores": section_scores,
        "key_strengths": strengths,
        "gaps_and_risks": gaps,
        "final_recommendation": recommendation,
    }
