import unittest

from app.services.non_negotiable_evaluator import evaluate_non_negotiables


def _analysis(
    *,
    resume_skills=None,
    estimated_years=5.0,
    education="Bachelor of Technology in Computer Science",
    certifications="",
    summary="",
    raw_resume_text="",
):
    return {
        "resume_skills": resume_skills or ["python", "sql"],
        "resume_sections": {
            "education": education,
            "certifications": certifications,
            "summary": summary,
            "other": "",
        },
        "experience_estimate": {
            "estimated_years": estimated_years,
        },
        "analysis_meta": {
            "active_domain": {
                "domain": "backend",
            }
        },
        "raw_resume_text": raw_resume_text or "\n".join(
            part for part in [education, certifications, summary] if part
        ),
    }


class NonNegotiableEvaluatorTest(unittest.TestCase):
    def test_saved_job_missing_required_skill_forces_reject(self):
        result = evaluate_non_negotiables(
            analysis=_analysis(resume_skills=["python"]),
            job_description="Backend engineer role",
            saved_job={
                "required_skills": ["python", "sql"],
                "min_experience": None,
                "education_requirements": [],
                "mandatory_certifications": [],
            },
        )

        self.assertEqual("reject", result["non_negotiable_verdict"])
        self.assertTrue(result["hard_reject"])
        self.assertIn("sql", " ".join(result["hard_reject_reasons"]).lower())

    def test_saved_job_min_experience_forces_reject(self):
        result = evaluate_non_negotiables(
            analysis=_analysis(estimated_years=2.0),
            job_description="Backend engineer role",
            saved_job={
                "required_skills": [],
                "min_experience": 4,
                "education_requirements": [],
                "mandatory_certifications": [],
            },
        )

        self.assertEqual("reject", result["non_negotiable_verdict"])
        self.assertIn("below the required minimum", " ".join(result["hard_reject_reasons"]).lower())

    def test_saved_job_education_missing_can_force_reject(self):
        result = evaluate_non_negotiables(
            analysis=_analysis(education="Bachelor of Commerce from State University"),
            job_description="Backend engineer role",
            saved_job={
                "required_skills": [],
                "min_experience": None,
                "education_requirements": ["Computer Science"],
                "mandatory_certifications": [],
            },
        )

        self.assertEqual("reject", result["non_negotiable_verdict"])
        self.assertIn("required education", " ".join(result["hard_reject_reasons"]).lower())

    def test_saved_job_missing_mandatory_certification_forces_reject(self):
        result = evaluate_non_negotiables(
            analysis=_analysis(certifications="Oracle Certified Associate"),
            job_description="Backend engineer role",
            saved_job={
                "required_skills": [],
                "min_experience": None,
                "education_requirements": [],
                "mandatory_certifications": ["AWS Certified Developer"],
            },
        )

        self.assertEqual("reject", result["non_negotiable_verdict"])
        self.assertIn("certification", " ".join(result["hard_reject_reasons"]).lower())

    def test_parsed_jd_missing_explicit_required_skill_forces_reject(self):
        jd = """
        Job Description
        Must have:
        Python
        SQL
        """
        result = evaluate_non_negotiables(
            analysis=_analysis(resume_skills=["python"]),
            job_description=jd,
            saved_job=None,
        )

        self.assertEqual("reject", result["non_negotiable_verdict"])
        self.assertIn("sql", " ".join(result["hard_reject_reasons"]).lower())

    def test_parsed_jd_education_mismatch_becomes_review_flag(self):
        jd = """
        Job Description
        Must have:
        Python
        Computer Science
        """
        result = evaluate_non_negotiables(
            analysis=_analysis(education="Bachelor of Commerce from State University"),
            job_description=jd,
            saved_job=None,
        )

        self.assertEqual("review", result["non_negotiable_verdict"])
        self.assertFalse(result["hard_reject"])
        self.assertGreater(len(result["review_flags"]), 0)
        self.assertIn("education", " ".join(result["review_flags"]).lower())

    def test_saved_job_rules_take_precedence_over_parsed_jd(self):
        jd = """
        Job Description
        Must have:
        Python
        """
        result = evaluate_non_negotiables(
            analysis=_analysis(resume_skills=["python"]),
            job_description=jd,
            saved_job={
                "required_skills": ["python", "sql"],
                "min_experience": None,
                "education_requirements": [],
                "mandatory_certifications": [],
            },
        )

        self.assertEqual("saved_job", result["evaluated_rules"]["source"])
        self.assertEqual("reject", result["non_negotiable_verdict"])
        self.assertIn("sql", " ".join(result["hard_reject_reasons"]).lower())

    def test_parsed_jd_required_skill_groups_respect_one_of_logic(self):
        jd = """
        Job Description
        Must have:
        Excellent in at least one of the programming languages and frameworks listed below:
        o Most preferred: javascript and node js, python with flask
        """
        result = evaluate_non_negotiables(
            analysis=_analysis(resume_skills=["python", "flask"]),
            job_description=jd,
            saved_job=None,
        )

        self.assertEqual("pass", result["non_negotiable_verdict"])
        self.assertEqual([], result["hard_reject_reasons"])

    def test_parsed_jd_optional_certification_not_added_to_non_negotiables(self):
        jd = """
        Job Description
        Requirements:
        Python
        AWS certification is preferred and good to have
        """
        result = evaluate_non_negotiables(
            analysis=_analysis(certifications=""),
            job_description=jd,
            saved_job=None,
        )

        self.assertEqual("pass", result["non_negotiable_verdict"])
        self.assertEqual([], result["hard_reject_reasons"])
        self.assertFalse(
            any("certification" in flag.lower() for flag in result["review_flags"])
        )

    def test_parsed_jd_required_certification_added_to_non_negotiables(self):
        jd = """
        Job Description
        Mandatory Certification: AWS Certified Developer
        """
        result = evaluate_non_negotiables(
            analysis=_analysis(resume_skills=["python", "sql", "aws"], certifications=""),
            job_description=jd,
            saved_job=None,
        )

        self.assertEqual("review", result["non_negotiable_verdict"])
        self.assertFalse(result["hard_reject"])
        self.assertTrue(
            any("certification" in flag.lower() for flag in result["review_flags"])
        )


if __name__ == "__main__":
    unittest.main()
