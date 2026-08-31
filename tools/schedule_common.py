from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "schedule.json"
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True)
class Reference:
    pattern: str
    previous_time: str


PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "schedule_time_element",
        re.compile(
            r'(?P<prefix><span\s+class="day-name">Вторник</span>\s*'
            r'<span\s+class="day-time">)'
            r'(?P<time>\d{2}:\d{2})'
        ),
    ),
    (
        "short_weekday",
        re.compile(r"(?P<prefix>\bВТ\s+)(?P<time>\d{2}:\d{2})"),
    ),
    (
        "weekday_text",
        re.compile(
            r"(?P<prefix>\b[Вв]торник(?:ам)?(?:,)?(?:\s+в)?\s+)"
            r"(?P<time>\d{2}:\d{2})"
        ),
    ),
    (
        "meeting_place",
        re.compile(
            r"(?P<prefix>Гагаринск(?:ого|ом)\s+парк(?:а|е)"
            r"(?:,\s*|\s+собираемся\s+в\s+|\s+в\s+))"
            r"(?P<time>\d{2}:\d{2})"
        ),
    ),
    (
        "tuesday_jsonld",
        re.compile(
            r'(?P<prefix>"dayOfWeek"\s*:\s*"Tuesday"\s*,\s*'
            r'"opens"\s*:\s*")(?P<time>\d{2}:\d{2})'
        ),
    ),
)


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    time = config.get("free_run", {}).get("time")
    if not isinstance(time, str) or not TIME_RE.fullmatch(time):
        raise ValueError(
            f"Некорректное время бесплатной пробежки в {CONFIG_PATH}: {time!r}"
        )
    counts = config.get("expected_reference_counts")
    if not isinstance(counts, dict):
        raise ValueError("expected_reference_counts должен быть объектом")
    invalid_counts = any(
        not isinstance(path, str) or not isinstance(count, int)
        for path, count in counts.items()
    )
    if invalid_counts:
        raise ValueError("expected_reference_counts должен содержать пары путь и целое число")
    return config


def public_html_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob("*.html")):
        if path.name != "template.html":
            yield path


def read_html(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def write_html(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def apply_time(text: str, expected_time: str) -> tuple[str, list[Reference]]:
    references: list[Reference] = []
    updated = text

    for name, pattern in PATTERNS:
        def replace(match: re.Match[str]) -> str:
            references.append(
                Reference(pattern=name, previous_time=match.group("time"))
            )
            return f'{match.group("prefix")}{expected_time}'

        updated = pattern.sub(replace, updated)

    return updated, references


def relative_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()

