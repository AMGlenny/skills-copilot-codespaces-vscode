"""Automated WCAG 2.2 AA checks on the Power Apps source.

These catch the things a machine can check: colour contrast, accessible
names, target size, headings and focus indicators. docs/accessibility.md
lists the manual checks (screen reader, keyboard, zoom) still needed.
"""
import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

APPS = Path(__file__).resolve().parent.parent / "powerapps"
INPUTS = ("Classic/TextInput", "Classic/DropDown", "Classic/ComboBox", "Classic/DatePicker")
ALLOWED_EXTRA_COLOURS = {"FFD166", "D0D0D0"}  # focus ring on dark header; decorative divider lines


def luminance(hex6):
    def ch(v):
        c = int(v, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = hex6[0:2], hex6[2:4], hex6[4:6]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def colours(app):
    text = (APPS / app / "App.pfx").read_text(encoding="utf-8")
    found = {k: v.upper() for k, v in re.findall(r'(clr\w+) = ColorValue\("#([0-9A-Fa-f]{6})"\)', text)}
    found["clrPanel"] = "FFFFFF"
    found["White"] = "FFFFFF"
    return found


def controls(app):
    out = []

    def walk(nodes, screen):
        for node in nodes:
            (name, body), = node.items()
            out.append((screen, name, body))
            walk(body.get("Children", []), screen)
    for path in sorted((APPS / app).glob("scr*.pa.yaml")):
        walk(yaml.safe_load(path.read_text(encoding="utf-8")), path.name.split(".")[0])
    return out


def number(value):
    m = re.fullmatch(r"=\s*(\d+)", str(value).strip())
    return int(m.group(1)) if m else None


@unittest.skipIf(yaml is None, "PyYAML not installed")
class AccessibilityTests(unittest.TestCase):
    apps = ("weekly", "measures")

    def test_colour_contrast(self):
        for app in self.apps:
            c = colours(app)
            text_colours = ["clrText", "clrMuted", "clrAccent", "clrAccentDark", "clrError", "clrSuccess", "clrHeader"]
            text_colours += [k for k in ("clrGreen", "clrAmber", "clrRed") if k in c]
            for fg in text_colours:
                for bg in ("clrPanel", "clrPage"):
                    ratio = contrast(c[fg], c[bg])
                    self.assertGreaterEqual(ratio, 4.5, f"{app}: {fg} on {bg} is {ratio:.2f}:1 (1.4.3 needs 4.5:1)")
            for bg in ("clrHeader", "clrAccent", "clrAccentDark"):
                ratio = contrast("FFFFFF", c[bg])
                self.assertGreaterEqual(ratio, 4.5, f"{app}: white on {bg} is {ratio:.2f}:1")
            # Non-text contrast (1.4.11): input borders and focus indicators need 3:1.
            for bg in ("clrPanel", "clrPage"):
                self.assertGreaterEqual(contrast(c["clrBorder"], c[bg]), 3, f"{app}: input borders")
            self.assertGreaterEqual(contrast("FFD166", c["clrHeader"]), 3, "focus ring on the header")
            self.assertGreaterEqual(contrast(c["clrText"], c["clrPanel"]), 3, "focus ring on white")

    def test_old_grey_header_would_have_failed(self):
        self.assertLess(contrast("FFFFFF", "B3B3B3"), 4.5)

    def test_only_design_colours_used(self):
        for app in self.apps:
            known = set(colours(app).values())
            for screen, name, body in controls(app):
                for prop, value in body.get("Properties", {}).items():
                    for hex6 in re.findall(r'ColorValue\("#([0-9A-Fa-f]{6})"\)', str(value)):
                        self.assertIn(hex6.upper(), known | ALLOWED_EXTRA_COLOURS, f"{screen}.{name}.{prop}")

    def test_inputs_have_accessible_names(self):
        for app in self.apps:
            for screen, name, body in controls(app):
                kind = body["Control"].split("@")[0]
                props = body.get("Properties", {})
                if kind in INPUTS or kind == "Gallery":
                    self.assertIn("AccessibleLabel", props, f"{screen}.{name} (4.1.2 name, role, value)")
                if kind == "Classic/Icon" and "OnSelect" in props:
                    self.assertIn("AccessibleLabel", props, f"{screen}.{name}")
                    self.assertEqual(props.get("TabIndex"), "=0", f"{screen}.{name} must be reachable by keyboard")
                if kind == "Classic/CheckBox":
                    self.assertTrue(props.get("Text"), f"{screen}.{name} needs a visible label")

    def test_target_size(self):
        for app in self.apps:
            for screen, name, body in controls(app):
                kind = body["Control"].split("@")[0]
                props = body.get("Properties", {})
                if kind not in ("Classic/Button", "Classic/Icon") or props.get("Visible") == "=false":
                    continue
                for dim in ("Width", "Height"):
                    n = number(props.get(dim, ""))
                    if n is not None:
                        self.assertGreaterEqual(n, 24, f"{screen}.{name}.{dim} (2.5.8 target size)")
                if kind == "Classic/Button":
                    self.assertIn("FocusedBorderThickness", props, f"{screen}.{name} (2.4.7 focus visible)")
                    self.assertGreaterEqual(number(props["FocusedBorderThickness"]), 2)

    def test_each_screen_has_one_main_heading(self):
        for app in self.apps:
            by_screen = {}
            for screen, name, body in controls(app):
                if body.get("Properties", {}).get("Role") == "=TextRole.Heading1":
                    by_screen[screen] = by_screen.get(screen, 0) + 1
            screens = {s for s, _, _ in controls(app)}
            for s in screens:
                self.assertEqual(by_screen.get(s, 0), 1, f"{s} needs exactly one Heading1 (1.3.1, 2.4.6)")

    def test_text_not_too_small(self):
        for app in self.apps:
            for screen, name, body in controls(app):
                n = number(body.get("Properties", {}).get("Size", ""))
                if n is not None:
                    self.assertGreaterEqual(n, 11, f"{screen}.{name}")

    def test_screens_reflow(self):
        for app in self.apps:
            for path in (APPS / app).glob("scr*.pa.yaml"):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Width: =Parent.Width", text, path.name)
                self.assertTrue("fxIsNarrow" in text or "Min(App.Width" in text,
                                f"{path.name} must adapt to narrow screens (1.4.10 reflow)")

    def test_status_messages_announced(self):
        for app in self.apps:
            live = [n for _, n, b in controls(app) if b.get("Properties", {}).get("Live") == "=Live.Polite"]
            self.assertTrue(live, f"{app}: needs polite live regions for status messages (4.1.3)")


if __name__ == "__main__":
    unittest.main()
