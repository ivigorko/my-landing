"""Regression tests for CI/local orchestration and the migrated shell checks."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight


class PreflightTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        (self.root / '4-lapy').mkdir()
        (self.root / 'assets/4-lapy').mkdir(parents=True)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_both_metrika_forms_and_only_template_exemption(self):
        self.write('page with spaces.html', b'mc.yandex.ru/watch/103646147')
        self.write('nested/page.html', b'data-metrika-counter="103646147"')
        self.write('nested/template.html', b'no counter')
        with redirect_stdout(StringIO()):
            self.assertEqual(0, preflight.check_metrika(self.root))
            self.write('blog.html', b'mc.yandex.ru/watch/999')
            self.assertEqual(1, preflight.check_metrika(self.root))

    def test_metrika_matches_legacy_grep(self):
        cases = [b'mc.yandex.ru/watch/103646147', b'data-metrika-counter="103646147"',
                 b'data-metrika-counter="999"', b'DATA-METRIKA-COUNTER="103646147"',
                 b"data-metrika-counter='103646147'", b'no counter']
        for source in cases:
            with self.subTest(source=source), redirect_stdout(StringIO()):
                path = self.write('index.html', source)
                old = subprocess.run(['grep', '-Eq',
                    r'mc\.yandex\.ru/watch/103646147|data-metrika-counter="103646147"', str(path)])
                self.assertEqual(old.returncode, preflight.check_metrika(self.root))

    def test_instagram_matches_legacy_grep_in_both_directories(self):
        cases = [b'<a href="https://instagram.com/x">', b"HREF='https://INSTAGR.AM/x'",
                 b'href="https://vk.com/x"', b'instagram.com plain text',
                 b'href="https://example.com/\ninstagram.com"']
        for name in ('4-lapy/nested/page.html', 'assets/4-lapy/links.js'):
            for source in cases:
                with self.subTest(name=name, source=source), redirect_stdout(StringIO()):
                    path = self.write(name, source)
                    old = subprocess.run(['grep', '-qiE',
                        r'''href=["'][^"']*(instagram\.com|instagr\.am)''', str(path)])
                    self.assertEqual(int(old.returncode == 0), preflight.check_four_paws(self.root))
                    path.unlink()

    def test_instagram_outside_four_paws_is_not_rejected(self):
        self.write('blog.html', b'href="https://instagram.com/x"')
        with redirect_stdout(StringIO()):
            self.assertEqual(0, preflight.check_four_paws(self.root))

    def test_missing_directory_and_read_error_are_not_silently_accepted(self):
        (self.root / '4-lapy').rmdir()
        with self.assertRaises(FileNotFoundError):
            preflight.check_four_paws(self.root)
        self.write('index.html', b'counter')
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('unreadable')):
            with self.assertRaises(PermissionError):
                preflight.check_metrika(self.root)

    def run_main(self, codes=(0, 0, 0), metrika=0, four_paws=0, error=None):
        output = StringIO()
        with patch.object(preflight, 'check_metrika', return_value=metrika, side_effect=error), \
             patch.object(preflight, 'check_four_paws', return_value=four_paws), \
             patch.object(preflight, 'python_check', side_effect=codes) as runner, \
             patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''}), redirect_stdout(output):
            code = preflight.main()
        self.assertEqual([
            ('-m', 'unittest', 'tools/test_schedule.py', 'tools/test_publication.py', 'tools/test_preflight.py'),
            ('tools/check_schedule.py',), ('tools/check_publication.py',)
        ], [call.args for call in runner.call_args_list])
        return code, output.getvalue()

    def test_all_existing_suites_and_checks_run_on_success(self):
        self.assertEqual(0, self.run_main()[0])

    def test_each_group_failure_fails_without_skipping_remaining_checks(self):
        for position in range(5):
            codes = [0] * 5
            codes[position] = 7
            with self.subTest(position=position):
                self.assertEqual(1, self.run_main(codes[2:], *codes[:2])[0])

    def test_exception_fails_and_remaining_checks_still_run(self):
        code, output = self.run_main(error=OSError('cannot read'))
        self.assertEqual(1, code)
        self.assertIn('OSError: cannot read', output)

    def test_subprocess_uses_current_python_utf8_root_and_propagates_exit(self):
        with patch.object(preflight.subprocess, 'run') as run:
            run.return_value.returncode = 9
            self.assertEqual(9, preflight.python_check('tools/check_schedule.py'))
            run.assert_called_once_with(
                [sys.executable, '-X', 'utf8', 'tools/check_schedule.py'],
                cwd=preflight.ROOT, check=False)

    def test_ci_summary_records_failure(self):
        summary = self.root / 'summary.md'
        with patch.object(preflight, 'check_metrika', return_value=1), \
             patch.object(preflight, 'check_four_paws', return_value=0), \
             patch.object(preflight, 'python_check', return_value=0), \
             patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}), redirect_stdout(StringIO()):
            self.assertEqual(1, preflight.main())
        self.assertEqual('FAIL: Metrika\n', summary.read_text())


if __name__ == '__main__':
    unittest.main()
