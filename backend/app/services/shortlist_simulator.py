def simulate_shortlist_outcome(
    scores: dict,
    critical_missing_skills: list[str],
    preferred_missing_skills: list[str],
    experience_comparison: dict,
    ats_audit: dict,
    keyword_coverage: dict,
) -> dict:
    reasons = []
    action_plan = []
    risk_points = 0

    critical_count = len(critical_missing_skills)

    if critical_count >= 4:
        reasons.append(
            f"Several must-have skills are still missing, especially: {', '.join(critical_missing_skills[:5])}."
        )
        action_plan.append(
            "Do not add missing required skills unless you genuinely have them. Strengthen adjacent evidence where valid."
        )
        risk_points += 3
    elif critical_count >= 2:
        reasons.append(
            f"Some important required skills are still missing, especially: {', '.join(critical_missing_skills[:4])}."
        )
        action_plan.append(
            "Improve alignment with the most important JD skills using real evidence from projects or experience."
        )
        risk_points += 2
    elif critical_count == 1:
        reasons.append(
            f"One important JD skill appears missing: {critical_missing_skills[0]}."
        )
        action_plan.append(
            "Check whether you already have valid evidence for this skill and surface it more clearly."
        )
        risk_points += 1

    required_skill_score = scores.get("required_skill_score", 0)
    if required_skill_score < 25:
        reasons.append(
            "Required skill coverage is currently weak — but check for transferable equivalents."
        )
        action_plan.append(
            "Highlight adjacent skills and experience that demonstrate readiness for key requirements."
        )
        risk_points += 1
    elif required_skill_score < 50:
        reasons.append(
            "Required skill coverage is partial — some important JD keywords may be missing."
        )
        action_plan.append(
            "Improve alignment with the most important required skills using real evidence."
        )
        risk_points += 1

    skill_support_score = scores.get("skill_support_score", 0)
    if skill_support_score < 30:
        reasons.append(
            "Matched skills are not strongly supported by project or experience evidence."
        )
        action_plan.append(
            "Rewrite bullets so important skills are backed by tools, actions, and outcomes."
        )
        risk_points += 1
    elif skill_support_score < 48:
        reasons.append(
            "Some matched skills need stronger evidence in your resume."
        )
        action_plan.append(
            "Add clearer evidence for the skills that matter most for this role."
        )
        risk_points += 1

    ats_score = ats_audit.get("score", 0)
    if ats_score < 60:
        reasons.append(
            "ATS formatting quality may reduce visibility in early screening."
        )
        action_plan.append(
            "Fix major formatting issues such as missing contact details or weak structure."
        )
        risk_points += 2
    elif ats_score < 75:
        reasons.append(
            "ATS formatting still has some room for improvement."
        )
        action_plan.append(
            "Clean up formatting and improve ATS readability where possible."
        )
        risk_points += 1

    if experience_comparison.get("meets_requirement") is False:
        reasons.append(
            "Estimated experience may appear below the JD requirement."
        )
        action_plan.append(
            "Highlight directly relevant roles, projects, and technical depth to reduce this gap."
        )
        risk_points += 1

    missing_required = [
        item["skill"] for item in keyword_coverage.get("items", [])
        if item["priority"] == "required" and item["status"] == "missing"
    ]
    if len(missing_required) >= 4:
        reasons.append(
            f"Several required JD keywords are still missing: {', '.join(missing_required[:5])}."
        )
        action_plan.append(
            "Add relevant keywords only where you genuinely have evidence, especially in experience and projects."
        )
        risk_points += 2
    elif len(missing_required) >= 2:
        reasons.append(
            f"Some required JD keywords are still missing: {', '.join(missing_required[:4])}."
        )
        action_plan.append(
            "Improve keyword alignment for the highest-priority requirements."
        )
        risk_points += 1

    if preferred_missing_skills:
        action_plan.append(
            f"Nice-to-have skills still missing include: {', '.join(preferred_missing_skills[:4])}."
        )

    overall_score = scores.get("overall_score", 0)

    # Thresholds loosened to reflect natural HR shortlisting:
    # Only "High risk" when there are truly many blockers AND score is low.
    if risk_points >= 10 or (risk_points >= 7 and overall_score < 38):
        verdict = "High rejection risk"
    elif risk_points >= 5:
        verdict = "Moderate rejection risk"
    else:
        verdict = "Lower rejection risk"

    if not reasons:
        reasons.append(
            "No major shortlist blockers were detected from the current screening signals."
        )

    if not action_plan:
        action_plan.append(
            "Keep the resume concise, evidence-backed, and closely aligned with the job description."
        )

    return {
        "verdict": verdict,
        "reasons": reasons[:5],
        "action_plan": action_plan[:5],
    }