"""Generate the OpenAPI schema (docs/openapi.json).

Run from the repository root:

    python aml_platform/backend/generate_openapi.py
"""

import json
import sys
from pathlib import Path

# Ensure backend root is in python path
sys.path.append(str(Path(__file__).resolve().parent))

from app.main import app  # noqa: E402


def build_schema() -> dict:
    return app.openapi()


def main():
    openapi_schema = build_schema()

    # Output goes to a FIXED relative path (see module docstring) — the
    # literal path keeps the write confined, out of reach of any traversal.
    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/openapi.json").write_text(json.dumps(openapi_schema, indent=2), encoding="utf-8")
    print("Successfully generated OpenAPI schema at docs/openapi.json")


if __name__ == "__main__":
    main()
