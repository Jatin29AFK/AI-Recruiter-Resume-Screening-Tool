import re


def make_issue(title: str, severity: str, details: str, recommendation: str) -> dict:
    return {
        "title": title,
        "severity": severity,
        "details": details,
        "recommendation": recommendation,
    }


def has_quantified_bullet(bullets: list[str]) -> bool:
    pattern = r"(\d+%|\d+x|\d+\+|\d+\s*(ms|sec|seconds|minutes|hrs|hours|users|projects|models|apis|pipelines|clients|requests|records|resumes|candidates|k|m|mn|billion|million|thousand))"
    return any(re.search(pattern, bullet.lower()) for bullet in bullets)


_WEAK_OPENERS = (
    "responsible for",
    "helped ",
    "worked on",
    "assisted in",
    "was involved",
    "participated in",
    "support ",
    "tasked with",
    "duties included",
)

_STRONG_VERB_PATTERN = re.compile(
    r"^(built|created|designed|developed|implemented|led|managed|reduced|improved|"
    r"increased|achieved|delivered|launched|deployed|optimized|automated|integrated|"
    r"architected|engineered|established|streamlined|collaborated|coordinated|"
    r"analyzed|researched|trained|mentored|migrated|refactored|resolved|owned|"
    r"drove|scaled|shipped|generated|produced|executed|authored)",
    re.IGNORECASE,
)


