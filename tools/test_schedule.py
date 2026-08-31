from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from schedule_common import apply_time  # noqa: E402


class ApplyTimeTests(unittest.TestCase):
    def test_supported_free_run_contexts_are_updated(self) -> None:
        cases = (
            "ВТ 20:00",
            "каждый вторник в 20:00",
            "Вторник, 20:00",
            "по вторникам в Гагаринском парке собираемся в 20:00",
            '<span class="day-name">Вторник</span>\n'
            '<span class="day-time">20:00</span>',
            '"dayOfWeek": "Tuesday", "opens": "20:00"',
        )

        for source in cases:
            with self.subTest(source=source):
                updated, references = apply_time(source, "19:15")
                self.assertIn("19:15", updated)
                self.assertNotIn("20:00", updated)
                self.assertEqual(1, len(references))

    def test_unrelated_time_is_not_changed(self) -> None:
        source = "Среда 20:00, окончание тренировки в 21:30"
        updated, references = apply_time(source, "19:15")

        self.assertEqual(source, updated)
        self.assertEqual([], references)

    def test_line_endings_are_preserved(self) -> None:
        source = "ВТ 20:00\r\nСреда 19:00\r\n"
        updated, _ = apply_time(source, "19:15")

        self.assertEqual("ВТ 19:15\r\nСреда 19:00\r\n", updated)


if __name__ == "__main__":
    unittest.main()

