"""Diagnostics observe strict JWT outcomes; they never authorize or retry rejected tokens."""
from datetime import datetime, timedelta, timezone
import json

import jwt
import pytest

from app.core.config import settings
from scripts import qa_clock_probe as probe


def test_probe_valid_synthetic_token_has_no_identity_or_token_in_output():
    result = probe.sample()
    assert result["error"] is None
    assert set(result) == {"error", "iat_ahead_seconds", "wall_minus_monotonic_step_seconds", "sample_elapsed_seconds"}
    assert result["sample_elapsed_seconds"] >= 0


def test_probe_reports_future_token_without_retry_or_relaxing_validation(monkeypatch):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"iat": now + timedelta(seconds=60), "exp": now + timedelta(minutes=5),
                        "sub": "PRIVATE-SUBJECT-MUST-NOT-APPEAR"},
                       settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    calls = []
    def create(*args):
        calls.append(args)
        return token
    monkeypatch.setattr(probe, "create_access_token", create)
    result = probe.sample()
    assert result["error"] == "ImmatureSignatureError"
    assert result["iat_ahead_seconds"] > 50
    assert len(calls) == 1
    assert token not in json.dumps(result)
    assert "PRIVATE-SUBJECT" not in json.dumps(result)


def test_probe_does_not_hide_bad_signature(monkeypatch):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"iat": now, "exp": now + timedelta(minutes=5)},
                       "unrelated-qa-key-with-at-least-thirty-two-bytes", algorithm=settings.JWT_ALGORITHM)
    monkeypatch.setattr(probe, "create_access_token", lambda *args: token)
    assert probe.sample()["error"] == "InvalidSignatureError"


def test_probe_refuses_non_test_environment(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(SystemExit) as error:
        probe.main(["--seconds", "1"])
    assert error.value.code == 2
