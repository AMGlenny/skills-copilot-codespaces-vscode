"""Checks every export is tidy, self-describing and safe, and that the Office
Script produces exactly the same output as the Python reference."""
import csv
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pms import exports, seed
from pms.schema import LISTS_BY_NAME

ROOT = Path(__file__).resolve().parent.parent
DATA = seed.build()
SAMPLES = exports.build_samples(DATA, seed.AS_OF)
SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
NEVER_EXPORTED_LISTS = {"wellbeing_checkins", "review_comments", "audit_log", "export_requests", "settings", "export_jobs"}


def read_csv(text):
    assert text.startswith("﻿"), "CSV files start with a byte order mark so Excel reads £ correctly"
    return list(csv.reader(io.StringIO(text[1:], newline="")))


class TidyTests(unittest.TestCase):
    def test_every_file_is_tidy(self):
        for dataset, files in SAMPLES.items():
            types = {(t["name"], c["name"]): c["type"] for t in exports.DATASETS[dataset]["tables"] for c in t["columns"]}
            for fname, text in files.items():
                if not fname.endswith(".csv"):
                    continue
                rows = read_csv(text)
                header, body = rows[0], rows[1:]
                table = fname[:-4]
                self.assertEqual(len(header), len(set(header)), fname)
                for h in header:
                    self.assertRegex(h, SNAKE, fname)
                for r in body:
                    self.assertEqual(len(r), len(header), f"{dataset}/{fname}")
                    self.assertNotIn(r[0].strip().lower(), {"total", "totals", "grand total"})
                    for h, v in zip(header, r):
                        self.assertNotIn(v.strip().upper(), {"N/A", "NA", "NULL", "NONE", "-"}, f"{fname}.{h}")
                        t = types.get((table, h), "text")
                        if v == "":
                            continue
                        if t == "date":
                            self.assertRegex(v, r"^\d{4}-\d{2}-\d{2}$", f"{fname}.{h}")
                        elif t == "datetime":
                            self.assertRegex(v, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", f"{fname}.{h}")
                        elif t == "number":
                            float(v)
                        elif t == "bool":
                            self.assertIn(v, ("true", "false"), f"{fname}.{h}")

    def test_every_export_has_dictionary_readme_and_info(self):
        for dataset, files in SAMPLES.items():
            for f in ("data_dictionary.csv", "README_for_AI.md", "export_info.txt"):
                self.assertIn(f, files, dataset)
            documented = {(r[0], r[1]) for r in read_csv(files["data_dictionary.csv"])[1:]}
            actual = set()
            for fname, text in files.items():
                if fname.endswith(".csv") and fname != "data_dictionary.csv":
                    actual |= {(fname[:-4], h) for h in read_csv(text)[0]}
            self.assertEqual(documented, actual, dataset)
            for r in read_csv(files["data_dictionary.csv"])[1:]:
                self.assertTrue(r[3].strip(), f"{dataset}: {r[0]}.{r[1]} has no description")
        self.assertIn("prompt_quarterly_report.md", SAMPLES["quarter_pack"])

    def test_lookup_columns_filled(self):
        rows = read_csv(SAMPLES["weekly_work"]["tasks.csv"])
        header = rows[0]
        for r in rows[1:]:
            rec = dict(zip(header, r))
            self.assertTrue(rec["team_name"])
            self.assertTrue(rec["raised_by_name"])
            if rec["contributes_to_key"]:
                self.assertTrue(rec["contributes_to_name"], rec["task_code"])

    def test_text_that_looks_like_numbers_stays_text(self):
        rows = read_csv(SAMPLES["measures"]["values_flat.csv"])
        refs = {r[rows[0].index("source_ref")] for r in rows[1:]}
        self.assertIn("1.01", refs)


class SafetyTests(unittest.TestCase):
    def test_restricted_data_never_exported(self):
        for name, d in exports.DATASETS.items():
            for t in d["tables"]:
                self.assertNotIn(t["list"], NEVER_EXPORTED_LISTS, f"{name}.{t['name']}")
                names = {c["name"] for c in t["columns"]}
                self.assertFalse(names & {"line_manager_email", "wellbeing", "comment", "reviewer_email"}, t["name"])

    def test_only_approved_values(self):
        for name, d in exports.DATASETS.items():
            for t in d["tables"]:
                if t["list"] == "submission_versions":
                    self.assertEqual(t["filter"], "version_status eq 'approved'")

    def test_selects_use_real_columns(self):
        defs = exports.definitions_json()
        for d in defs["datasets"].values():
            for t in d["tables"]:
                internal = {"Title"} | {c.name for c in LISTS_BY_NAME[t["list"]].columns}
                for f in t["select"].split(","):
                    self.assertIn(f, internal, f"{t['name']}: {f}")
                for c in t["columns"]:
                    for lk in c.get("lookup", []):
                        self.assertIn(lk["table"], defs["lookup_tables"])
        json.dumps(defs)  # must be plain JSON


class DateAndScheduleTests(unittest.TestCase):
    def test_uk_date(self):
        cases = {
            "2026-09-28T12:00:00Z": "2026-09-28",   # seed data, midday UTC
            "2026-09-27T23:00:00Z": "2026-09-28",   # midnight BST
            "2026-12-01T00:00:00Z": "2026-12-01",   # midnight GMT
            "2026-03-29T00:30:00Z": "2026-03-29",   # just before clocks go forward
            "2026-03-29T23:00:00Z": "2026-03-30",   # first BST midnight
            "2026-10-24T23:00:00Z": "2026-10-25",   # last BST midnight
            "2026-10-25T23:00:00Z": "2026-10-25",   # GMT again
            "2026-07-01T09:15:00.123Z": "2026-07-01",
        }
        for iso, expected in cases.items():
            self.assertEqual(exports.uk_date(iso), expected, iso)

    def test_previous_quarter(self):
        self.assertEqual(exports.previous_fy_quarter(date(2026, 10, 10)), "2026-27 Q2")
        self.assertEqual(exports.previous_fy_quarter(date(2026, 4, 10)), "2025-26 Q4")
        self.assertEqual(exports.previous_fy_quarter(date(2027, 1, 10)), "2026-27 Q3")
        self.assertEqual(exports.previous_fy_quarter(date(2026, 7, 1)), "2026-27 Q1")

    def test_job_due(self):
        job = dict(active=True, frequency="weekly", run_day=1)
        self.assertTrue(exports.job_due(job, date(2026, 9, 28)))  # Monday
        self.assertFalse(exports.job_due(job, date(2026, 9, 29)))
        q = dict(active=True, frequency="quarterly", run_day=10)
        self.assertTrue(exports.job_due(q, date(2026, 10, 10)))
        self.assertFalse(exports.job_due(q, date(2026, 11, 10)))
        self.assertTrue(exports.job_due(dict(active=True, frequency="daily", run_day=None), date(2026, 1, 1)))
        self.assertFalse(exports.job_due(dict(active=False, frequency="daily", run_day=None), date(2026, 1, 1)))


TRICKY_TABLE = dict(name="tricky", columns=[
    dict(name="key", source="Title", type="text", description="x"),
    dict(name="note", source="note", type="text", description="x"),
    dict(name="amount", source="amount", type="number", description="x"),
    dict(name="flag", source="flag", type="bool", description="x"),
    dict(name="day", source="day", type="date", description="x"),
    dict(name="at", source="at", type="datetime", description="x"),
    dict(name="who", lookup_from="who", type="text", description="x",
         lookup=[dict(table="groups", field="group_name"), dict(table="people", field="display_name")]),
])
TRICKY_ITEMS = [
    dict(Title="1.10", note='He said "hi", then left', amount=5.0, flag=True, day="2026-09-27T23:00:00Z",
         at="2026-09-30T06:00:00.5Z", who="p@x"),
    dict(Title="0012", note="line one\nline two", amount=0.1, flag=False, day="2026-12-01T00:00:00Z",
         at="2026-12-01T00:00:00Z", who="G1"),
    dict(Title="k3", note=" leading space", amount=None, flag=None, day=None, at=None, who="unknown"),
    dict(Title="k4", note="£1,250 spent", amount=-1250.75, flag="true", day="2026-03-29T00:30:00Z", at=None, who=None),
]
TRICKY_LOOKUPS = {"groups": [dict(Title="G1", group_name="Group one")],
                  "people": [dict(Title="p@x", display_name="Pat X")]}


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class OfficeScriptParityTests(unittest.TestCase):
    """Runs the Office Script's transform in node (types stripped) and
    compares it with the Python reference on the same input."""

    @classmethod
    def run_script(cls, cases):
        source = (ROOT / "office_scripts" / "PMSExport.ts").read_text(encoding="utf-8")
        harness = source + """
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = input.map((c) => toCsv(c.table.columns.map((x) => x.name), transform(c.table, c.items, c.lookups), true));
process.stdout.write(JSON.stringify(out));
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "harness.ts"
            path.write_text(harness, encoding="utf-8")
            result = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", str(path)],
                                    input=json.dumps(cases), capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def python_csv(self, table, items, lookups):
        headers, rows = exports.transform(table, items, lookups)
        return exports.to_csv(headers, rows)

    def test_tricky_values_match(self):
        js, = self.run_script([dict(table=TRICKY_TABLE, items=TRICKY_ITEMS, lookups=TRICKY_LOOKUPS)])
        py = self.python_csv(TRICKY_TABLE, TRICKY_ITEMS, TRICKY_LOOKUPS)
        self.assertEqual(js, py)
        self.assertIn('"He said ""hi"", then left"', py)
        self.assertIn("1.10,", py)
        self.assertIn(",2026-09-28,", py)

    def test_all_sample_tables_match(self):
        lookups = {t: exports.sp_items(t, DATA[t]) for t in exports.LOOKUP_TABLES}
        cases = []
        for d in exports.DATASETS.values():
            for t in d["tables"]:
                cases.append(dict(table=t, items=exports.sp_items(t["list"], DATA[t["list"]]), lookups=lookups))
        js = self.run_script(cases)
        for case, out in zip(cases, js):
            self.assertEqual(out, self.python_csv(case["table"], case["items"], lookups), case["table"]["name"])


if __name__ == "__main__":
    unittest.main()
