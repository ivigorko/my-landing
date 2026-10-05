"""Run the same complete site checks locally and in CI (stdlib only)."""
from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COUNTER_ID = '103646147'
METRIKA = re.compile(rb'mc\.yandex\.ru/watch/103646147|data-metrika-counter="103646147"')
INSTAGRAM = re.compile(rb"href=[\"'][^\"'\n]*(instagram\.com|instagr\.am)", re.IGNORECASE)


def check_metrika(root=ROOT):
    pages = sorted(path for path in root.rglob('*.html')
                   if path.is_file() and path.name != 'template.html')
    missing = [path.relative_to(root).as_posix() for path in pages
               if not METRIKA.search(path.read_bytes())]
    if missing:
        print(f'Yandex.Metrika {COUNTER_ID} is missing on:')
        for name in missing:
            print(f'- {name}')
        return 1
    print(f'OK: Metrika {COUNTER_ID} present on {len(pages)} pages')
    return 0


def check_four_paws(root=ROOT):
    matches = []
    for name in ('4-lapy', 'assets/4-lapy'):
        folder = root / name
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        for path in sorted(folder.rglob('*')):
            if path.is_file() and INSTAGRAM.search(path.read_bytes()):
                matches.append(path.relative_to(root).as_posix())
    if matches:
        print('Instagram links are not allowed in the Four Paws section:')
        for name in matches:
            print(f'- {name}')
        return 1
    print('OK: no Instagram links found in the Four Paws section')
    return 0


def python_check(*args):
    return subprocess.run([sys.executable, '-X', 'utf8', *args], cwd=ROOT,
                          check=False).returncode


def main():
    checks = (
        ('Metrika', check_metrika),
        ('Four Paws links', check_four_paws),
        ('Tests (schedule, publication, preflight)',
         lambda: python_check('-m', 'unittest', 'tools/test_schedule.py',
                              'tools/test_publication.py', 'tools/test_preflight.py')),
        ('Schedule', lambda: python_check('tools/check_schedule.py')),
        ('Publication', lambda: python_check('tools/check_publication.py')),
    )
    failed = []
    for name, check in checks:
        print(f'== {name} ==', flush=True)
        try:
            code = check()
        except Exception as error:
            print(f'{name}: {type(error).__name__}: {error}', flush=True)
            code = 1
        if code != 0:
            failed.append(name)
            print(f'FAIL: {name} (exit {code})', flush=True)
    summary = ('FAIL: ' + ', '.join(failed)) if failed else 'OK: all site checks passed'
    print(summary, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
            output.write(summary + '\n')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
