import unittest

from app.tr_template import format_date_pt_br_extenso


class DateFormatExtensoTests(unittest.TestCase):
    def test_iso_date_to_extenso(self):
        self.assertEqual(format_date_pt_br_extenso("2026-05-29"), "29 de maio de 2026")

    def test_us_slash_date_to_extenso(self):
        self.assertEqual(format_date_pt_br_extenso("5/29/2026"), "29 de maio de 2026")

    def test_br_slash_date_to_extenso(self):
        self.assertEqual(format_date_pt_br_extenso("29/5/2026"), "29 de maio de 2026")

    def test_non_date_keeps_original(self):
        self.assertEqual(format_date_pt_br_extenso("maio/2026"), "maio/2026")


if __name__ == "__main__":
    unittest.main()