def build_ats_audit(
    structured_resume: dict,
    critical_missing_skills: list[str] | None = None,
    filename: str = "",
) -> dict:
    """
    Comprehensive ATS audit.  Pass `critical_missing_skills` (from JD analysis) and
    `filename` so JD-specific keyword and file-format checks can run.
    """
    issues: list[dict] = []
    quick_fixes: list[str] = []
    score = 100

    full_name = structured_resume.get("full_name", "")
    email = structured_resume.get("email", "")
    phone = structured_resume.get("phone", "")
    summary = structured_resume.get("summary", "")
    skills = structured_resume.get("skills", [])
    experience_bullets = structured_resume.get("experience_bullets", [])
    project_bullets = structured_resume.get("project_bullets", [])
    linkedin = structured_resume.get("linkedin", "")
    github = structured_resume.get("github", "")
    all_bullets = experience_bullets + project_bullets

    # ── Contact information ──────────────────────────────────────────────────
    if not full_name:
        score -= 12
        issues.append(make_issue(
            "Missing candidate name",
            "high",
            "The resume header does not clearly expose the candidate name. "
            "ATS systems extract the name from the top of the document.",
            "Place your full name as the very first line of the resume.",
        ))

    if not email:
        score -= 10
        issues.append(make_issue(
            "Missing email address",
            "high",
            "No email address found. Recruiters cannot contact the candidate automatically.",
            "Add a professional email address in the header section.",
        ))

    if not phone:
        score -= 8
        issues.append(make_issue(
            "Missing phone number",
            "medium",
            "A phone number is expected in ATS-parsed contact sections.",
            "Add a phone number in the header below your name.",
        ))

    # ── File format ──────────────────────────────────────────────────────────
    if filename.lower().endswith(".docx"):
        score -= 5
        issues.append(make_issue(
            "DOCX format — potential parsing risk",
            "medium",
            "Many ATS platforms have trouble with DOCX files that use tables, columns, "
            "text boxes, or complex styles. Content inside those elements may be skipped entirely.",
            "Export a clean single-column PDF before submitting to job portals. "
            "Avoid tables and text boxes in your layout.",
        ))
        quick_fixes.append("Convert to a clean single-column PDF for ATS submission.")

    # ── Professional summary ─────────────────────────────────────────────────
    if not summary:
        score -= 8
        issues.append(make_issue(
            "Missing professional summary",
            "medium",
            "No professional summary/objective detected. "
            "ATS often extracts this section to classify the candidate's target role.",
            "Add a 2–4 sentence summary that names your role, top skills, and goal.",
        ))
        quick_fixes.append("Write a role-specific summary in 2–4 lines.")
    elif len(summary.strip()) < 80:
        score -= 5
        issues.append(make_issue(
            "Professional summary too brief",
            "medium",
            f"The summary is only {len(summary.strip())} characters — too short to signal "
            "role alignment to an ATS keyword scanner.",
            "Expand the summary to at least 2 full sentences covering your role, key skills, and value.",
        ))
    elif len(summary) > 600:
        score -= 4
        issues.append(make_issue(
            "Professional summary too long",
            "low",
            "A summary over 600 characters may bury key keywords or reduce recruiter readability.",
            "Trim the summary to 3–5 focused sentences.",
        ))

    # ── Skills section ───────────────────────────────────────────────────────
    if not skills:
        score -= 12
        issues.append(make_issue(
            "Missing skills section",
            "high",
            "ATS systems rely on an explicit skills section for keyword extraction. "
            "Without it, matched skills can drop significantly.",
            "Add a dedicated skills section listing tools, languages, and technologies.",
        ))
        quick_fixes.append("Add a dedicated skills section with relevant keywords.")
    elif len(skills) > 40:
        score -= 3
        issues.append(make_issue(
            "Overstuffed skills section",
            "low",
            f"The skills section lists {len(skills)} items. "
            "Padding with too many skills can trigger ATS keyword-stuffing filters "
            "and dilutes the relevance signal.",
            "Trim to the 20–30 most relevant skills for this role. Quality over quantity.",
        ))

    # ── Experience section ───────────────────────────────────────────────────
    if len(experience_bullets) < 2:
        score -= 10
        issues.append(make_issue(
            "Weak or missing experience section",
            "high",
            "Fewer than 2 experience bullets were found. ATS systems extract experience "
            "depth from this section to determine seniority and role fit.",
            "Add at least 4–6 achievement-focused bullets per role.",
        ))
        quick_fixes.append("Expand experience bullets with stronger evidence and outcomes.")
    elif len(experience_bullets) < 4:
        score -= 4
        issues.append(make_issue(
            "Sparse experience bullets",
            "medium",
            f"Only {len(experience_bullets)} experience bullet(s) detected. "
            "Strong candidates typically have 4–8 bullets per role.",
            "Add more bullets covering different skills, projects, and measurable achievements.",
        ))

    # ── Projects section ─────────────────────────────────────────────────────
    if len(project_bullets) < 2:
        score -= 5
        issues.append(make_issue(
            "Weak or missing projects section",
            "medium",
            "Fewer than 2 project bullets were found. Projects are key for technical roles "
            "where ATS scans for hands-on implementation evidence.",
            "Add project bullets describing tools used, what you built, and the outcome.",
        ))
        quick_fixes.append("Add project bullets that show tools, actions, and results.")

    # ── Bullet quality ───────────────────────────────────────────────────────
    long_bullets = [b for b in all_bullets if len(b) > 220]
    if long_bullets:
        score -= 5
        issues.append(make_issue(
            "Overlong bullet points",
            "medium",
            f"{len(long_bullets)} bullet(s) exceed 220 characters. "
            "Very long bullets are hard to scan and may wrap badly in ATS displays.",
            "Break long bullets into two focused sentences or separate bullets.",
        ))

    short_bullets = [b for b in experience_bullets if len(b.strip()) < 50]
    if len(short_bullets) >= 2:
        score -= 4
        issues.append(make_issue(
            "Underdeveloped bullets",
            "low",
            f"{len(short_bullets)} experience bullet(s) are under 50 characters — "
            "too short to demonstrate real impact or technical depth.",
            "Expand short bullets: add the tool used, the action taken, and a measurable outcome.",
        ))

    weak_bullets = [
        b for b in experience_bullets
        if any(b.lower().strip().startswith(phrase) for phrase in _WEAK_OPENERS)
    ]
    if weak_bullets:
        score -= 6
        examples = "; ".join(f'"{b[:60]}..."' for b in weak_bullets[:2])
        issues.append(make_issue(
            "Weak action verb usage",
            "medium",
            f"{len(weak_bullets)} bullet(s) start with passive phrases "
            f"(e.g. 'Responsible for', 'Helped', 'Worked on'). Example: {examples}. "
            "ATS and recruiters score bullet strength based on verb quality.",
            "Replace weak openers with strong past-tense action verbs: "
            "Built, Designed, Led, Improved, Reduced, Achieved, Deployed, Automated.",
        ))
        quick_fixes.append("Rewrite passive bullets to start with strong action verbs.")

    if all_bullets and not has_quantified_bullet(all_bullets):
        score -= 8
        issues.append(make_issue(
            "No quantified impact detected",
            "medium",
            "None of the bullets contain measurable results (numbers, %, x improvement, scale). "
            "ATS systems and recruiters give higher weight to proven, measurable impact.",
            "Add metrics to at least 3 bullets: user counts, latency reductions, accuracy %, "
            "scale (50k records), cost savings, or time saved.",
        ))
        quick_fixes.append("Rewrite at least 3 bullets with measurable outcomes (%, numbers, scale).")

    # ── JD keyword alignment ─────────────────────────────────────────────────
    if critical_missing_skills:
        count = len(critical_missing_skills)
        sev = "high" if count >= 4 else "medium"
        score -= min(count * 4, 18)
        sample = ", ".join(critical_missing_skills[:6])
        tail = f" (+{count - 6} more)" if count > 6 else ""
        issues.append(make_issue(
            f"{count} critical JD keyword{'s' if count > 1 else ''} absent from resume",
            sev,
            f"The following required skills from the job description were not detected "
            f"in the resume: {sample}{tail}. "
            "ATS systems scan for exact keyword matches against the JD — missing these "
            "can cause auto-rejection before a human ever reads the resume.",
            "Add each missing skill to the skills section if you have that knowledge, "
            "or embed it naturally inside experience/project bullets where accurate.",
        ))

    # ── Social / profile links ───────────────────────────────────────────────
    if not linkedin:
        score -= 2
        quick_fixes.append("Add a LinkedIn profile URL in the header.")

    if not github and any(kw in " ".join(skills).lower() for kw in ("python", "javascript", "react", "java", "code", "github")):
        score -= 2
        quick_fixes.append("Add a GitHub profile link — important for technical roles.")

    # ── Final scoring ────────────────────────────────────────────────────────
    score = max(0, min(score, 100))

    if score >= 85:
        grade = "Strong"
    elif score >= 70:
        grade = "Good"
    elif score >= 55:
        grade = "Fair"
    else:
        grade = "Weak"

    return {
        "score": score,
        "grade": grade,
        "issues": issues,
        "quick_fixes": quick_fixes[:8],
    }

    issues = []
    quick_fixes = []
    score = 100

    full_name = structured_resume.get("full_name", "")
    email = structured_resume.get("email", "")
    phone = structured_resume.get("phone", "")
    summary = structured_resume.get("summary", "")
    skills = structured_resume.get("skills", [])
    experience_bullets = structured_resume.get("experience_bullets", [])
    project_bullets = structured_resume.get("project_bullets", [])
    linkedin = structured_resume.get("linkedin", "")
    github = structured_resume.get("github", "")

    if not full_name:
        score -= 12
        issues.append(
            make_issue(
                "Missing name",
                "high",
                "The resume header does not clearly expose the candidate name.",
                "Place your full name clearly at the top of the resume.",
            )
        )

    if not email:
        score -= 10
        issues.append(
            make_issue(
                "Missing email",
                "high",
                "Recruiters may not be able to contact you quickly.",
                "Add a professional email address near the top of the resume.",
            )
        )

    if not phone:
        score -= 10
        issues.append(
            make_issue(
                "Missing phone number",
                "high",
                "A phone number is typically expected in resume contact details.",
                "Add a phone number in the header section.",
            )
        )

    if not summary:
        score -= 8
        issues.append(
            make_issue(
                "Missing professional summary",
                "medium",
                "The resume lacks a concise role-aligned summary.",
                "Add a short summary tailored to the target job.",
            )
        )

    if not skills:
        score -= 12
        issues.append(
            make_issue(
                "Missing skills section",
                "high",
                "ATS systems often rely on explicit skills sections.",
                "Add a dedicated skills section with relevant tools and technologies.",
            )
        )

    if len(experience_bullets) < 2:
        score -= 10
        issues.append(
            make_issue(
                "Weak experience section",
                "high",
                "The experience section has too few bullets to prove impact.",
                "Add more achievement-focused experience bullets.",
            )
        )

    if len(project_bullets) < 2:
        score -= 6
        issues.append(
            make_issue(
                "Weak project section",
                "medium",
                "The project section may not show enough depth.",
                "Add stronger project bullets with tools, actions, and outcomes.",
            )
        )

    long_bullets = [
        bullet for bullet in (experience_bullets + project_bullets)
        if len(bullet) > 220
    ]
    if long_bullets:
        score -= 6
        issues.append(
            make_issue(
                "Overlong bullets",
                "medium",
                "Some bullets are too long and may reduce readability.",
                "Shorten bullets and make each one focused on one impact story.",
            )
        )

    if summary and len(summary) > 500:
        score -= 5
        issues.append(
            make_issue(
                "Summary too long",
                "low",
                "A long summary may reduce clarity for recruiters.",
                "Keep the summary concise and target-role focused.",
            )
        )

    if not has_quantified_bullet(experience_bullets + project_bullets):
        score -= 8
        issues.append(
            make_issue(
                "Missing quantified impact",
                "medium",
                "The resume does not clearly show measurable results.",
                "Add numbers, percentages, scale, latency, usage, or improvement metrics where possible.",
            )
        )

    if not linkedin:
        score -= 2
        quick_fixes.append("Add LinkedIn profile link in the header.")

    if not github:
        score -= 2
        quick_fixes.append("Add GitHub profile link if relevant to the target role.")

    if not summary:
        quick_fixes.append("Write a role-specific summary in 2–4 lines.")
    if not has_quantified_bullet(experience_bullets + project_bullets):
        quick_fixes.append("Rewrite at least 3 bullets with measurable outcomes.")
    if len(experience_bullets) < 2:
        quick_fixes.append("Expand experience bullets with stronger evidence.")
    if len(project_bullets) < 2:
        quick_fixes.append("Add project bullets that show tools, actions, and results.")

    score = max(0, min(score, 100))

    if score >= 85:
        grade = "Strong"
    elif score >= 70:
        grade = "Good"
    elif score >= 55:
        grade = "Fair"
    else:
        grade = "Weak"

    return {
        "score": score,
        "grade": grade,
        "issues": issues,
        "quick_fixes": quick_fixes[:6],
    }