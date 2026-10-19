"""Unit tests only: no dotenv, frontend, browser or QA database."""
import unittest

import httpx

from automation_test.common_setup.frontend_preflight import (
    FrontendPreflightError,
    QA_RUN_HEADER,
    verify_frontend,
)


RUN_ID = "62554f84-bac3-4ba2-ae42-e08dd77ee46d"
URL = "http://127.0.0.1:3001"


class FrontendPreflightTests(unittest.TestCase):
    def transport(self, status=200, headers=None):
        def respond(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(str(request.url), URL + "/admin/login")
            return httpx.Response(status, headers=headers or {})
        return httpx.MockTransport(respond)

    def test_accepts_only_matching_qa_html(self):
        verify_frontend(URL, RUN_ID, transport=self.transport(headers={
            QA_RUN_HEADER: RUN_ID, "content-type": "text/html; charset=utf-8",
        }))

    def test_wrong_run_or_unmarked_server_is_rejected(self):
        for marker in (None, "e23525e2-34fa-4b07-8ee1-415c5161a39d"):
            with self.subTest(marker=marker):
                headers = {"content-type": "text/html"}
                if marker:
                    headers[QA_RUN_HEADER] = marker
                with self.assertRaisesRegex(FrontendPreflightError, "không khớp"):
                    verify_frontend(URL, RUN_ID, transport=self.transport(headers=headers))

    def test_non_200_and_redirects_are_rejected(self):
        for status in (204, 301, 302, 307, 401, 404, 500, 503):
            with self.subTest(status=status):
                with self.assertRaisesRegex(FrontendPreflightError, f"HTTP {status}"):
                    verify_frontend(URL, RUN_ID, transport=self.transport(
                        status, {"location": "http://localhost:3000/admin/login"},
                    ))

    def test_network_errors_fail_without_retry(self):
        for error in (httpx.ConnectError, httpx.ReadTimeout):
            calls = []
            def unavailable(request):
                calls.append(request)
                raise error("SENSITIVE_RESPONSE_MUST_NOT_BE_LOGGED")
            with self.subTest(error=error.__name__):
                with self.assertRaises(FrontendPreflightError) as caught:
                    verify_frontend(URL, RUN_ID, transport=httpx.MockTransport(unavailable))
                self.assertEqual(len(calls), 1)
                self.assertIn(URL, str(caught.exception))
                self.assertNotIn("SENSITIVE", str(caught.exception))

    def test_invalid_origin_is_rejected_before_request_and_not_echoed(self):
        invalid_urls = [
            "", "http://localhost:3000", "http://localhost", "http://localhost:bad",
            "https://127.0.0.1:3001", "http://example.test:3001",
            "http://localhost.example.test:3001", "http://localhost:3001/admin",
            "http://secret:password@localhost:3001", "http://localhost:3001?token=secret",
            "http://localhost:3001#secret", " http://localhost:3001", "http://[broken",
        ]
        def unexpected_request(request):
            self.fail("Invalid config must not send any request")
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaisesRegex(FrontendPreflightError, "FRONTEND_URL") as caught:
                    verify_frontend(url, RUN_ID, transport=httpx.MockTransport(unexpected_request))
                self.assertNotIn("secret", str(caught.exception))
                self.assertNotIn("password", str(caught.exception))

    def test_missing_or_invalid_run_id_is_rejected_before_request(self):
        def unexpected_request(request):
            self.fail("Missing QA identity must not send any request")
        for marker in ("", "not-a-uuid"):
            with self.subTest(marker=marker):
                with self.assertRaisesRegex(FrontendPreflightError, "SPAOS_QA_RUN_ID"):
                    verify_frontend(URL, marker, transport=httpx.MockTransport(unexpected_request))

    def test_non_html_with_valid_marker_is_rejected(self):
        for mime in ("application/json", "text/plain", ""):
            with self.subTest(mime=mime):
                with self.assertRaisesRegex(FrontendPreflightError, "HTML"):
                    verify_frontend(URL, RUN_ID, transport=self.transport(headers={
                        QA_RUN_HEADER: RUN_ID, "content-type": mime,
                    }))

    def test_ipv6_loopback_and_trailing_slash_are_supported(self):
        def respond(request):
            self.assertEqual(str(request.url), "http://[::1]:3001/admin/login")
            return httpx.Response(200, headers={
                QA_RUN_HEADER: RUN_ID, "content-type": "text/html",
            })
        verify_frontend("http://[::1]:3001/", RUN_ID, transport=httpx.MockTransport(respond))


if __name__ == "__main__":
    unittest.main()
