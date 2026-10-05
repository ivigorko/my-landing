from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'data' / 'schedule.json'
TIME_RE = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d$')
WEEKDAYS = {
    'Monday': ('понедельник', 'в понедельник', 'каждый понедельник', 'понедельникам', 'понедельниках', 'ПН'),
    'Tuesday': ('вторник', 'во вторник', 'каждый вторник', 'вторникам', 'вторниках', 'ВТ'),
    'Wednesday': ('среда', 'в среду', 'каждую среду', 'средам', 'средах', 'СР'),
    'Thursday': ('четверг', 'в четверг', 'каждый четверг', 'четвергам', 'четвергах', 'ЧТ'),
    'Friday': ('пятница', 'в пятницу', 'каждую пятницу', 'пятницам', 'пятницах', 'ПТ'),
    'Saturday': ('суббота', 'в субботу', 'каждую субботу', 'субботам', 'субботах', 'СБ'),
    'Sunday': ('воскресенье', 'в воскресенье', 'каждое воскресенье', 'воскресеньям', 'воскресеньях', 'ВС'),
}

# Полные контексты бесплатной пробежки сохраняют остальные дни и маршруты.
BINDINGS = (
    'В неделе: среда (темповая или интервалы, 19:00), пятница (ОФП для бегунов, без бега, 19:00), {day} (открытая пробежка {meeting_point}, {time}, всегда бесплатно), воскресенье (длинная пробежка 20+ км, 09:00). {rest_days} — дни отдыха.',
    'Этот парк — исторически главная площадка для стартов и сборов клуба. Теперь бесплатная открытая пробежка проходит по {plural_day} в {time} {meeting_point}.',
    '4 тренировки в неделю — среда, пятница (ОФП, без бега), {day}, воскресенье. {rest_days} — дни отдыха',
    '{{ "@type": "OpeningHoursSpecification", "dayOfWeek": "{schema_day}", "opens": "{time}" }}',
    'Открытая пробежка клуба ПРОБег проходит по {plural_day} в {time}, сбор {meeting_point}.',
    '<span class="day-name">{day_title}</span>\n        <span class="day-time">{time}</span>\n        <p class="day-what">Бесплатная открытая пробежка {meeting_point}. Темп подбирается под группу.</p>',
    'открытая пробежка {on_day}, темповая в среду, ОФП в пятницу и длительная в воскресенье',
    '{on_day_title} в {time} клуб собирается на бесплатную пробежку {meeting_point}.',
    '<span>{day} {time}</span><span>первая тренировка бесплатно</span>',
    '{each_day} в {time}, сбор {meeting_point}. Бежим в лёгком темпе.',
    '{each_day_title} в {time} — открытая пробежка {meeting_point}.',
    'Расписание клуба ПРОБег: открытая пробежка {on_day} в {time},',
    '<strong>{short_day} {time}</strong><span>бесплатная пробежка',
    'Бесплатная открытая пробежка {on_day} оплаты не требует.',
    '{day_title} {time} — открытая пробежка {meeting_point}.',
    'на открытую пробежку {on_day} в {time} {meeting_point}',
    'Первая тренировка бесплатно, {meeting_point} в {time}.',
    'В клубе ПРОБег — {short_day} {time} открытая пробежка',
    '<strong>{short_day} {time}</strong> открытая пробежка',
    'Бесплатная открытая пробежка ({day}, {time}, {place})',
    '<label>Сбор</label><span class="val">{place}</span>',
    'По {plural_day} {meeting_point} собираемся в {time}',
    'Открытая пробежка в клубе ПРОБег по {plural_day}',
    '{day_title} {time}</strong> — открытая пробежка',
    'Бесплатная открытая пробежка {meeting_point}.',
    'Место сбора — {place} (для открытых пробежек)',
    'Открытая пробежка {on_day} всегда бесплатная.',
    'приходите на бесплатную пробежку {on_day} в {time} {meeting_point}',
    'на открытую пробежку {on_day} и попросить',
    '{each_day} в {time}, сбор {meeting_point}',
    'на обычных средах и {prepositional_days}',
    'на следующую открытую пробежку {on_day}.',
    'На открытой пробежке {on_day} мы делаем',
    '{day_title}, {time} — открытая пробежка',
    'Сбор {meeting_point} {on_day} в {time}',
    'ждут тебя {meeting_point} {on_day}',
    'открытые пробежки по {plural_day}',
    '{short_day} {time} — бесплатно',
    '<span style="display:block;padding:4px 0;font-size:0.95rem;">{short_day} {time} · {place}</span>',
    'открытой пробежкой {on_day}.',
    'хватает открытой {on_day}',
)


