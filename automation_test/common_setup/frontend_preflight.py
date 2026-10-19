"""Read-only preflight for a runner-owned QA frontend; never starts processes."""
from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

import httpx


QA_RUN_HEADER = "X-SpaOS-QA-Run-ID"


class FrontendPreflightError(RuntimeError):
    """The configured frontend is unavailable or cannot be identified as QA."""


def verify_frontend(
    frontend_url: str,
    expected_run_id: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> None:
    """Verify the QA login page without redirects, environment proxies or retries."""
    try:
        origin = urlsplit(frontend_url)
        port = origin.port
        valid_url = (
            origin.scheme == "http"
            and origin.hostname in {"localhost", "127.0.0.1", "::1"}
            and port is not None
            and 0 < port != 3000
            and origin.username is None
            and origin.password is None
            and origin.path in {"", "/"}
            and not origin.query
            and not origin.fragment
            and frontend_url == frontend_url.strip()
        )
    except ValueError:
        valid_url = False
    if not valid_url:
        # Never echo unvalidated URLs: they may contain credentials or query secrets.
        raise FrontendPreflightError(
            "FRONTEND_URL phải là HTTP loopback với port QA rõ ràng "
            "(ví dụ http://127.0.0.1:3001), không có credentials/path/query/fragment; "
            "không dùng cổng 3000 của người dùng. Harness không tự mở hoặc tắt server."
        )

    try:
        run_id = str(UUID(expected_run_id))
    except (ValueError, AttributeError, TypeError):
        raise FrontendPreflightError(
            "Thiếu hoặc sai SPAOS_QA_RUN_ID (UUID). Cần frontend do runner QA "
            "khởi tạo và cùng mã nhận diện. Chạy python -m automation_test.run_ui_qa; "
            "không dùng server ứng dụng đang mở để thay thế."
        ) from None

    url = frontend_url.rstrip("/") + "/admin/login"
    try:
        with httpx.Client(
            transport=transport,
            timeout=5.0,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = client.get(url)
    except httpx.RequestError:
        raise FrontendPreflightError(
            f"Không kết nối được frontend QA tại {url}. "
            "Kiểm tra runner QA/FRONTEND_URL; harness không tự khởi động server "
            "hay chuyển sang cổng 3000."
        ) from None

    if response.status_code != 200:
        raise FrontendPreflightError(
            f"Frontend QA tại {url} trả HTTP {response.status_code}; cần HTTP 200, "
            "không theo redirect và không tự mở/tắt server."
        )
    if response.headers.get(QA_RUN_HEADER) != run_id:
        raise FrontendPreflightError(
            f"Server tại {url} không khớp lượt QA hiện tại ({QA_RUN_HEADER}). "
            "Không sử dụng hoặc dừng process đang chiếm cổng. Kiểm tra runner T00b."
        )
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "text/html":
        raise FrontendPreflightError(
            f"Frontend QA tại {url} không trả trang HTML đăng nhập hợp lệ. "
            "Kiểm tra frontend của runner; không tự mở/tắt server."
        )
