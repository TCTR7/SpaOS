"""Lifecycle regression: all processes, network and database contexts are fake."""
from contextlib import contextmanager
from pathlib import Path
import io
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from automation_test import run_ui_qa as runner
from automation_test.common_setup import qa_frontend as frontend
from automation_test.common_setup.frontend_preflight import FrontendPreflightError


class FrontendLifecycleTests(unittest.TestCase):
    def exercise(self, *, build_code=0, ready_error=None, body_error=None):
        build, server = Mock(name="owned-build"), Mock(name="owned-server")
        build.stdout, server.stdout = io.StringIO(""), io.StringIO("")
        build.wait.return_value = build_code
        server.poll.return_value = None
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(frontend, "source_fingerprints", return_value={}), \
                patch.object(frontend, "write_qa_tsconfig"), \
                patch.object(frontend.socket, "socket") as socket, \
                patch.object(frontend.subprocess, "Popen", side_effect=[build, server]) as launch, \
                patch.object(frontend, "verify_frontend", side_effect=ready_error), \
                patch.object(frontend.time, "monotonic", side_effect=[0, 181]), \
                patch.object(frontend, "stop_owned_process") as stop:
            try:
                with frontend.qa_frontend("http://127.0.0.1:54321", artifact_root=Path(folder)) as qa:
                    self.assertEqual(qa["env"]["BACKEND_INTERNAL_URL"], "http://127.0.0.1:54321")
                    self.assertEqual(qa["env"]["SPAOS_QA_RUN_ID"], qa["run_id"])
                    if body_error:
                        raise body_error
            finally:
                expected = [server, build] if launch.call_count == 2 else [build]
                self.assertEqual([c.args[0] for c in stop.call_args_list], expected)
                socket.return_value.bind.assert_called_once_with(("127.0.0.1", 3001))
                self.assertEqual(launch.call_args_list[0].args[0][-1], "build")
                self.assertEqual(list(Path(folder).iterdir()), [], "QA must not create artifact/log directories")
                self.assertEqual(launch.call_args_list[0].kwargs["stdout"], subprocess.PIPE)
                self.assertEqual(launch.call_args_list[0].kwargs["stderr"], subprocess.STDOUT)

    def test_success_cleans_only_owned_processes(self):
        self.exercise()

    def test_build_failure_cleans_without_starting_server(self):
        with self.assertRaisesRegex(RuntimeError, "build failed"):
            self.exercise(build_code=1)

    def test_preflight_failure_cleans_frontend(self):
        with self.assertRaisesRegex(RuntimeError, "not ready"):
            self.exercise(ready_error=FrontendPreflightError("wrong server"))

    def test_interrupt_cleans_frontend(self):
        with self.assertRaises(KeyboardInterrupt):
            self.exercise(body_error=KeyboardInterrupt())

    def test_reserved_user_port_is_rejected_without_process(self):
        with patch.object(frontend.subprocess, "Popen") as launch:
            with self.assertRaises(ValueError):
                with frontend.qa_frontend("http://127.0.0.1:54321", port=3000):
                    self.fail("Must reject port 3000")
            launch.assert_not_called()

    def test_stop_finished_process_does_not_issue_kill(self):
        process = Mock()
        process.poll.return_value = 0
        with patch.object(frontend.subprocess, "run") as command:
            frontend.stop_owned_process(process)
            command.assert_not_called()
            process.terminate.assert_not_called()

    def test_occupied_port_does_not_start_or_stop_any_process(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(frontend, "source_fingerprints", return_value={}), \
                patch.object(frontend.socket, "socket") as socket, \
                patch.object(frontend.subprocess, "Popen") as launch, \
                patch.object(frontend, "stop_owned_process") as stop:
            socket.return_value.bind.side_effect = OSError("Port belongs to another process")
            with self.assertRaises(OSError):
                with frontend.qa_frontend("http://127.0.0.1:54321", artifact_root=Path(folder)):
                    self.fail("Occupied port must fail")
            launch.assert_not_called()
            stop.assert_not_called()

    def test_start_failure_cleans_completed_build_handle(self):
        build = Mock()
        build.stdout = io.StringIO("")
        build.wait.return_value = 0
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(frontend, "source_fingerprints", return_value={}), \
                patch.object(frontend, "write_qa_tsconfig"), \
                patch.object(frontend.socket, "socket"), \
                patch.object(frontend.subprocess, "Popen", side_effect=[build, OSError("Start failed")]), \
                patch.object(frontend, "stop_owned_process") as stop:
            with self.assertRaises(OSError):
                with frontend.qa_frontend("http://127.0.0.1:54321", artifact_root=Path(folder)):
                    self.fail("Start failed")
            stop.assert_called_once_with(build)


class RunnerLifecycleTests(unittest.TestCase):
    def exercise(self, code=0, failure=None):
        events = []
        @contextmanager
        def backend():
            events.append("backend-start")
            try:
                yield "http://127.0.0.1:54321"
            finally:
                events.append("backend-stop")
        with tempfile.TemporaryDirectory() as folder:
            @contextmanager
            def ui(url, **kwargs):
                self.assertEqual(url, "http://127.0.0.1:54321")
                events.append("frontend-start")
                try:
                    yield dict(frontend_url="http://127.0.0.1:3001", run_id="test",
                               artifacts=Path(folder), env={})
                finally:
                    events.append("frontend-stop")
            process = Mock()
            process.stdout = io.StringIO("23 passed\n")
            process.wait.return_value = code
            process.wait.side_effect = failure
            with patch.object(runner, "qa_backend", backend), \
                    patch.object(runner, "qa_frontend", ui), \
                    patch.object(runner, "verify_api_isolation", return_value={}), \
                    patch.object(runner.subprocess, "Popen", return_value=process) as launch, \
                    patch.object(runner, "stop_owned_process") as stop:
                result = runner.run(["automation_test/features", "-q"])
                stop.assert_called_once_with(process)
                self.assertEqual(launch.call_count, 1)
                command=launch.call_args.args[0]
                self.assertEqual(command[command.index("-c")+1],str(runner.ROOT / "automation_test" / "pytest.ini"))
                self.assertEqual(list(Path(folder).iterdir()), [], "No pytest.log or isolation.json")
            self.assertEqual(events, ["backend-start", "frontend-start", "frontend-stop", "backend-stop"])
            return result

    def test_success_has_one_shared_backend(self):
        self.assertEqual(self.exercise(), 0)

    def test_pytest_exit_code_is_preserved(self):
        self.assertEqual(self.exercise(code=2), 2)

    def test_interrupted_pytest_cleans_both_contexts(self):
        self.assertEqual(self.exercise(failure=KeyboardInterrupt()), 130)


class DefaultSelectionTests(unittest.TestCase):
    def test_default_cli_delegates_selection_to_pytest_config(self):
        with patch.object(runner.sys,"argv",["run_ui_qa"]),patch.object(runner,"run",return_value=0) as run:
            self.assertEqual(runner.main(),0)
        self.assertEqual(run.call_args.args[0],["-q","--tb=short"])

    def test_filtered_default_still_uses_configured_testpaths(self):
        with patch.object(runner.sys,"argv",["run_ui_qa","--","-k","deep_link"]),patch.object(runner,"run",return_value=0) as run:
            self.assertEqual(runner.main(),0)
        self.assertEqual(run.call_args.args[0],["-k","deep_link"])

    def test_explicit_selection_remains_targeted(self):
        selected="automation_test/reviews/test_shared_saas.py"
        with patch.object(runner.sys,"argv",["run_ui_qa","--",selected,"-q"]),patch.object(runner,"run",return_value=0) as run:
            self.assertEqual(runner.main(),0)
        self.assertEqual(run.call_args.args[0],[selected,"-q"])

    def test_root_relative_explicit_node_is_resolved_without_adding_default_tests(self):
        selected="automation_test/reviews/test_shared_saas.py::test_canonical_login_routes_brand_manifest_and_worker"
        command=runner.pytest_command([selected,"-k","login or deep_link"])
        self.assertEqual(command[-3:], [str(runner.ROOT / "automation_test" / "reviews" / "test_shared_saas.py")+"::test_canonical_login_routes_brand_manifest_and_worker","-k","login or deep_link"])

    def test_default_collection_includes_shared_saas_once_without_legacy_probes(self):
        # Collection never executes autouse fixtures or starts API/browser/DB.
        result=subprocess.run(runner.pytest_command(["--collect-only","-qq","--color=no"]),cwd=runner.TEST_ROOT,
            capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        nodes=[line.strip() for line in result.stdout.splitlines() if "::test_" in line]
        self.assertTrue(nodes,"No regression tests were collected")
        self.assertEqual(len(nodes),len(set(nodes)),"Duplicate test collection")
        shared=[node for node in nodes if "test_shared_saas.py::" in node]
        self.assertGreaterEqual(len(shared),11,"Shared SaaS regressions disappeared from default selection")
        self.assertTrue(any("test_admin_login.py::" in node for node in nodes))
        self.assertTrue(any("test_branch_work_guard.py::" in node for node in nodes))
        self.assertTrue(any("test_operator_ui.py::" in node for node in nodes))
        self.assertFalse(any("reviews/" in node.replace("\\","/") and "test_shared_saas.py::" not in node for node in nodes),"One-off review probes must stay opt-in")


if __name__ == "__main__":
    unittest.main()
