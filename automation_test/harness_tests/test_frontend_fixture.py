"""Regression for the actual E2E fixture, with imports and all I/O isolated."""
import importlib.util
import inspect
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import httpx
import pytest

from automation_test.common_setup import frontend_preflight


RUN_ID = "62554f84-bac3-4ba2-ae42-e08dd77ee46d"


def load_fixture_module():
    # Do not load .env.test or import API/auth/DB helpers in these unit tests.
    stubs = {}
    for name, attributes in {
        "common_setup.qa_backend": {"qa_backend": Mock()},
        "common_setup.api_helper": {"ApiHelper": Mock()},
        "common_setup.auth_setup": {
            "create_admin_authenticated_context": Mock(),
            "create_customer_pwa_authenticated_context": Mock(),
        },
        "common_setup.config": {
            "BASE_DIR": Path(__file__).resolve().parents[1],
            "config": SimpleNamespace(
                frontend_url="http://127.0.0.1:3001", frontend_run_id=RUN_ID,
            ),
        },
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        stubs[name] = module
    stubs["common_setup.frontend_preflight"] = frontend_preflight
    source = Path(__file__).resolve().parents[1] / "conftest.py"
    spec = importlib.util.spec_from_file_location("qa_fixture_under_test", source)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


class FrontendFixtureTests(unittest.TestCase):
    def check_fixture(self, status=200, marker=RUN_ID, disconnected=False):
        headers = {"content-type": "text/html"}
        if marker:
            headers[frontend_preflight.QA_RUN_HEADER] = marker
        response = httpx.Response(status, headers=headers)
        def respond(request):
            if disconnected:
                raise httpx.ConnectError("QA unavailable")
            return response
        real_client = httpx.Client
        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(respond)
            return real_client(**kwargs)

        with (
            patch("subprocess.Popen", side_effect=AssertionError("Unexpected process start")) as spawn,
            patch("subprocess.run", side_effect=AssertionError("Unexpected process command")) as command,
            patch.object(httpx, "get", return_value=response,
                         side_effect=httpx.ConnectError("QA unavailable") if disconnected else None),
            patch.object(httpx, "Client", side_effect=client_factory),
        ):
            module = load_fixture_module()
            fixture_result = module.ensure_frontend_server.__wrapped__()
            if inspect.isgenerator(fixture_result):
                try:
                    next(fixture_result)
                finally:
                    fixture_result.close()
            spawn.assert_not_called()
            command.assert_not_called()

    def test_unreachable_frontend_fails_without_starting_server(self):
        with self.assertRaises(pytest.fail.Exception):
            self.check_fixture(disconnected=True)

    def test_404_server_is_not_reused(self):
        with self.assertRaises(pytest.fail.Exception):
            self.check_fixture(status=404, marker=None)

    def test_unmarked_html_server_is_not_reused(self):
        with self.assertRaises(pytest.fail.Exception):
            self.check_fixture(marker=None)

    def test_matching_frontend_is_used_without_lifecycle_commands(self):
        self.check_fixture()


if __name__ == "__main__":
    unittest.main()
