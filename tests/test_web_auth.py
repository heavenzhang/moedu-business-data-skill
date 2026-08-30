import queue
import threading
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from unittest.mock import patch

from moedu_agent_cli.client import ApiResponse
from moedu_agent_cli.config import Settings
from moedu_agent_cli.web_auth import run_browser_login


class BrowserAuthTests(unittest.TestCase):
    @patch("moedu_agent_cli.web_auth.save_config")
    @patch("moedu_agent_cli.web_auth.load_config", return_value={})
    @patch("moedu_agent_cli.web_auth.Client")
    def test_loopback_form_logs_in_and_saves_only_token_metadata(
        self,
        client_class,
        _load_config,
        save_config,
    ):
        client_class.return_value.post.return_value = ApiResponse(
            data={"adminToken": "new-token"},
            request_id="browser-request-1",
            duration_ms=1,
            api_code=0,
            message="success",
        )
        opened_urls = queue.Queue()
        outcome = {}

        def capture_url(url, **_kwargs):
            opened_urls.put(url)
            return True

        def authorize():
            outcome["result"] = run_browser_login(
                Settings(
                    api_base="https://crm.moedu.com/crm-api",
                    token="old-token",
                    agent_id="test-agent",
                    timeout=5,
                    verify_tls=True,
                    local_audit=False,
                ),
                username="kevin",
                wait_seconds=30,
                client_type=4,
            )

        with patch("moedu_agent_cli.web_auth.webbrowser.open", side_effect=capture_url):
            worker = threading.Thread(target=authorize, daemon=True)
            worker.start()
            login_url = opened_urls.get(timeout=5)
            with urlopen(login_url, timeout=5) as response:
                page = response.read().decode("utf-8")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            self.assertIn('type="password"', page)
            self.assertNotIn("http://", page)

            parsed = urlsplit(login_url)
            state = parse_qs(parsed.query)["state"][0]
            request = Request(
                "http://{0}/login".format(parsed.netloc),
                data=urlencode(
                    {"state": state, "username": "kevin", "password": "secret"}
                ).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                self.assertIn("授权成功", response.read().decode("utf-8"))
            worker.join(timeout=5)

        self.assertFalse(worker.is_alive())
        self.assertTrue(outcome["result"]["independent_session"])
        client_class.return_value.post.assert_called_once_with(
            "login",
            {"username": "kevin", "password": "secret", "type": 4},
            authenticated=False,
        )
        saved = save_config.call_args.args[0]
        self.assertEqual(saved["token"], "new-token")
        self.assertNotIn("password", saved)
        self.assertEqual(saved["base_url"], "https://crm.moedu.com")


if __name__ == "__main__":
    unittest.main()
