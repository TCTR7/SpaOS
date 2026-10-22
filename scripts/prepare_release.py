"""Stamp both artifacts once before build; never regenerate at container start."""
import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--version", required=True)
parser.add_argument("--release-id", required=True)
args = parser.parse_args()
import re
if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", args.version):
    parser.error("Use semantic version, for example 0.2.0")
if not re.fullmatch(r"[a-zA-Z0-9._-]{1,100}", args.release_id) or args.release_id == "development":
    parser.error("Use a unique release id, not development")
stamp = datetime.now(timezone.utc).isoformat()
for component in ("backend", "frontend"):
    info = dict(version=args.version, release_id=args.release_id, build_id=component+"-"+uuid.uuid4().hex[:12], built_at=stamp)
    if component == "backend":
        (root/"backend/app/build_info.json").write_text(json.dumps(info)+"\n", encoding="utf8")
    else:
        (root/"frontend/src/lib/build-info.ts").write_text("// Generated before build.\nexport const BUILD_INFO = "+json.dumps(info)+";\n", encoding="utf8")
package = root/"frontend/package.json"
data = json.loads(package.read_text(encoding="utf8"))
data["version"] = args.version
package.write_text(json.dumps(data, indent=2)+"\n", encoding="utf8")
print("Stamped", args.version, args.release_id, "— build and deploy both artifacts from this source snapshot.")
