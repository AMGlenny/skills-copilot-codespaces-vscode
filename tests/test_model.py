"""Checks that the schema, periods, rules and seed data are clean and consistent.

Run with:  python -m unittest discover -s tests
"""
import re
import unittest
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, timedelta

from pms import periods, rules, seed, sharepoint
from pms.schema import FREQUENCIES, LISTS, LISTS_BY_NAME, columns

SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
RESERVED = {"id", "title", "created", "modified", "author", "editor", "attachments", "contenttype",
            "order", "guid", "version", "path", "type"}

DATA = seed.build()


def by_key(list_name):
    key = LISTS_BY_NAME[list_name].key
    return {r[key]: r for r in DATA[list_name]}


class SchemaTests(unittest.TestCase):
    def test_names_are_snake_case_and_safe(self):
        for lst in LISTS:
            self.assertRegex(lst.name, SNAKE)
            names = [c.name for c in lst.all_columns]
            self.assertEqual(len(names), len(set(names)), lst.name)
            for n in names:
                self.assertRegex(n, SNAKE)
                self.assertLessEqual(len(n), 32, n)
                self.assertNotIn(n, RESERVED, f"{lst.name}.{n}")

    def test_choices_and_indexes(self):
        for lst in LISTS:
            for c in lst.all_columns:
                self.assertEqual(c.type == "choice", bool(c.choices), f"{lst.name}.{c.name}")
                if c.type == "note":
                    self.assertFalse(c.indexed, f"{lst.name}.{c.name}: long text cannot be indexed")
                if c.default is not None and c.choices:
                    self.assertIn(c.default, c.choices)

    def test_references_point_at_real_columns(self):
        for lst in LISTS:
            for c in lst.columns:
                if c.ref:
                    table, col = c.ref.split(".")
                    self.assertIn(table, LISTS_BY_NAME, c.ref)
                    self.assertIn(col, columns(table), c.ref)

    def test_periods_types_match_frequencies(self):
        self.assertEqual(columns("periods")["period_type"].choices, FREQUENCIES)
        self.assertEqual(columns("measures")["frequency"].choices, FREQUENCIES)

    def test_field_xml_is_valid(self):
        for lst in LISTS:
            for c in lst.columns:
                el = ET.fromstring(sharepoint.field_xml(c))
                self.assertEqual(el.get("Name"), c.name)
                self.assertEqual(el.get("DisplayName"), c.name)


