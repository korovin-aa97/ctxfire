"""Validate a ctxfire JSON report against the committed public schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("schemas/report-v1.1.schema.json"))
    args = parser.parse_args()
    schema = cast(dict[str, Any], json.loads(args.schema.read_text(encoding="utf-8")))
    report = cast(dict[str, Any], json.loads(args.report.read_text(encoding="utf-8")))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
