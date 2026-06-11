import unittest

from app.services.jd_guardrails import validate_job_description_input


class JdGuardrailsTest(unittest.TestCase):
    def test_rejects_blank_input_with_clear_message(self):
        with self.assertRaises(ValueError) as ctx:
            validate_job_description_input("   \n\t  ")

        self.assertEqual("Please paste a job description first.", str(ctx.exception))

    def test_accepts_concise_but_real_jd(self):
        jd = """
        Hiring: Backend Developer
        Responsibilities: Build APIs, maintain services, write unit tests.
        Requirements: Python, FastAPI, SQL, Docker.
        Experience: 2+ years.
        """

        cleaned = validate_job_description_input(jd)
        self.assertIn("backend developer", cleaned.lower())

    def test_rejects_script_like_content(self):
        bad = """
        <script>
        const a = 1
        function run() { console.log(window.location.href) }
        </script>
        """

        with self.assertRaises(ValueError) as ctx:
            validate_job_description_input(bad)

        self.assertIn("code or script", str(ctx.exception).lower())

    def test_rejects_non_jd_notes(self):
        bad = """
        Grocery list
        tomatoes
        onions
        rice
        milk
        """

        with self.assertRaises(ValueError) as ctx:
            validate_job_description_input(bad)

        message = str(ctx.exception).lower()
        self.assertTrue(
            "too short" in message or "does not look enough like a job description" in message
        )

    def test_rejects_script_like_content_with_recruiter_guidance(self):
        bad = """
        <script>
        const a = 1
        function run() { console.log(window.location.href) }
        </script>
        """

        with self.assertRaises(ValueError) as ctx:
            validate_job_description_input(bad)

        self.assertIn("please paste the actual jd content", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
