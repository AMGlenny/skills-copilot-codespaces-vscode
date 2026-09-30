"""Static checks on the Power Apps source: YAML parses, control names are
unique, and formulas only refer to controls, screens and columns that exist.

Needs PyYAML (pip install pyyaml); skipped if it isn't installed.
"""
import re
import unittest
from pathlib import Path

from pms.schema import LISTS

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

APP = Path(__file__).resolve().parent.parent / "powerapps" / "weekly"
SCREENS = {p.name.split(".")[0] for p in APP.glob("scr*.pa.yaml")}
COLUMNS = {c.name for lst in LISTS for c in lst.all_columns} | {"ID", "sort_open"}
CONTROL_PREFIX = re.compile(r"\b((?:txt|dd|cmb|dp|btn|chk|gal|lbl|icn|con|rect)[A-Z]\w*)")
LIST_NAMES = {lst.name for lst in LISTS}


def walk(nodes, out):
    for node in nodes:
        (name, body), = node.items()
        out.append((name, body))
        walk(body.get("Children", []), out)


def strip_comments(formula):
    return re.sub(r"//[^\n]*", "", formula)


@unittest.skipIf(yaml is None, "PyYAML not installed")
class PowerAppsSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = []
        cls.by_file = {}
        for path in sorted(APP.glob("*.pa.yaml")):
            items = []
            walk(yaml.safe_load(path.read_text(encoding="utf-8")), items)
            cls.by_file[path.name] = items
            cls.controls += items
        cls.names = {n for n, _ in cls.controls}
        cls.app_pfx = strip_comments((APP / "App.pfx").read_text(encoding="utf-8"))

    def formulas(self):
        for name, body in self.controls:
            for prop, value in body.get("Properties", {}).items():
                yield name, prop, value

    def test_every_screen_file_present(self):
        self.assertEqual(SCREENS, {"scrWeek", "scrTask", "scrProblem", "scrTeam"})

    def test_controls_well_formed_and_unique(self):
        self.assertEqual(len(self.names), len(self.controls), "duplicate control names")
        for name, body in self.controls:
            self.assertIn("Control", body, name)
            self.assertRegex(body["Control"], r"^[A-Za-z/]+@\d+\.\d+\.\d+$", name)

    def test_properties_are_formulas(self):
        for name, prop, value in self.formulas():
            self.assertIsInstance(value, str, f"{name}.{prop}")
            self.assertTrue(value.startswith("="), f"{name}.{prop} must start with =")

    def test_referenced_controls_exist(self):
        for name, prop, value in self.formulas():
            for ref in CONTROL_PREFIX.findall(strip_comments(value)):
                self.assertIn(ref, self.names, f"{name}.{prop} refers to unknown control {ref}")

    def test_referenced_screens_exist(self):
        for name, prop, value in self.formulas():
            for ref in re.findall(r"Navigate\((\w+)", value):
                self.assertIn(ref, SCREENS, f"{name}.{prop}")

    def test_columns_exist(self):
        pattern = re.compile(r"\b(?:ThisItem|varTask|varProblem|varUpdate|varCheckin|fxPerson|r)\.(\w+)")
        for name, prop, value in self.formulas():
            for col in pattern.findall(strip_comments(value)):
                self.assertIn(col, COLUMNS | {"display_name", "type", "key", "label", "code", "path"},
                              f"{name}.{prop} uses unknown column {col}")

    def test_patched_lists_exist(self):
        text = self.app_pfx + "".join(v for _, _, v in self.formulas())
        for ref in re.findall(r"(?:Patch|Defaults|Filter|LookUp)\(\s*([a-z_]+)\b", text):
            if not ref.startswith(("col", "fx")):
                self.assertIn(ref, LIST_NAMES)

    def test_brace_balance(self):
        for name, prop, value in self.formulas():
            v = re.sub(r'"[^"]*"', "", strip_comments(value))
            self.assertEqual(v.count("("), v.count(")"), f"{name}.{prop} brackets")
            self.assertEqual(v.count("{"), v.count("}"), f"{name}.{prop} braces")


if __name__ == "__main__":
    unittest.main()
