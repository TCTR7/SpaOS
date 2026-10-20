import io
import json
import unittest
from unittest.mock import Mock, patch

from automation_test.common_setup import qa_backend as backend
from automation_test.common_setup.layout_evidence import artifact_directory


class ConsoleOnlyTests(unittest.TestCase):
    def test_layout_file_capture_is_rejected_in_console_mode(self):
        with patch.dict("os.environ", {"SPAOS_QA_NO_ARTIFACTS": "1"}):
            with self.assertRaisesRegex(RuntimeError, "Artifact writing disabled"):
                artifact_directory("collector")

    def test_backend_disables_docker_persistence_and_forwards_auth_only(self):
        calls = []
        def command(args, **kwargs):
            calls.append((args, kwargs))
            return Mock(stdout="127.0.0.1:54321\n" if args[1:2] == ["port"] else "created", stderr="")
        attached = Mock(stdout=io.StringIO("INFO access should not be forwarded\nAuthentication clock validation rejected: numeric-only\n"))
        attached.wait.return_value = 0
        with patch.object(backend.subprocess, "run", side_effect=command), \
                patch.object(backend.subprocess, "Popen", return_value=attached), \
                patch.object(backend.httpx, "get", return_value=Mock(status_code=200)), \
                patch("builtins.print") as output:
            with backend.qa_backend() as url:
                self.assertEqual(url, "http://127.0.0.1:54321")
        override = json.loads(calls[0][1]["input"])
        self.assertEqual(override["services"]["backend"]["logging"]["driver"], "none")
        self.assertIn("-", calls[0][0])
        self.assertFalse(any(args[:2] == ["docker", "logs"] for args, _ in calls))
        self.assertEqual(output.call_count, 1)
        self.assertIn("Authentication clock", output.call_args.args[0])
        self.assertTrue(any(args[:2] == ["docker", "stop"] for args, _ in calls))


if __name__ == "__main__":
    unittest.main()
