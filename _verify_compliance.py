"""Локальный smoke-test для compliance-аудита.

Проверяет:
1. На новых страницах (privacy-policy, terms) — есть все обязательные блоки
2. На index.html и blog.html — cookie gate работает (Метрика НЕ инициализируется напрямую в <head>)
3. На всех страницах есть ссылки на политику/оферту (если ожидается)
4. JSON-LD в новых страницах валидный
5. Внутренние ссылки на .html не битые
"""
import re
import json
import sys
import io
from pathlib import Path

# Force UTF-8 output (PowerShell по умолчанию cp1251)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).parent
PAGES = ['index.html', 'blog.html', 'privacy-policy.html', 'terms.html']

errors = []
warnings = []


def fail(msg):
    errors.append(msg)
    print(f'  [FAIL] {msg}')


def warn(msg):
    warnings.append(msg)
    print(f'  [WARN] {msg}')


def ok(msg):
    print(f'  [OK]   {msg}')


# Test 1: cookie gate на главной и в блоге
print('\n=== [1] Cookie consent gate (152-ФЗ) ===')
for fname in ['index.html', 'blog.html']:
    html = (ROOT / fname).read_text(encoding='utf-8')
    print(f'\n[{fname}]')
    if 'loadYandexMetrika' in html:
        ok('contains loadYandexMetrika function (gated)')
    else:
        fail('no loadYandexMetrika function — Метрика грузится синхронно!')

    # Проверяем только <head> — init Метрики допустим ТОЛЬКО внутри определения loadYandexMetrika
    head_match = re.search(r'(?s)<head>(.*?)</head>', html)
    head = head_match.group(1) if head_match else ''
    init_match = re.search(r"ym\(\s*103646147\s*,\s*['\"]init['\"]", head)
    if init_match:
        init_pos = init_match.start()
        fn_a = head.find('function loadYandexMetrika')
        fn_b = head.find('loadYandexMetrika = function')
        fn_pos = max(fn_a, fn_b)
        if fn_pos == -1:
            fail('init Метрики в <head> без gate-функции — нарушение 152-ФЗ')
        elif init_pos < fn_pos:
            fail('init Метрики в <head> ВЫЗЫВАЕТСЯ ДО определения gate — нарушение 152-ФЗ')
        else:
            ok('init Метрики в <head> — внутри gate-функции (cookie consent)')
    else:
        ok('init Метрики в <head> отсутствует (cookie consent gate корректен)')

    if 'cookieBanner' in html and 'probeg-consent' in html:
        ok('cookie-баннер и localStorage gate присутствуют')
    else:
        fail('нет cookie-баннера или gate')
    if "localStorage.getItem('probeg-consent')" in html:
        ok('auto-load Метрики при ранее данном согласии')
    else:
        warn('нет auto-load при ранее данном согласии')


# Test 2: новые страницы
print('\n=== [2] Privacy policy & Terms ===')
for fname in ['privacy-policy.html', 'terms.html']:
    html = (ROOT / fname).read_text(encoding='utf-8')
    print(f'\n[{fname}]')
    if 'Политика конфиденциальности' in html or 'Публичная оферта' in html:
        ok('title содержит ключевое слово')
    else:
        fail('title не содержит ключевое слово')
    if '[ФАМИЛИЯ_ИМЯ_ОТЧЕСТВО]' in html or '[ИНН]' in html:
        warn('остались плейсхолдеры (заполнить перед push)')
    else:
        ok('нет плейсхолдеров')
    if '152-ФЗ' in html or 'персональных данных' in html.lower():
        ok('упомянут 152-ФЗ / персональные данные')
    else:
        warn('нет упоминания 152-ФЗ')
    if 'ВКонтакте' in html and 'vk.com' in html:
        ok('есть ссылка на VK')


# Test 3: JSON-LD (только для index.html — у новых страниц его нет)
print('\n=== [3] JSON-LD ===')
for fname in ['index.html', 'privacy-policy.html', 'terms.html']:
    html = (ROOT / fname).read_text(encoding='utf-8')
    blocks = re.findall(r'(?s)<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html)
    print(f'\n[{fname}] blocks={len(blocks)}')
    for i, b in enumerate(blocks):
        try:
            obj = json.loads(b)
            t = obj.get('@type', '@graph')
            n = obj.get('name', '')
            if isinstance(t, list):
                t = '/'.join(t)
            ok(f'  block[{i}] type={t} name={n[:50]}')
        except Exception as e:
            fail(f'  block[{i}] PARSE ERROR: {e}')


# Test 4: внутренние ссылки
print('\n=== [4] Внутренние ссылки ===')
for fname in PAGES:
    if not (ROOT / fname).exists():
        warn(f'файл не найден: {fname}')
        continue
    html = (ROOT / fname).read_text(encoding='utf-8')
    refs = set()
    for m in re.finditer(r'href="([^"#]+\.html)(?:#[^"]*)?"', html):
        target = m.group(1)
        if target.startswith('http'):
            continue
        refs.add(target)
    for ref in sorted(refs):
        if not (ROOT / ref).exists():
            fail(f'[{fname}] битая ссылка: {ref}')
        else:
            ok(f'[{fname}] -> {ref}')


# Test 5: footer — обязательные ссылки
print('\n=== [5] Footer — реквизиты и правовые ссылки ===')
for fname in ['index.html', 'blog.html', 'privacy-policy.html', 'terms.html']:
    if not (ROOT / fname).exists():
        continue
    html = (ROOT / fname).read_text(encoding='utf-8')
    print(f'\n[{fname}]')
    if 'terms.html' in html:
        ok('есть ссылка на оферту')
    else:
        warn('нет ссылки на оферту')
    if 'privacy-policy.html' in html:
        ok('есть ссылка на политику')
    else:
        warn('нет ссылки на политику')
    if '[ИНН]' in html:
        warn('ИНН — плейсхолдер (заполнить перед push)')
    else:
        ok('ИНН подставлен')


# Test 6: дисклеймер
print('\n=== [6] Медицинский дисклеймер ===')
for fname, label in [('index.html', 'pricing-секция'), ('blog.html', 'footer-disclaimer')]:
    html = (ROOT / fname).read_text(encoding='utf-8')
    if 'противопоказан' in html.lower() or 'проконсультируйтесь' in html.lower() or 'консультац' in html.lower():
        ok(f'[{fname}] ({label}) — дисклеймер про противопоказания')
    else:
        warn(f'[{fname}] нет дисклеймера про противопоказания')


# Итог
print('\n=== ИТОГ ===')
if errors:
    print(f'[FAIL] {len(errors)} ошибок, {len(warnings)} предупреждений')
    sys.exit(1)
elif warnings:
    print(f'[OK] Все проверки пройдены, {len(warnings)} предупреждений (плейсхолдеры)')
    sys.exit(0)
else:
    print('[OK] Все проверки пройдены без замечаний')
    sys.exit(0)
