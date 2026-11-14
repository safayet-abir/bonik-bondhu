"""CI: fail if the built frontend contains anything that looks like a secret
(Security T6, NFR-05). Usage: python scripts/check_dist_secrets.py frontend/dist"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = {
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"),
    "GEMINI variable": re.compile(rb"GEMINI_API_KEY"),
    "OpenAI-style key": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "DATABASE_URL": re.compile(rb"postgres(ql)?(\+psycopg)?://[^\s\"']+:[^\s\"']+@"),
    "Private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
TEXT_SUFFIXES = {".js", ".css", ".html", ".json", ".map", ".txt", ".svg"}


def main(dist: Path) -> int:
    if not dist.is_dir():
        print(f"dist folder not found: {dist}")
        return 1
    hits = []
    for path in dist.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            data = path.read_bytes()
            hits += [f"{path}: {name}" for name, rx in PATTERNS.items() if rx.search(data)]
    if hits:
        print("Possible secrets in frontend build:\n" + "\n".join(hits))
        return 1
    print(f"No secrets found in {dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/dist")))
