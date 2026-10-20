"""JWT tolerates a two-second clock correction, never an arbitrary future/expired token."""
from datetime import datetime, timezone
import uuid
import jwt
import pytest
from app.core.config import settings
from app.core.security import decode_access_token
from tests.test_operator import operator_env, login, B


def freeze_jwt_clock(monkeypatch):
    current = datetime(2030, 1, 1, tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return current if tz else current.replace(tzinfo=None)
    monkeypatch.setattr(jwt.api_jwt, "datetime", Clock)
    return int(current.timestamp())


def signed(claims, secret=None):
    return jwt.encode(claims, secret or settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_management_token_accepts_small_clock_skew_but_preserves_validation(monkeypatch):
    now = freeze_jwt_clock(monkeypatch)
    claims = {"sub":str(uuid.uuid4()),"tenant_id":str(uuid.uuid4()),"role":"ADMIN","iat":now+1,"exp":now+60}
    assert decode_access_token(signed(claims))["sub"] == claims["sub"]
    for changes, error in (({"iat":now+3}, jwt.ImmatureSignatureError),
                           ({"iat":now-60,"exp":now-3}, jwt.ExpiredSignatureError),
                           ({"aud":"spaos-operator"}, jwt.InvalidAudienceError)):
        with pytest.raises(error):
            decode_access_token(signed({**claims,**changes}))
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(signed(claims, "unrelated-qa-key-with-at-least-thirty-two-bytes"))


def test_future_token_logs_numeric_clock_metadata_but_no_private_claims(monkeypatch, caplog):
    now = freeze_jwt_clock(monkeypatch)
    token = signed({"iat": now + 10, "exp": now + 60, "sub": "PRIVATE-CUSTOMER",
                    "tenant_id": "PRIVATE-BRANCH", "phone": "PRIVATE-PHONE"})
    with pytest.raises(jwt.ImmatureSignatureError):
        decode_access_token(token)
    assert "Authentication clock validation rejected" in caplog.text
    assert "server_unix" in caplog.text and "iat_ahead_seconds" in caplog.text
    assert token not in caplog.text
    assert "PRIVATE-" not in caplog.text


def test_bad_signature_does_not_emit_claim_clock_diagnostics(monkeypatch, caplog):
    now = freeze_jwt_clock(monkeypatch)
    token = signed({"iat": now + 10, "exp": now + 60}, "unrelated-qa-key-with-at-least-thirty-two-bytes")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)
    assert "Authentication clock validation rejected" not in caplog.text


@pytest.mark.parametrize("claims", [[], {"iat": {"private": "PRIVATE"}}, {"iat": float("inf")}, {"iat": "PRIVATE"}])
def test_clock_diagnostics_never_return_non_numeric_claim_values(claims):
    import base64
    import json
    from app.core.security import _clock_metadata
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode()
    result = _clock_metadata("header." + encoded + ".signature")
    assert "iat_ahead_seconds" not in result
    assert "PRIVATE" not in str(result)


@pytest.mark.asyncio
async def test_operator_clock_skew_preserves_expiry_scope_and_version(operator_env, monkeypatch):
    client, _ = operator_env
    headers = await login(client)
    claims = jwt.decode(headers["Authorization"].split()[1], settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM], audience="spaos-operator")
    now = freeze_jwt_clock(monkeypatch)
    claims.update(iat=now+1, exp=now+60)
    async def request(changes):
        return await client.get(B+"/operator/me",headers={"Authorization":"Bearer "+signed({**claims,**changes})})
    assert (await request({})).status_code == 200
    for changes in ({"iat":now+3},{"iat":now-60,"exp":now-3},{"scope":"other"},
                    {"version":claims["version"]+1},{"aud":"other"}):
        assert (await request(changes)).status_code == 401
