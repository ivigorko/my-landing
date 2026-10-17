import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLES = (ROOT / "assets" / "4-lapy" / "styles.css").read_text(encoding="utf-8")


def css_rule(selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", STYLES)
    if not match:
        raise AssertionError(f"Не найдено CSS-правило {selector}")
    return match.group(1)


def css_rules(selector: str) -> list[str]:
    return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", STYLES)


class FourLapyFormSpacingTests(unittest.TestCase):
    def test_grid_does_not_stretch_fields_to_the_tallest_neighbor(self):
        self.assertRegex(css_rule(".field-grid"), r"align-items\s*:\s*start")

    def test_field_does_not_duplicate_the_grid_row_gap(self):
        rules = css_rules(".field")
        self.assertTrue(rules)
        for rule in rules:
            margins = re.findall(r"margin-bottom\s*:\s*([^;]+)", rule)
            self.assertTrue(all(value.strip() == "0" for value in margins))

    def test_empty_feedback_rows_do_not_reserve_space(self):
        feedback = css_rule(".field-error:empty, .field-advisory:empty")
        self.assertRegex(feedback, r"display\s*:\s*none")


if __name__ == "__main__":
    unittest.main()
