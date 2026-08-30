import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from moedu_agent_cli.cli import AGENT_CLIENT_TYPE, main
from moedu_agent_cli.client import ApiError, ApiResponse
from moedu_agent_cli.config import normalize_api_base, resolve_settings


class AuthTests(unittest.TestCase):
    def test_production_http_is_upgraded_to_https(self):
        self.assertEqual(
            normalize_api_base("http://crm.moedu.com"),
            "https://crm.moedu.com/crm-api",
        )
        self.assertEqual(
            normalize_api_base("http://192.0.2.10"),
            "http://192.0.2.10/crm-api",
        )

    @patch("moedu_agent_cli.cli.save_config")
    @patch("moedu_agent_cli.cli.load_config", return_value={})
    @patch("moedu_agent_cli.config.load_config", return_value={})
    @patch("moedu_agent_cli.cli.getpass.getpass", return_value="secret")
    @patch("moedu_agent_cli.cli.Client")
    def test_login_uses_independent_agent_session(
        self,
        client_class,
        _getpass,
        _config_load,
        _cli_load,
        save_config,
    ):
        client_class.return_value.post.return_value = ApiResponse(
            data={"adminToken": "token-value"},
            request_id="request-1",
            duration_ms=1,
            api_code=0,
            message="success",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--base-url",
                    "http://crm.moedu.com",
                    "auth",
                    "login",
                    "--username",
                    "kevin",
                ]
            )

        self.assertEqual(code, 0)
        client_class.return_value.post.assert_called_once_with(
            "login",
            {"username": "kevin", "password": "secret", "type": AGENT_CLIENT_TYPE},
            authenticated=False,
        )
        saved = save_config.call_args.args[0]
        self.assertEqual(saved["base_url"], "https://crm.moedu.com")
        self.assertEqual(saved["client_type"], AGENT_CLIENT_TYPE)
        self.assertEqual(json.loads(output.getvalue())["data"]["independent_session"], True)

    @patch("moedu_agent_cli.config.load_config", return_value={"token": "expired"})
    @patch("moedu_agent_cli.cli.Client")
    def test_expired_session_has_actionable_error(self, client_class, _load_config):
        client_class.return_value.post.side_effect = ApiError(
            "请先登录！",
            "request-302",
            http_status=200,
            api_code=302,
        )
        error = io.StringIO()
        with redirect_stderr(error):
            code = main(["doctor"])

        self.assertEqual(code, 3)
        value = json.loads(error.getvalue())
        self.assertTrue(value["error"]["reauth_required"])
        self.assertIn("独立会话", value["error"]["hint"])

    @patch("moedu_agent_cli.config.load_config", return_value={"base_url": "http://crm.moedu.com"})
    def test_stored_production_url_is_resolved_as_https(self, _load_config):
        settings = resolve_settings(
            SimpleNamespace(
                base_url=None,
                agent_id=None,
                timeout=None,
                insecure=False,
                no_local_audit=False,
            )
        )
        self.assertEqual(settings.api_base, "https://crm.moedu.com/crm-api")

    @patch("moedu_agent_cli.cli.run_browser_login")
    @patch("moedu_agent_cli.config.load_config", return_value={})
    def test_browser_login_dispatches_without_terminal_password(self, _load_config, browser_login):
        browser_login.return_value = {
            "authenticated": True,
            "username": "kevin",
            "client_type": AGENT_CLIENT_TYPE,
            "independent_session": True,
            "config_saved": True,
        }
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--base-url",
                    "http://crm.moedu.com",
                    "auth",
                    "browser-login",
                    "--username",
                    "kevin",
                ]
            )

        self.assertEqual(code, 0)
        settings = browser_login.call_args.args[0]
        self.assertEqual(settings.api_base, "https://crm.moedu.com/crm-api")
        self.assertEqual(browser_login.call_args.kwargs["client_type"], AGENT_CLIENT_TYPE)
        self.assertTrue(json.loads(output.getvalue())["data"]["authenticated"])


if __name__ == "__main__":
    unittest.main()
