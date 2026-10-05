from __future__ import annotations

import copy
import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_schedule
import schedule_common
from schedule_common import apply_schedule, load_config, read_html


def footer(text):
    return '<span style="display:block;padding:4px 0;font-size:0.95rem;">' + text + '</span>'


class ScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        cls.free_run = cls.config['free_run']

    def test_day_time_and_place_are_corrected_together(self):
        cases = (
            (footer('ВТ 19:15 · Гагаринский парк'), footer('СБ 10:00 · парк Шевченко')),
            ('Каждый вторник в 19:15 — открытая пробежка у Гагаринского парка.',
             'Каждую субботу в 10:00 — открытая пробежка в парке Шевченко.'),
            ('Бесплатная открытая пробежка (вторник, 19:15, Гагаринский парк)',
             'Бесплатная открытая пробежка (суббота, 10:00, парк Шевченко)'),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                updated, references = apply_schedule(source, self.free_run)
                self.assertEqual(expected, updated)
                self.assertEqual(1, len(references))

    def test_individual_stale_fields_are_detected(self):
        expected = footer('СБ 10:00 · парк Шевченко')
        for source in ('ВТ 10:00 · парк Шевченко', 'СБ 19:15 · парк Шевченко',
                       'СБ 10:00 · Гагаринский парк'):
            with self.subTest(source=source):
                self.assertEqual(expected, apply_schedule(footer(source), self.free_run)[0])

    def test_unrelated_days_places_and_card_are_preserved(self):
        source = ('Среда 19:00, пятница 19:00, воскресенье 09:00. '
                  'Интенсивная работа (вторник). Гагаринский парк, Салгирка. '
                  'СР 19:00 · Гагаринский парк\r\n'
                  '<span class="day-name">Среда</span>\r\n'
                  '        <span class="day-time">19:00</span>\r\n'
                  '        <p class="day-what">Темповая / интервалы.</p>')
        self.assertEqual((source, []), apply_schedule(source, self.free_run))

    def test_schema_for_other_training_days_is_preserved(self):
        source = ('{ "@type": "OpeningHoursSpecification", "dayOfWeek": "Wednesday", '
                  '"opens": "19:00", "closes": "20:30" }')
        self.assertEqual((source, []), apply_schedule(source, self.free_run))

    def test_new_schema_has_no_invented_end_time(self):
        source = read_html(schedule_common.ROOT / 'index.html')
        import re
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL)[1])
        hours = data['openingHoursSpecification']
        free = next(item for item in hours if item['dayOfWeek'] == 'Saturday')
        self.assertEqual('10:00', free['opens'])
        self.assertNotIn('closes', free)
        self.assertEqual(['Wednesday', 'Friday', 'Sunday'],
                         [item['dayOfWeek'] for item in hours if item is not free])

    def test_all_registered_contexts_are_idempotent(self):
        for name, count in self.config['expected_reference_counts'].items():
            with self.subTest(page=name):
                source = read_html(schedule_common.ROOT / name)
                updated, references = apply_schedule(source, self.free_run)
                self.assertEqual(source, updated)
                self.assertEqual(count, len(references))
                self.assertEqual(updated, apply_schedule(updated, self.free_run)[0])

    def test_line_endings_are_preserved(self):
        source = footer('ВТ 19:15 · Гагаринский парк') + '\r\nСреда 19:00\r\n'
        self.assertEqual(footer('СБ 10:00 · парк Шевченко') + '\r\nСреда 19:00\r\n',
                         apply_schedule(source, self.free_run)[0])

    def test_future_change_updates_day_time_and_place(self):
        free_run = dict(self.free_run, dayOfWeek='Thursday', time='18:30',
                        place='парк Победы', meeting_point='в парке Победы')
        source = 'Каждую субботу в 10:00 — открытая пробежка в парке Шевченко.'
        expected = 'Каждый четверг в 18:30 — открытая пробежка в парке Победы.'
        self.assertEqual(expected, apply_schedule(source, free_run)[0])
        self.assertEqual(expected, apply_schedule(expected, free_run)[0])

    def test_invalid_configuration_is_rejected(self):
        for fields in ({'time': '25:00'}, {'dayOfWeek': 'Unknown'}, {'place': ''},
                       {'meeting_point': '<script>'}, {'effective_from': '2026-10-11'}):
            with self.subTest(fields=fields), TemporaryDirectory() as folder:
                config = copy.deepcopy(self.config)
                config['free_run'].update(fields)
                path = Path(folder) / 'schedule.json'
                path.write_text(json.dumps(config), encoding='utf-8')
                with patch.object(schedule_common, 'CONFIG_PATH', path), self.assertRaises(ValueError):
                    load_config()

    def test_missing_unregistered_and_stale_references_fail_check(self):
        for text, count in (('нет расписания', 1), (footer('ВТ 19:15 · Гагаринский парк'), 1),
                            (footer('СБ 10:00 · парк Шевченко'), 0)):
            with self.subTest(text=text, count=count), TemporaryDirectory() as folder:
                path = Path(folder) / 'index.html'
                path.write_text(text, encoding='utf-8')
                counts = {'index.html': count} if count else {}
                config = dict(self.config, expected_reference_counts=counts)
                with patch.object(check_schedule, 'load_config', return_value=config), \
                     patch.object(check_schedule, 'public_html_files', return_value=[path]), \
                     patch.object(check_schedule, 'relative_path', return_value='index.html'), \
                     redirect_stdout(StringIO()):
                    self.assertEqual(1, check_schedule.main())


if __name__ == '__main__':
    unittest.main()
