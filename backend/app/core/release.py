import json
from pathlib import Path

BUILD_INFO = json.loads((Path(__file__).resolve().parents[1]/"build_info.json").read_text(encoding="utf8"))