@dataclass(frozen=True)
class Reference:
    previous_text: str
    expected_text: str


def schedule_values(free_run: dict) -> dict[str, str]:
    day, on_day, each_day, plural, prepositional, short = WEEKDAYS[free_run['dayOfWeek']]
    training_days = {'Wednesday', 'Friday', 'Sunday', free_run['dayOfWeek']}
    rest = ', '.join(forms[0] for key, forms in WEEKDAYS.items() if key not in training_days)
    return {
        'day': day, 'day_title': day.capitalize(), 'on_day': on_day,
        'on_day_title': on_day.capitalize(), 'each_day': each_day,
        'each_day_title': each_day.capitalize(), 'plural_day': plural,
        'prepositional_days': prepositional, 'short_day': short,
        'schema_day': free_run['dayOfWeek'], 'rest_days': rest.capitalize(),
        'time': free_run['time'], 'place': free_run['place'],
        'meeting_point': free_run['meeting_point'],
    }


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    free_run = config.get('free_run', {})
    if free_run.get('dayOfWeek') not in WEEKDAYS:
        raise ValueError('Некорректный день бесплатной пробежки')
    time = free_run.get('time')
    if not isinstance(time, str) or not TIME_RE.fullmatch(time):
        raise ValueError(f'Некорректное время бесплатной пробежки: {time!r}')
    for field in ('place', 'meeting_point'):
        value = free_run.get(field)
        if not isinstance(value, str) or not value.strip() or re.search(r'[<>"\r\n{}]', value):
            raise ValueError(f'Некорректное место бесплатной пробежки: {field}')
    effective_from = date.fromisoformat(free_run['effective_from'])
    if effective_from.weekday() != list(WEEKDAYS).index(free_run['dayOfWeek']):
        raise ValueError('Дата начала расписания не совпадает с днём пробежки')
    counts = config.get('expected_reference_counts')
    if not isinstance(counts, dict) or any(
        not isinstance(path, str) or type(count) is not int or count <= 0
        for path, count in counts.items()
    ):
        raise ValueError('expected_reference_counts должен содержать путь и положительное целое число')
    return config


def public_html_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob('*.html')):
        if path.name != 'template.html':
            yield path


def read_html(path: Path) -> str:
    return path.read_bytes().decode('utf-8')


def write_html(path: Path, text: str) -> None:
    path.write_bytes(text.encode('utf-8'))


def binding_pattern(template: str) -> str:
    weekday_fields = {
        'day': 0, 'day_title': 0, 'on_day': 1, 'on_day_title': 1,
        'each_day': 2, 'each_day_title': 2, 'plural_day': 3,
        'prepositional_days': 4, 'short_day': 5,
    }
    parts = []
    for literal, field, _, _ in Formatter().parse(template):
        parts.append(re.escape(literal).replace(re.escape('\n'), r'\r?\n'))
        if field:
            if field in weekday_fields:
                forms = [values[weekday_fields[field]] for values in WEEKDAYS.values()]
                if field.endswith('_title'):
                    forms = [value.capitalize() for value in forms]
                parts.append('(?:' + '|'.join(re.escape(value) for value in forms) + ')')
            elif field == 'schema_day':
                parts.append('(?:' + '|'.join(WEEKDAYS) + ')')
            elif field == 'time':
                parts.append(r'\d{2}:\d{2}')
            elif field in ('place', 'meeting_point'):
                parts.append(r'[^<>"\r\n.,;()]{1,100}')
            else:
                parts.append(r'[^<>"\r\n]{1,100}?')
    return ''.join(parts)


def apply_schedule(text: str, free_run: dict) -> tuple[str, list[Reference]]:
    values = schedule_values(free_run)
    references = []
    templates = sorted(BINDINGS, key=len, reverse=True)
    pattern = re.compile('|'.join(
        f'(?P<b{index}>{binding_pattern(template)})'
        for index, template in enumerate(templates)
    ))

    def replace(match: re.Match[str]) -> str:
        template = templates[int(match.lastgroup[1:])]
        expected = template.format(**values)
        if '\r\n' in match.group():
            expected = expected.replace('\n', '\r\n')
        references.append(Reference(match.group(), expected))
        return expected

    return pattern.sub(replace, text), references


def relative_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()
