import unittest

from moedu_agent_cli.output import project_data, redact_pii


class OutputTests(unittest.TestCase):
    def test_pii_is_redacted_recursively(self):
        value = {
            "name": "示例员工",
            "mobile": "13800000000",
            "nested": {"idCard": "secret", "score": 95},
        }
        self.assertEqual(redact_pii(value)["mobile"], "[REDACTED]")
        self.assertEqual(redact_pii(value)["nested"]["idCard"], "[REDACTED]")
        self.assertEqual(redact_pii(value)["nested"]["score"], 95)

    def test_pii_can_be_explicitly_included(self):
        value = {"mobile": "13800000000"}
        self.assertEqual(redact_pii(value, include_pii=True), value)

    def test_projection_supports_dot_paths(self):
        value = [{"id": 1, "owner": {"name": "A"}, "unused": 2}]
        self.assertEqual(project_data(value, ["id", "owner.name"]), [{"id": 1, "owner.name": "A"}])


if __name__ == "__main__":
    unittest.main()
