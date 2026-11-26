#!/usr/bin/env python3
"""Run the idempotent Ranger bootstrap container from the host."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
command = [
    "docker", "compose", "--env-file", ".env",
    "-f", "infra/compose.yaml", "-f", "infra/compose.security.yaml",
    "run", "--rm", "ranger-init",
]
sys.exit(subprocess.call(command, cwd=ROOT))
