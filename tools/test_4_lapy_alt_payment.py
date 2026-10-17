from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
THANKS = (ROOT / "4-lapy" / "thanks.html").read_text(encoding="utf-8")
LANDING = (ROOT / "4-lapy" / "index.html").read_text(encoding="utf-8")

PHONE = "+7 978 947 06 24"


class AlternativePaymentTests(unittest.TestCase):
    def test_thanks_page_contains_alternative_tbank_payment(self):
        self.assertIn(PHONE, THANKS)
        self.assertIn("переведите 1 500 ₽ по номеру телефона", THANKS)
        self.assertIn("Т-Банк", THANKS)
        self.assertIn("В комментарии к переводу укажите номер заявки", THANKS)

    def test_phone_is_not_published_on_landing_page(self):
        self.assertNotIn(PHONE, LANDING)


if __name__ == "__main__":
    unittest.main()
