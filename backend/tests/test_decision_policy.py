import unittest

from app.services.decision_policy import bucket_label, get_screening_policy


class DecisionPolicyTest(unittest.TestCase):
    def test_policy_has_required_fields(self):
        policy = get_screening_policy()
        self.assertIn("shortlist_threshold", policy)
        self.assertIn("review_threshold", policy)
        self.assertIn("policy_version", policy)
        self.assertGreater(policy["shortlist_threshold"], policy["review_threshold"])

    def test_bucket_cutoffs_are_deterministic(self):
        policy = get_screening_policy()
        shortlist = policy["shortlist_threshold"]
        review = policy["review_threshold"]

        self.assertEqual("Shortlist", bucket_label(shortlist))
        self.assertEqual("Review", bucket_label(review))
        self.assertEqual("Reject", bucket_label(review - 0.1))


if __name__ == "__main__":
    unittest.main()
