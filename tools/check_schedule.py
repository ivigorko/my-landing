from __future__ import annotations

from schedule_common import (
    apply_schedule,
    load_config,
    public_html_files,
    read_html,
    relative_path,
)


def main() -> int:
    config = load_config()
    free_run = config["free_run"]
    expected_counts = config["expected_reference_counts"]
    actual_counts: dict[str, int] = {}
    errors: list[str] = []

    for path in public_html_files():
        source = read_html(path)
        updated, references = apply_schedule(source, free_run)
        if not references:
            continue

        relative = relative_path(path)
        actual_counts[relative] = len(references)
        mismatches = sorted(
            {
                reference.previous_text
                for reference in references
                if reference.previous_text != reference.expected_text
            }
        )
        if updated != source:
            errors.append(
                f"{relative}: найдено несогласованное расписание {', '.join(mismatches)}"
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
        f"{total} ссылок, бесплатная пробежка: {free_run['dayOfWeek']}, {free_run['time']}, {free_run['place']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

