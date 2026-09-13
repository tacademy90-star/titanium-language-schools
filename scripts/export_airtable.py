"""Export each configured Airtable language-center view to its own JSON file."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_VIEWS = [
    {"filename": "erican", "name": "ERiCAN", "view_id": "viwTRsQ5fSUMz2FzF"},
    {"filename": "ems", "name": "EMS", "view_id": "viw06ZYlNHPoLZcsX"},
    {"filename": "bright", "name": "BRIGHT", "view_id": "viwKeiRqhHVaKTgKL"},
    {"filename": "britania", "name": "BRITANIA", "view_id": "viwRArVDZFEmJEi2z"},
    {"filename": "big-ben", "name": "BIG BEN", "view_id": "viwgZv9Nl26V4Mxfd"},
    {"filename": "wwlc", "name": "WWLC", "view_id": "viwxNiRHMNo6HhG3L"},
    {"filename": "els", "name": "ELS", "view_id": "viwQOvDD7YuVrJtaL"},
    {
        "filename": "sheffiled-academy",
        "name": "Sheffiled Academy",
        "view_id": "viwLSmqWFiMahv7z8",
    },
    {
        "filename": "excel-language-center",
        "name": "EXCEL Language Center",
        "view_id": "viwkIoi8AaU1DU5U3",
    },
    {
        "filename": "excel-one-south",
        "name": "EXCEL One South",
        "view_id": "viwa95WfxIDL0NaU2",
    },
]


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def configured_views() -> list[dict[str, str]]:
    raw = os.environ.get("AIRTABLE_VIEWS_JSON", "").strip()
    views = json.loads(raw) if raw else DEFAULT_VIEWS
    if not isinstance(views, list) or not views:
        raise ValueError("AIRTABLE_VIEWS_JSON must be a non-empty JSON list")

    filenames: set[str] = set()
    for view in views:
        if not isinstance(view, dict):
            raise ValueError("Every Airtable view must be a JSON object")
        for key in ("filename", "name", "view_id"):
            if not isinstance(view.get(key), str) or not view[key].strip():
                raise ValueError(f"Every Airtable view needs a non-empty {key}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", view["filename"]):
            raise ValueError(
                f"Invalid filename {view['filename']!r}; use lowercase letters, numbers, and hyphens"
            )
        if view["filename"] in filenames:
            raise ValueError(f"Duplicate filename: {view['filename']}")
        filenames.add(view["filename"])
    return views


def fetch_records(token: str, base_id: str, table_id: str, view_id: str) -> list[dict]:
    endpoint = f"https://api.airtable.com/v0/{base_id}/{urllib.parse.quote(table_id, safe='')}"
    records: list[dict] = []
    offset: str | None = None

    while True:
        params = {"pageSize": "100", "view": view_id}
        if offset:
            params["offset"] = offset

        request = urllib.request.Request(
            f"{endpoint}?{urllib.parse.urlencode(params)}",
            headers={"Authorization": f"Bearer {token}"},
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Airtable API returned HTTP {exc.code}: {details}") from exc

        records.extend(payload.get("records", []))
        offset = payload.get("offset")
        if not offset:
            return records


def main() -> None:
    token = required_env("AIRTABLE_TOKEN")
    base_id = required_env("AIRTABLE_BASE_ID")
    table_id = required_env("AIRTABLE_TABLE_ID")
    views = configured_views()

    exports = []
    for view in views:
        records = fetch_records(token, base_id, table_id, view["view_id"])
        exports.append((view, records))

    output_dir = Path("data/language-centers")
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.glob("*.json"):
        old_file.unlink()

    total_records = 0
    for view, records in exports:
        output_path = output_dir / f"{view['filename']}.json"
        output_path.write_text(
            json.dumps(
                {
                    "center": view["name"],
                    "view_id": view["view_id"],
                    "records": records,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        total_records += len(records)
        print(f"Exported {len(records)} records to {output_path}")

    print(f"Exported {total_records} records across {len(exports)} language centers")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        raise
