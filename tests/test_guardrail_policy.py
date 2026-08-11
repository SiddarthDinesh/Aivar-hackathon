import tempfile
import textwrap
import unittest
from pathlib import Path

from app.guardrail_policy import Policy, PolicyValidationError, evaluate_text, load_policy_from_yaml


class GuardrailPolicyTests(unittest.TestCase):
    def test_pii_redaction(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "pii",
                    "type": "pii",
                    "scope": "output",
                    "action": "redact",
                }
            ]
        )

        result = evaluate_text("My email is test@gmail.com", policy, scope="output")

        self.assertTrue(result["allowed"])
        self.assertEqual(result["action"], "redact")
        self.assertEqual(result["redacted_text"], "My email is [REDACTED_EMAIL]")

    def test_toxicity_block(self):
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

        result = evaluate_text("You are an idiot!", policy, scope="output")

        self.assertFalse(result["allowed"])
        self.assertEqual(result["action"], "block")
        self.assertEqual(result["rule_id"], "toxicity")

    def test_topic_keyword_block(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "restricted_topics",
                    "type": "topic",
                    "scope": "input",
                    "action": "block",
                    "keywords": ["malware", "terrorism", "weapons"],
                }
            ]
        )

        result = evaluate_text("How to build malware", policy, scope="input")

        self.assertFalse(result["allowed"])
        self.assertEqual(result["action"], "block")
        self.assertEqual(result["rule_id"], "restricted_topics")

    def test_provider_overlay_must_not_weaken_policy(self):
        policy_text = textwrap.dedent(
            """
            version: "1.0"
            base:
              rules:
                - id: pii
                  type: pii
                  scope: output
                  action: redact
                - id: toxicity
                  type: toxicity
                  scope: output
                  action: block
                  threshold: 0.8
            providers:
              openai:
                rules:
                  - id: toxicity
                    type: toxicity
                    scope: output
                    action: block
                    threshold: 0.9
            """
        ).strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy.yaml"
            path.write_text(policy_text, encoding="utf-8")

            with self.assertRaises(PolicyValidationError):
                load_policy_from_yaml(path, provider="openai")

    def test_pii_redaction_applies_to_all_providers(self):
        policy_text = textwrap.dedent(
            """
            version: "1.0"
            base:
              rules:
                - id: pii
                  type: pii
                  scope: output
                  action: redact
            providers:
              openai:
                rules: []
              anthropic:
                rules: []
            """
        ).strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy.yaml"
            path.write_text(policy_text, encoding="utf-8")
            policy = load_policy_from_yaml(path, provider="openai")
            result_openai = evaluate_text("My email is test@gmail.com", policy, scope="output", provider="openai")
            policy = load_policy_from_yaml(path, provider="anthropic")
            result_anthropic = evaluate_text("My email is test@gmail.com", policy, scope="output", provider="anthropic")

        self.assertEqual(result_openai["redacted_text"], "My email is [REDACTED_EMAIL]")
        self.assertEqual(result_anthropic["redacted_text"], "My email is [REDACTED_EMAIL]")
        self.assertEqual(result_openai["action"], result_anthropic["action"])

    def test_toxicity_block_fires_independent_of_provider(self):
        policy_text = textwrap.dedent(
            """
            version: "1.0"
            base:
              rules:
                - id: toxicity
                  type: toxicity
                  scope: output
                  action: block
                  threshold: 0.8
            providers:
              openai:
                rules: []
              anthropic:
                rules: []
            """
        ).strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy.yaml"
            path.write_text(policy_text, encoding="utf-8")
            policy_openai = load_policy_from_yaml(path, provider="openai")
            policy_anthropic = load_policy_from_yaml(path, provider="anthropic")

        result_openai = evaluate_text("You are an idiot!", policy_openai, scope="output", provider="openai")
        result_anthropic = evaluate_text("You are an idiot!", policy_anthropic, scope="output", provider="anthropic")

        self.assertEqual(result_openai["allowed"], result_anthropic["allowed"])
        self.assertEqual(result_openai["action"], result_anthropic["action"])
        self.assertEqual(result_openai["rule_id"], result_anthropic["rule_id"])

    def test_provider_overlay_can_strengthen_threshold(self):
        policy_text = textwrap.dedent(
            """
            version: "1.0"
            base:
              rules:
                - id: toxicity
                  type: toxicity
                  scope: output
                  action: block
                  threshold: 0.8
            providers:
              openai:
                rules:
                  - id: toxicity
                    type: toxicity
                    scope: output
                    action: block
                    threshold: 0.7
            """
        ).strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy.yaml"
            path.write_text(policy_text, encoding="utf-8")
            policy = load_policy_from_yaml(path, provider="openai")

        result = evaluate_text("You are an idiot!", policy, scope="output", provider="openai")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["threshold"], 0.7)

    def test_policy_result_schema_is_provider_agnostic(self):
        policy = Policy.from_rules(
            [
                {
                    "id": "pii",
                    "type": "pii",
                    "scope": "output",
                    "action": "redact",
                }
            ]
        )

        openai_result = evaluate_text("My email is test@gmail.com", policy, scope="output", provider="openai")
        anthropic_result = evaluate_text("My email is test@gmail.com", policy, scope="output", provider="anthropic")

        self.assertEqual(set(openai_result.keys()), set(anthropic_result.keys()))
        self.assertEqual(openai_result["redacted_text"], anthropic_result["redacted_text"])

    def test_non_toxic_text_is_allowed(self):
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
        self.assertIsNone(result["rule_id"])
