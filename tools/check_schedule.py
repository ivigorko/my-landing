from __future__ import annotations

from schedule_common import (
    apply_time,
    load_config,
    public_html_files,
    read_html,
    relative_path,
)


def main() -> int:
    config = load_config()
    expected_time = config["free_run"]["time"]
    expected_counts = config["expected_reference_counts"]
    actual_counts: dict[str, int] = {}
    errors: list[str] = []

    for path in public_html_files():
        source = read_html(path)
        updated, references = apply_time(source, expected_time)
        if not references:
            continue

        relative = relative_path(path)
        actual_counts[relative] = len(references)
        mismatches = sorted(
            {
                reference.previous_time
                for reference in references
                if reference.previous_time != expected_time
            }
        )
        if updated != source:
            errors.append(
                f"{relative}: найдено несогласованное время {', '.join(mismatches)}"
            )

    for relative, expected_count in sorted(expected_counts.items()):
        actual_count = actual_counts.get(relative, 0)
        if actual_count != expected_count:
            errors.append(
                f"{relative}: ожидалось ссылок {expected_count}, найдено {actual_count}"
            )

    unregistered = sorted(set(actual_counts) - set(expected_counts))
    for relative in unregistered:
        errors.append(
            f"{relative}: файл содержит {actual_counts[relative]} ссылок, но не зарегистрирован"
        )

    if errors:
        print("Проверка расписания не пройдена:")
        for error in errors:
            print(f"- {error}")
        return 1

    total = sum(actual_counts.values())
    print(
        f"Расписание согласовано: {len(actual_counts)} файлов, "
        f"{total} ссылок, время бесплатной пробежки {expected_time}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

