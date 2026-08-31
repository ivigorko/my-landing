from __future__ import annotations

import argparse

from schedule_common import (
    apply_time,
    load_config,
    public_html_files,
    read_html,
    relative_path,
    write_html,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Синхронизировать время бесплатной пробежки во всех HTML-файлах."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать изменения без записи файлов.",
    )
    args = parser.parse_args()

    config = load_config()
    expected_time = config["free_run"]["time"]
    total_references = 0
    changed_files = 0

    for path in public_html_files():
        source = read_html(path)
        updated, references = apply_time(source, expected_time)
        if not references:
            continue

        total_references += len(references)
        changed = updated != source
        status = "изменится" if changed else "совпадает"
        print(f"{relative_path(path)}: {len(references)} ссылок, {status}")

        if changed:
            changed_files += 1
            if not args.dry_run:
                write_html(path, updated)

    mode = "Проверено" if args.dry_run else "Синхронизировано"
    print(
        f"{mode}: {total_references} ссылок; "
        f"файлов с изменениями: {changed_files}; время: {expected_time}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