class PeriodTests(unittest.TestCase):
    rows = periods.generate(2025, 2026, daily_from_fy=2026)

    def test_keys_unique(self):
        keys = [r["period_key"] for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_contiguous_and_non_overlapping(self):
        groups = defaultdict(list)
        for r in self.rows:
            self.assertLessEqual(r["start_date"], r["end_date"])
            groups[r["period_type"]].append(r)
        for ptype, rows in groups.items():
            rows.sort(key=lambda r: r["start_date"])
            for a, b in zip(rows, rows[1:]):
                if ptype == "term":
                    self.assertLess(a["end_date"], b["start_date"])
                else:
                    self.assertEqual(a["end_date"] + timedelta(days=1), b["start_date"], ptype)

    def test_uk_financial_year(self):
        p = {r["period_key"]: r for r in self.rows}
        self.assertEqual(p["Q-2026-27-Q1"]["start_date"], date(2026, 4, 1))
        self.assertEqual(p["Q-2026-27-Q4"]["end_date"], date(2027, 3, 31))
        self.assertEqual(p["FY-2026-27"]["period_type"], "annual")
        self.assertEqual(p["M-2027-02"]["financial_year"], "2026-27")
        self.assertEqual(p["M-2027-02"]["financial_quarter"], "2026-27 Q4")
        self.assertEqual(p["CY-2026"]["start_date"], date(2026, 1, 1))
        self.assertEqual(p["AY-2026-27"]["start_date"], date(2026, 9, 1))

    def test_weeks_start_monday(self):
        for r in self.rows:
            if r["period_type"] in ("weekly", "fortnightly"):
                self.assertEqual(r["start_date"].weekday(), 0, r["period_key"])

    def test_every_frequency_present(self):
        self.assertEqual({r["period_type"] for r in self.rows}, set(FREQUENCIES))


HIGHER_KPI = dict(unit="count", polarity="higher_is_better", measure_class="kpi")
LOWER_KPI = dict(unit="count", polarity="lower_is_better", measure_class="kpi")
HIGHER_MEASURE = dict(unit="count", polarity="higher_is_better", measure_class="measure")


class RuleTests(unittest.TestCase):
    def test_rag(self):
        cases = [
            (HIGHER_KPI, 100, False, 100, 90, "green"),
            (HIGHER_KPI, 95, False, 100, 90, "amber"),
            (HIGHER_KPI, 89, False, 100, 90, "red"),
            (HIGHER_KPI, 99, False, 100, None, "red"),
            (HIGHER_KPI, 95, False, None, 90, "green"),
            (HIGHER_KPI, 85, False, None, 90, "red"),
            (LOWER_KPI, 100, False, 100, 110, "green"),
            (LOWER_KPI, 105, False, 100, 110, "amber"),
            (LOWER_KPI, 111, False, 100, 110, "red"),
            (HIGHER_KPI, 50, False, None, None, "no_target"),
            (HIGHER_KPI, None, True, 100, 90, "no_data"),
            # Tolerance is ignored for plain measures.
            (HIGHER_MEASURE, 95, False, 100, 90, "red"),
            (HIGHER_MEASURE, 95, False, None, 90, "no_target"),
            (dict(HIGHER_KPI, polarity="neither"), 95, False, 100, 90, "not_applicable"),
            (dict(HIGHER_KPI, unit="text"), None, False, None, None, "not_applicable"),
        ]
        for m, v, missing, t, tol, expected in cases:
            self.assertEqual(rules.rag_status(m, v, missing, t, tol), expected, (m, v, t, tol))

    def test_validation(self):
        ok = rules.validate_value(HIGHER_KPI, 10, None, False, None, "green")
        self.assertEqual(ok, [])
        self.assertTrue(rules.validate_value(HIGHER_KPI, None, None, True, "", "no_data"))
        self.assertTrue(rules.validate_value(HIGHER_KPI, 10, None, False, None, "red"))
        self.assertTrue(rules.validate_value(HIGHER_KPI, 10.5, None, False, "x", "green"))
        self.assertTrue(rules.validate_value(dict(HIGHER_KPI, unit="yes_no"), 2, None, False, "x", "green"))
        self.assertTrue(rules.validate_value(dict(HIGHER_KPI, unit="text"), 3, None, False, "x", "green"))


class SeedTests(unittest.TestCase):
    def test_keys_unique_and_required_present(self):
        for lst in LISTS:
            rows = DATA.get(lst.name, [])
            keys = [r[lst.key] for r in rows]
            self.assertEqual(len(keys), len(set(keys)), lst.name)
            for r in rows:
                self.assertEqual(set(r), {c.name for c in lst.all_columns}, lst.name)
                for c in lst.all_columns:
                    if c.required:
                        self.assertIsNotNone(r[c.name], f"{lst.name}.{c.name} {r[lst.key]}")
                    if c.choices and r[c.name] is not None:
                        self.assertIn(r[c.name], c.choices, f"{lst.name}.{c.name}")

    def test_foreign_keys(self):
        for lst in LISTS:
            for c in lst.columns:
                if not c.ref:
                    continue
                table, col = c.ref.split(".")
                valid = {r[col] for r in DATA[table]}
                for r in DATA.get(lst.name, []):
                    if r[c.name] is not None:
                        self.assertIn(r[c.name], valid, f"{lst.name}.{c.name}={r[c.name]}")

    def test_contributes_to(self):
        groups, measures = by_key("groups"), by_key("measures")
        for name in ("tasks", "problems"):
            for r in DATA[name]:
                t, k = r["contributes_to_type"], r["contributes_to_key"]
                if t == "none":
                    self.assertIsNone(k)
                else:
                    self.assertIn(k, groups if t == "group" else measures)

    def test_no_placeholder_text(self):
        for name, rows in DATA.items():
            for r in rows:
                for v in r.values():
                    if isinstance(v, str):
                        self.assertNotIn(v.strip().upper(), {"N/A", "NA", "NULL", "-", ""}, name)

    def test_roles(self):
        roles = defaultdict(Counter)
        people = {}
        for r in DATA["measure_roles"]:
            if r["active"]:
                roles[r["measure_code"]][r["role"]] += 1
                people[(r["measure_code"], r["role"])] = r["email"]
        for m in DATA["measures"]:
            c = roles[m["measure_code"]]
            self.assertEqual(c["owner"], 1, m["measure_code"])
            self.assertGreaterEqual(c["updater"], 1, m["measure_code"])
            self.assertGreaterEqual(c["approver"], 1, m["measure_code"])
            self.assertNotEqual(people[(m["measure_code"], "owner")], people[(m["measure_code"], "approver")])

    def test_tolerance_only_for_kpi_and_okr(self):
        measures = by_key("measures")
        for r in DATA["reference_values"]:
            if r["ref_type"] == "tolerance":
                self.assertIn(measures[r["measure_code"]]["measure_class"], ("kpi", "okr"))

    def test_parent_child_patterns(self):
        measures = by_key("measures")
        same_ref = [m for m in measures.values() if m["parent_measure_code"]
                    and measures[m["parent_measure_code"]]["source_ref"] == m["source_ref"]]
        nested = [m for m in measures.values() if m["parent_measure_code"]
                  and m["source_ref"].startswith(measures[m["parent_measure_code"]]["source_ref"] + ".")]
        self.assertTrue(same_ref, "need a child sharing its parent's ref (1.01 and 1.01)")
        self.assertTrue(nested, "need a nested child (1 and 1.01)")

    def test_submissions_and_versions_consistent(self):
        measures, periods_ = by_key("measures"), by_key("periods")
        versions = defaultdict(list)
        for v in DATA["submission_versions"]:
            versions[v["submission_key"]].append(v)
        for s in DATA["submissions"]:
            m = measures[s["measure_code"]]
            self.assertEqual(s["submission_key"], f"{s['measure_code']}|{s['period_key']}")
            self.assertEqual(periods_[s["period_key"]]["period_type"], m["frequency"])
            vs = sorted(versions[s["submission_key"]], key=lambda v: v["version_no"])
            self.assertEqual([v["version_no"] for v in vs], list(range(1, len(vs) + 1)))
            self.assertEqual(s["current_version"], len(vs))
            approved = [v for v in vs if v["version_status"] == "approved"]
            self.assertLessEqual(len(approved), 1)
            if s["status"] == "not_started":
                self.assertEqual(vs, [])
            if s["status"] == "approved":
                self.assertEqual(s["approved_version"], s["current_version"])
            if s["approved_version"]:
                self.assertEqual(approved[0]["version_no"], s["approved_version"])
                self.assertIsNotNone(s["approved_by"])
            for v in vs:
                self.assertIn(v["entered_by"], {r["email"] for r in DATA["measure_roles"]
                                                if r["measure_code"] == m["measure_code"] and r["role"] == "updater"})
                self.assertGreater(v["entered_date"].date(), periods_[s["period_key"]]["end_date"] - timedelta(days=1))
                self.assertLessEqual(v["entered_date"].date(), seed.AS_OF)
                if v["submitted_date"]:
                    self.assertGreaterEqual(v["submitted_date"], v["entered_date"])
            if s["approved_date"]:
                self.assertLessEqual(s["approved_date"].date(), seed.AS_OF)
                self.assertGreaterEqual(s["approved_date"], s["submitted_date"])

    def test_submitted_values_pass_validation(self):
        measures = by_key("measures")
        for v in DATA["submission_versions"]:
            if v["version_status"] == "draft":
                continue
            m = measures[v["measure_code"]]
            errors = rules.validate_value(m, v["value_number"], v["value_text"], v["value_missing"],
                                          v["narrative"], v["rag_status"])
            self.assertEqual(errors, [], v["version_key"])
            if m["unit"] == "percent" and v["value_number"] is not None:
                self.assertTrue(0 <= v["value_number"] <= 100)

    def test_every_frequency_and_state_covered(self):
        measures = by_key("measures")
        approved_freqs = {measures[s["measure_code"]]["frequency"] for s in DATA["submissions"] if s["approved_version"]}
        self.assertEqual(approved_freqs, set(FREQUENCIES))
        self.assertEqual({s["status"] for s in DATA["submissions"]},
                         set(columns("submissions")["status"].choices))
        rags = {v["rag_status"] for v in DATA["submission_versions"]} - {None}
        self.assertEqual(rags, set(columns("submission_versions")["rag_status"].choices))
        self.assertTrue(any(m["status"] == "retired" for m in measures.values()))
        overdue = [s for s in DATA["submissions"] if s["status"] == "not_started"
                   and s["expected_by"] and s["expected_by"] < seed.AS_OF]
        self.assertTrue(overdue, "need an expected-but-not-received example")

    def test_rpt_values(self):
        approved = {s["submission_key"] for s in DATA["submissions"] if s["approved_version"]}
        rpt = DATA["rpt_values"]
        self.assertEqual({r["submission_key"] for r in rpt}, approved)
        latest = Counter(r["measure_code"] for r in rpt if r["is_latest"])
        self.assertTrue(all(n == 1 for n in latest.values()))
        self.assertEqual(set(latest), {r["measure_code"] for r in rpt})

    def test_weekly_work(self):
        people = by_key("people")
        for r in DATA["weekly_updates"] + DATA["wellbeing_checkins"]:
            self.assertEqual(r["week_start"].weekday(), 0)
        for r in DATA["wellbeing_checkins"]:
            self.assertEqual(r["line_manager_email"], people[r["email"]]["line_manager_email"])
        for r in DATA["tasks"]:
            self.assertEqual(r["completed_by"] is not None, r["status"] == "complete")
            self.assertEqual(r["completed_date"] is not None, r["status"] != "open")
        for r in DATA["problems"]:
            self.assertEqual(r["closed_date"] is not None, r["status"] == "closed")


class RequestTests(unittest.TestCase):
    def test_item_bodies_only_use_known_columns(self):
        for r in sharepoint.item_requests(DATA):
            name = re.search(r"getbytitle\('([a-z_]+)'\)", r["uri"]).group(1)
            allowed = {c.name for c in LISTS_BY_NAME[name].columns} | {"Title"}
            self.assertLessEqual(set(r["body"]), allowed)

    def test_dates_sent_as_midday_utc(self):
        for r in sharepoint.item_requests({"periods": DATA["periods"][:5]}):
            self.assertTrue(r["body"]["start_date"].endswith("T12:00:00Z"))


if __name__ == "__main__":
    unittest.main()
