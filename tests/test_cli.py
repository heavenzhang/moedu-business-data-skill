import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from moedu_agent_cli.cli import _normalize_data, _parse_filters, main


class CliTests(unittest.TestCase):
    def test_filter_values_are_typed(self):
        self.assertEqual(
            _parse_filters(["year=2026", "active=true", "name=销售一部"]),
            {"year": 2026, "active": True, "name": "销售一部"},
        )

    def test_page_envelope_is_normalized(self):
        data, page, extra = _normalize_data(
            {
                "list": [{"id": 1}],
                "pageNumber": 1,
                "pageSize": 20,
                "totalRow": 1,
                "totalPage": 1,
                "firstPage": True,
                "lastPage": True,
                "extraData": {"sum": 3},
            },
            True,
        )
        self.assertEqual(data, [{"id": 1}])
        self.assertEqual(page["total"], 1)
        self.assertEqual(extra, {"sum": 3})

    def test_resource_list_is_machine_readable(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["resources", "list", "--domain", "crm"])
        self.assertEqual(code, 0)
        value = json.loads(output.getvalue())
        self.assertTrue(value["ok"])
        self.assertTrue(all(row["domain"] == "crm" for row in value["data"]))

    def test_support_resource_domain_is_discoverable(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["resources", "list", "--domain", "support"])
        self.assertEqual(code, 0)
        value = json.loads(output.getvalue())
        self.assertEqual([row["name"] for row in value["data"]], ["support.feedback"])

    def test_unknown_resource_returns_structured_error(self):
        error = io.StringIO()
        with redirect_stderr(error):
            code = main(["resources", "describe", "missing"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(error.getvalue())["error"]["type"], "input_error")


if __name__ == "__main__":
    unittest.main()
