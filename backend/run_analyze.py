# run_analyze.py
import json
from app.services.analyzer import analyze_resume_against_jd

# Load JDs
jobs = json.load(open("data/jobs.json"))
aiml_jd = jobs["5b15cd35-1352-4909-bf45-99f946d160cc"]["description"]
backend_jd = jobs["c60616ed-3b08-4ac3-bc0e-d4096e66e643"]["description"]

files = [
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/VINITHAK.pdf", "VINITHAK.pdf", aiml_jd),
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/VijayPrakash.pdf", "VijayPrakash.pdf", backend_jd),
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/arjun_sharma_STRONG_FIT.docx", "arjun_sharma_STRONG_FIT.docx", aiml_jd),
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/priya_mehta_AVERAGE_FIT.docx", "priya_mehta_AVERAGE_FIT.docx", aiml_jd),
    ("/home/jatin/Documents/AI Resume Matcher/ai-resume-matcher GC MAIN/sample-resumes/rohan_verma_LOW_FIT.docx", "rohan_verma_LOW_FIT.docx", aiml_jd),
]

results = []
for path, fn, jd in files:
    try:
        # Run in default mode to verify natural shortlisting behaviour
        r = analyze_resume_against_jd(path, fn, jd, include_llm_explanation=False)
        summary = {
            "filename": r.get("filename"),
            "overall_score": r.get("scores", {}).get("overall_score"),
            "fit_label": r.get("scores", {}).get("fit_label"),
            "required_skill_score": r.get("scores", {}).get("required_skill_score"),
            "general_skill_score": r.get("scores", {}).get("general_skill_score"),
            "semantic_score": r.get("scores", {}).get("semantic_score"),
            "skill_support_score": r.get("scores", {}).get("skill_support_score"),
            "ats_score": r.get("ats_audit", {}).get("score"),
            "matched_skills": r.get("matched_skills"),
            "critical_missing_skills": r.get("critical_missing_skills"),
            "non_negotiable_flags": r.get("non_negotiable_flags"),
            "shortlist_verdict": r.get("shortlist_simulation", {}).get("verdict"),
        }
        results.append(summary)
    except Exception as e:
        results.append({"filename": fn, "error": str(e)})

print(json.dumps(results, indent=2))