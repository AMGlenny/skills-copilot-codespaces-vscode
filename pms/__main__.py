"""Command line entry point.

    python -m pms build              rebuild everything in dist/ and docs/
    python -m pms periods 2027       periods for FY 2027-28 as a setup request file
"""
import csv
import json
import sys
from pathlib import Path

from . import docs, periods, seed, sharepoint
from .schema import LISTS, LISTS_BY_NAME

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
MAX_REQUESTS_PER_FILE = 4000  # Power Automate "Apply to each" limit is 5,000 on standard licences


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_requests(stem, reqs):
    chunks = [reqs[i:i + MAX_REQUESTS_PER_FILE] for i in range(0, len(reqs), MAX_REQUESTS_PER_FILE)]
    names = []
    for n, chunk in enumerate(chunks, 1):
        name = f"{stem}.json" if len(chunks) == 1 else f"{stem}_part{n}.json"
        _write_json(DIST / "setup" / name, chunk)
        names.append((name, len(chunk)))
    return names


def _write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build():
    data = seed.build()
    written = _write_requests("01_schema", sharepoint.schema_requests())
    written += _write_requests("02_seed", sharepoint.item_requests(data))

    for lst in LISTS:
        cols = lst.all_columns
        rows = [{c.name: sharepoint.csv_value(c.type, r.get(c.name)) for c in cols} for r in data.get(lst.name, [])]
        _write_csv(DIST / "seed_csv" / f"{lst.name}.csv", [c.name for c in cols], rows)
    _write_csv(DIST / "data_dictionary.csv", docs.DICT_HEADER, docs.dictionary_rows())

    (ROOT / "docs" / "data_dictionary.md").write_text(docs.dictionary_markdown() + "\n", encoding="utf-8")
    (ROOT / "docs" / "data_model_diagram.md").write_text(
        "# Data model diagram (all keys)\n\n"
        "_Generated from `pms/schema.py`. Shows each table's key (PK) and the columns that link to other tables (FK)._\n\n"
        "```mermaid\n" + docs.mermaid() + "\n```\n", encoding="utf-8")

    for name, count in written:
        print(f"dist/setup/{name}: {count} requests")
    print(f"dist/seed_csv/: {len(LISTS)} files, {sum(len(v) for v in data.values())} rows")


def periods_for(fy):
    rows = [r for r in periods.generate(fy, fy) if r["financial_year"] == periods.fy_label(fy)
            or r["period_type"] in ("calendar_year", "academic_year", "term") and r["start_date"].year >= fy]
    reqs = sharepoint.item_requests({"periods": rows})
    name = f"periods_fy{periods.fy_label(fy)}"
    for n, c in _write_requests(name, reqs):
        print(f"dist/setup/{n}: {c} requests. Check the term rows: dates come from TERM_DATES in pms/periods.py.")


def main(argv):
    if not argv or argv[0] == "build":
        build()
    elif argv[0] == "periods" and len(argv) == 2:
        periods_for(int(argv[1]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
