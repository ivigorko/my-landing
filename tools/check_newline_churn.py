"""Reject mass newline-only changes in existing text files."""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    '.css', '.html', '.js', '.json', '.md', '.py', '.txt', '.xml', '.yaml', '.yml'
}
MIN_EOL_CHURN = 20


def changed_line_count(before: list[str], after: list[str]) -> int:
    """Count added and removed lines in SequenceMatcher opcodes."""
    total = 0
    for tag, old_start, old_end, new_start, new_end in SequenceMatcher(
            None, before, after, autojunk=False).get_opcodes():
        if tag != 'equal':
            total += old_end - old_start
            total += new_end - new_start
    return total


def newline_churn(before: bytes, after: bytes) -> tuple[int, int, int]:
    """Return raw, semantic and newline-only changed-line counts."""
    raw_before = before.decode('utf-8').splitlines(keepends=True)
    raw_after = after.decode('utf-8').splitlines(keepends=True)
    semantic_before = before.decode('utf-8').splitlines()
    semantic_after = after.decode('utf-8').splitlines()
    raw = changed_line_count(raw_before, raw_after)
    semantic = changed_line_count(semantic_before, semantic_after)
    return raw, semantic, max(0, raw - semantic)


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ['git', *args], cwd=ROOT, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False
    )


def available_ref(reference: str) -> bool:
    return git('rev-parse', '--verify', '--quiet', reference).returncode == 0


def comparison_base() -> str | None:
    explicit = os.environ.get('PREFLIGHT_BASE_REF')
    if explicit:
        return explicit if available_ref(explicit) else None
    if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and available_ref('HEAD^1'):
        return 'HEAD^1'
    if available_ref('origin/main'):
        return 'origin/main'
    if available_ref('HEAD^1'):
        return 'HEAD^1'
    return None


def in_pull_request_ci() -> bool:
    return os.environ.get('GITHUB_EVENT_NAME') == 'pull_request'


def changed_files(base: str) -> list[str]:
    target = ('HEAD',) if in_pull_request_ci() else ()
    result = git('diff', '--name-only', '--diff-filter=AM', base, *target, '--')
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip())
    return result.stdout.decode('utf-8').splitlines()


def base_file(base: str, relative: str) -> bytes | None:
    result = git('show', f'{base}:{relative}')
    if result.returncode != 0:
        return None
    return result.stdout


def current_file(relative: str) -> bytes | None:
    if in_pull_request_ci():
        result = git('show', f'HEAD:{relative}')
        return result.stdout if result.returncode == 0 else None
    path = ROOT / relative
    return path.read_bytes() if path.is_file() else None


def check(base: str | None = None) -> int:
    if not (ROOT / '.git').exists():
        print('SKIP: newline churn requires a Git checkout')
        return 0
    base = base or comparison_base()
    if not base:
        print('Newline check failed: comparison base is unavailable')
        return 1

    failures = []
    checked = 0
    for relative in changed_files(base):
        path = ROOT / relative
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        before = base_file(base, relative)
        after = current_file(relative)
        if before is None or after is None:
            continue
        checked += 1
        raw, semantic, eol_only = newline_churn(before, after)
        if eol_only >= MIN_EOL_CHURN and raw > max(semantic * 2, MIN_EOL_CHURN):
            failures.append((relative, raw, semantic, eol_only))

    if failures:
        print('Mass newline-only changes found:')
        for relative, raw, semantic, eol_only in failures:
            print(
                f'- {relative}: raw churn {raw}, semantic churn {semantic}, '
                f'newline-only churn {eol_only}'
            )
        return 1
    print(f'OK: no mass newline-only changes in {checked} existing text files')
    return 0


if __name__ == '__main__':
    raise SystemExit(check(sys.argv[1] if len(sys.argv) > 1 else None))
