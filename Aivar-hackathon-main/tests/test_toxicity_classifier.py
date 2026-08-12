import unittest

from app.guardrail_policy import Policy, evaluate_text


class ToxicityClassifierTests(unittest.TestCase):
    def test_non_toxic_text_has_low_score_and_allowed(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "toxicity",
                    "type": "toxicity",
                    "scope": "output",
                    "action": "block",
                    "threshold": 0.8,
                }
            ]
        )

        result = evaluate_text("This is a kind and helpful response.", policy, scope="output")

        self.assertTrue(result["allowed"])
        self.assertEqual(result["action"], "allow")
        self.assertIn("score", result)
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)

    def test_clearly_toxic_text_is_blocked(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "toxicity",
                    "type": "toxicity",
                    "scope": "output",
                    "action": "block",
                    "threshold": 0.8,
                }
            ]
        )

        result = evaluate_text("You are an idiot and a moron!", policy, scope="output")

        self.assertFalse(result["allowed"])
        self.assertEqual(result["action"], "block")
        self.assertIn("score", result)

    def test_score_between_zero_and_one(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "toxicity",
                    "type": "toxicity",
                    "scope": "output",
                    "action": "block",
                    "threshold": 0.5,
                }
            ]
        )

        result = evaluate_text("Neutral content.", policy, scope="output")
        score = result.get("score", 0.0)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_toxicity_works_independent_of_provider(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "toxicity",
                    "type": "toxicity",
                    "scope": "output",
                    "action": "block",
                    "threshold": 0.8,
                }
            ]
        )

        # Evaluate with explicit provider names and compare results
        r1 = evaluate_text("You are an idiot!", policy, scope="output", provider="openai")
        r2 = evaluate_text("You are an idiot!", policy, scope="output", provider="anthropic")
        self.assertEqual(r1["allowed"], r2["allowed"])
        self.assertEqual(r1["action"], r2["action"])
        self.assertEqual(r1["rule_id"], r2["rule_id"])


if __name__ == "__main__":
    unittest.main()
