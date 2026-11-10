from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FourLapyLocationTest(unittest.TestCase):
    def test_confirmed_location_is_consistent_and_children_terms_are_preserved(self):
        index = (ROOT / "4-lapy" / "index.html").read_text(encoding="utf-8")
        thanks = (ROOT / "4-lapy" / "thanks.html").read_text(encoding="utf-8")
        rules = (ROOT / "4-lapy" / "rules.html").read_text(encoding="utf-8")

        for page in (index, thanks, rules):
            self.assertIn("сквер имени владимира жириновского", page.lower())
            self.assertNotIn("Гагаринский парк", page)

        self.assertIn(
            "https://yandex.ru/maps/org/skver_imeni_vladimira_zhirinovskogo/171459332497/",
            index,
        )
        self.assertIn("Детские слоты открыты", index)
        self.assertIn("Участвовать можно с 4 лет", index)
        self.assertIn("1 км и 1 500 рублей", index)
        self.assertNotIn("500 м", index)

    def test_extended_registration_deadline_is_visible(self):
        index = (ROOT / "4-lapy" / "index.html").read_text(encoding="utf-8")

        self.assertEqual(index.count("Регистрацию продлили до 8 ноября включительно"), 2)
        self.assertNotIn("Регистрация открыта до 31 октября", index)
        self.assertNotIn("До 31 октября включительно", index)

    def test_confirmed_schedule_has_prominent_first_screen_block(self):
        index = (ROOT / "4-lapy" / "index.html").read_text(encoding="utf-8")
        styles = (ROOT / "assets" / "4-lapy" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('class="schedule-highlight"', index)
        self.assertIn("Расписание старта", index)
        self.assertIn(">9:15</time>", index)
        self.assertIn(">10:00</time>", index)
        self.assertIn(">10:30</time>", index)
        self.assertIn(".schedule-highlight", styles)
        self.assertNotIn("Дата и время", index)


if __name__ == "__main__":
    unittest.main()

