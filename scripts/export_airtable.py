"""Export all records from an Airtable view to a stable JSON file."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


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
    view_id = required_env("AIRTABLE_VIEW_ID")

    records = fetch_records(token, base_id, table_id, view_id)
    output_path = Path("data/english-schools.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(records)} Airtable records to {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        raise
