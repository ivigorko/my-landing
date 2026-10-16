"""Tests for newline churn detection."""
from pathlib import Path
from unittest.mock import patch
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_newline_churn as checker
from check_newline_churn import changed_line_count, newline_churn


class NewlineChurnTests(unittest.TestCase):
    def test_identical_content_has_no_churn(self):
        content = b'one\r\ntwo\nthree\r\n'
        self.assertEqual((0, 0, 0), newline_churn(content, content))

    def test_semantic_edit_with_preserved_endings_has_no_eol_churn(self):
        before = b'one\r\ntwo\r\nthree\r\n'
        after = b'one\r\nchanged\r\nthree\r\n'
        raw, semantic, eol_only = newline_churn(before, after)
        self.assertEqual(semantic, raw)
        self.assertEqual(0, eol_only)

    def test_mass_line_ending_change_is_detected(self):
        before = ''.join(f'line {number}\n' for number in range(40)).encode()
        after = ''.join(
            f'line {number}\r\n' if number != 20 else 'changed\r\n'
            for number in range(40)
        ).encode()
        raw, semantic, eol_only = newline_churn(before, after)
        self.assertGreater(raw, semantic * 2)
        self.assertGreaterEqual(eol_only, 20)

    def test_changed_line_count_counts_both_sides(self):
        self.assertEqual(2, changed_line_count(['a'], ['b']))

    def test_pull_request_compares_committed_trees(self):
        completed = subprocess.CompletedProcess([], 0, b'tools/preflight.py\n', b'')
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'pull_request'}), \
             patch.object(checker, 'git', return_value=completed) as run:
            self.assertEqual(['tools/preflight.py'], checker.changed_files('HEAD^1'))
        run.assert_called_once_with(
            'diff', '--name-only', '--diff-filter=AM', 'HEAD^1', 'HEAD', '--'
        )

    def test_local_check_compares_working_tree(self):
        completed = subprocess.CompletedProcess([], 0, b'tools/preflight.py\n', b'')
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': ''}), \
             patch.object(checker, 'git', return_value=completed) as run:
            self.assertEqual(['tools/preflight.py'], checker.changed_files('origin/main'))
        run.assert_called_once_with(
            'diff', '--name-only', '--diff-filter=AM', 'origin/main', '--'
        )


if __name__ == '__main__':
    unittest.main()
