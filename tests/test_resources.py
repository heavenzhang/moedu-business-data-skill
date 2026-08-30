import unittest

from moedu_agent_cli.resources import RESOURCE_LIST, get_resource


class ResourceRegistryTests(unittest.TestCase):
    def test_names_are_unique(self):
        names = [resource.name for resource in RESOURCE_LIST]
        self.assertEqual(len(names), len(set(names)))

    def test_all_routes_are_allowlisted_as_read_only(self):
        forbidden = ("/add", "/save", "/update", "/delete", "/publish", "/activate", "/evaluate")
        for resource in RESOURCE_LIST:
            route = "/" + resource.list_path.lower()
            self.assertFalse(any(fragment in route for fragment in forbidden), resource.name)
            self.assertTrue(resource.public_dict()["read_only"])

    def test_jxc_label_is_present_in_path_and_body(self):
        resource = get_resource("jxc.sales-orders")
        self.assertEqual(resource.default_body["label"], 5)
        self.assertTrue(resource.list_path.endswith("/5"))

    def test_restricted_resource_is_marked(self):
        self.assertEqual(get_resource("hrm.payroll-records").sensitivity, "restricted")

    def test_goal_resources_use_real_primary_keys(self):
        self.assertEqual(get_resource("goals.teams").primary_key, "teamId")
        self.assertEqual(get_resource("goals.plans").primary_key, "planId")
        self.assertEqual(get_resource("goals.budgets").primary_key, "companyBudgetId")
        self.assertEqual(get_resource("goals.ipi").primary_key, "scorecardId")

    def test_feedback_resource_is_read_only_and_uses_admin_list(self):
        resource = get_resource("support.feedback")
        self.assertEqual(resource.primary_key, "feedbackId")
        self.assertIn("reviewStatus", resource.filter_hints)
        self.assertEqual(resource.list_path, "oaFeedback/admin/page")
        self.assertEqual(resource.detail_path, "oaFeedback/detail/{id}")
        self.assertTrue(resource.public_dict()["read_only"])

    def test_crm_detail_routes_stay_disabled_until_server_authorization_is_uniform(self):
        crm_resources = [resource for resource in RESOURCE_LIST if resource.domain == "crm"]
        self.assertTrue(crm_resources)
        self.assertTrue(all(resource.detail_path is None for resource in crm_resources))


if __name__ == "__main__":
    unittest.main()
