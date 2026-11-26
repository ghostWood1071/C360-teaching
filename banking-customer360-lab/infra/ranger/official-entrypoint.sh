#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import os
import re
from pathlib import Path

source = Path("/home/ranger/customer360/install.properties.template")
target = Path("/opt/ranger/admin/install.properties")
content = source.read_text(encoding="utf-8")

def substitute(match: re.Match[str]) -> str:
    name = match.group(1)
    if name not in os.environ:
        raise RuntimeError(f"Missing Ranger environment variable: {name}")
    return os.environ[name]

target.write_text(
    re.sub(r"\$\{([A-Z][A-Z0-9_]*)\}", substitute, content),
    encoding="utf-8",
)
target.chmod(0o600)
PY

exec /home/ranger/scripts/ranger.sh
