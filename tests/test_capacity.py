"""Every query the apps and flows make must be safe on lists over 5,000 items."""
import unittest

from pms import capacity
from pms.schema import LISTS


class QueryIndexTests(unittest.TestCase):
    def test_every_filtered_column_is_indexed(self):
        missing = []
        for q in capacity.QUERIES:
            for c in q.columns:
                col = capacity.column(q.list, c)
                if not col.indexed:
                    missing.append(f"{q.list}.{col.name} ({q.where})")
        self.assertEqual(missing, [], "add indexed=True in pms/schema.py")

    def test_list_views_filter_on_indexed_columns(self):
        import re
        for lst in LISTS:
            cols = {c.name: c for c in lst.all_columns}
            for v in lst.views:
                for name in re.findall(r"FieldRef Name='(\w+)'", v.where):
                    self.assertTrue(cols[name].indexed, f"{lst.name} view {v.name} filters on {name}")


class GrowthTests(unittest.TestCase):
    def test_open_work_fits_power_apps_limit(self):
        self.assertLess(capacity.open_submissions(capacity.Profile()), capacity.POWER_APPS_ROW_LIMIT)

    def test_small_lists_stay_under_power_apps_limit(self):
        fixed = capacity.fixed_rows(capacity.Profile())
        for name in ("measures", "people", "org_units", "groups"):
            self.assertLess(fixed[name], capacity.POWER_APPS_ROW_LIMIT, name)

    def test_script_runs_within_daily_limit(self):
        _, runs = capacity.flow_actions_per_day(capacity.Profile())
        self.assertLess(runs, 1600)

    def test_report_builds(self):
        text = capacity.report()
        self.assertIn("Every query, checked against the indexes", text)
        self.assertNotIn("\u2014", text)


if __name__ == "__main__":
    unittest.main()
