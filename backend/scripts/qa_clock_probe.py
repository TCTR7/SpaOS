"""Read-only JWT/clock probe. Test containers only; no database, tokens or identities in output."""
import argparse
import base64
import json
import time
import uuid

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def sample():
    wall_start, mono_start = time.time(), time.monotonic()
    token = create_access_token(uuid.uuid4(), uuid.uuid4(), "ADMIN")
    # Metadata of our own synthetic token, never used for authorization.
    payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
    issued = payload["iat"]
    checked_at = time.time()
    error = None
    try:
        decode_access_token(token)
    except jwt.PyJWTError as exc:
        error = type(exc).__name__
    wall_end, mono_end = time.time(), time.monotonic()
    return {
        "error": error,
        "iat_ahead_seconds": issued - checked_at,
        "wall_minus_monotonic_step_seconds": (wall_end - wall_start) - (mono_end - mono_start),
        "sample_elapsed_seconds": mono_end - mono_start,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--interval", type=float, default=0.005)
    args = parser.parse_args(argv)
    if settings.ENVIRONMENT != "test":
        parser.error("Run only in an isolated container with ENVIRONMENT=test")
    if not 1 <= args.seconds <= 600 or not 0.001 <= args.interval <= 1:
        parser.error("seconds must be 1..600 and interval 0.001..1")
    start = time.monotonic()
    previous_wall, previous_mono = time.time(), time.monotonic()
    count = rejected = 0
    forward = backward = 0.0
    max_ahead = float("-inf")
    while time.monotonic() - start < args.seconds:
        result = sample()
        count += 1
        max_ahead = max(max_ahead, result["iat_ahead_seconds"])
        wall, mono = time.time(), time.monotonic()
        step = (wall - previous_wall) - (mono - previous_mono)
        forward, backward = max(forward, step), min(backward, step)
        if result["error"]:
            rejected += 1
            # A rejected sample stays rejected; no sleep/retry to turn it into a pass.
            print(json.dumps({"sample": count, "observed_at_unix": wall, **result}), flush=True)
        previous_wall, previous_mono = wall, mono
        time.sleep(args.interval)
    print(json.dumps({"samples": count, "rejected": rejected, "elapsed_seconds": time.monotonic() - start,
                      "max_iat_ahead_seconds": max_ahead, "max_forward_step_seconds": forward,
                      "max_backward_step_seconds": backward}), flush=True)
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
