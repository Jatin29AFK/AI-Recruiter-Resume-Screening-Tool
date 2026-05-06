import json
from app.services.analyzer import analyze_resume_against_jd

# Load JDs
jobs = json.load(open("data/jobs.json"))
aiml_jd = jobs["5b15cd35-1352-4909-bf45-99f946d160cc"]["description"]
backend_jd = jobs["c60616ed-3b08-4ac3-bc0e-d4096e66e643"]["description"]

files = [
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/VINITHAK.pdf", "VINITHAK.pdf", aiml_jd),
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/VijayPrakash.pdf", "VijayPrakash.pdf", backend_jd),
]

results = []
for path, fn, jd in files:
    try:
        r = analyze_resume_against_jd(path, fn, jd, include_llm_explanation=False)
        summary = {
            "filename": r.get("filename"),
            "overall_score": r.get("scores", {}).get("overall_score"),
            "required_skill_score": r.get("scores", {}).get("required_skill_score"),
            "ats_score": r.get("ats_audit", {}).get("score"),
            "ats_issues": r.get("ats_audit", {}).get("issues"),
            "matched_skills": r.get("matched_skills"),
            "missing_skills": r.get("missing_skills")[:20],
            "critical_missing_skills": r.get("critical_missing_skills"),
            "experience_estimate": r.get("experience_estimate"),
            "experience_comparison": r.get("experience_comparison"),
            "non_negotiable_flags": r.get("non_negotiable_flags"),
            "timeline_analysis": r.get("timeline_analysis"),
        }
        results.append(summary)
    except Exception as e:
        results.append({"filename": fn, "error": str(e)})

print(json.dumps(results, indent=2))