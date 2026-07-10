# ПРОБег · сайт бегового клуба

Финальная вёрстка сайта бегового клуба ПРОБег (Симферополь).

## Структура

```
probeg-final/
├── index.html              ← главная
├── blog.html               ← лента блога (список статей)
├── assets/
│   ├── logo.png            ← логотип
│   ├── yana.jpg            ← фото тренера
│   └── blog/
│       ├── start.jpg       ← «Как начать бегать» (3:2, 2K)
│       ├── technique.jpg   ← «Техника бега» (3:2, 2K)
│       └── pulse.jpg       ← «Пульсовые зоны» (3:2, 2K)
└── blog/
    ├── kak-nachat-begat.html
    ├── tehnika-bega.html
    └── pulsovye-zony.html
```

## Как развернуть

1. Залей всю папку как есть на хостинг (FTP/SFTP/панель). Структура каталогов должна сохраниться — `assets/`, `assets/blog/` и `blog/` рядом с `index.html` и `blog.html`.
2. Точка входа — `index.html` (он же `/`).
3. Никакого серверного рендеринга не нужно, чистый статический сайт.

## Что поправить перед публикацией

### 1. Домен в мета-тегах (обязательно)
В файлах `blog.html`, `blog/kak-nachat-begat.html`, `blog/tehnika-bega.html`, `blog/pulsovye-zony.html` найди и замени плейсхолдер на свой реальный домен:

```
probeg.example.com  →  твой.домен
```

Где встречается: `<link rel="canonical">`, `<meta property="og:url">`, `<meta property="og:image">`, JSON-LD блок `"url"` и `"@id"`.

Проще всего через `sed`:
```bash
sed -i 's|probeg.example.com|твой.домен|g' blog.html blog/*.html
```

### 2. ВКонтакте (уже указан актуальный)
Везде стоит ссылка `https://vk.com/probeg_simf` (группа Яны). Если сменится handle — замени глобально:
```bash
sed -i 's|vk.com/probeg_simf|vk.com/новый-handle|g' index.html blog.html blog/*.html
```

### 3. Картинки блога
Если захочешь заменить сгенерированные фото на реальные съёмки — просто положи свои файлы в `assets/blog/` под теми же именами (`start.jpg`, `technique.jpg`, `pulse.jpg`). Размер любой — они подгоняются через CSS `object-fit: cover`.

### 4. Цены на абонементы
В `index.html`, секция «Абонементы», найди блок `<div class="price-card">` для каждого тарифа и обнови `<div class="p-amount">`.

### 5. Расписание тренировок
В `index.html`, секция «Расписание», карточки `.day-card`. Меняй текст, дни, время, описание.

## Что внутри (страницы)

| URL | Что |
|---|---|
| `/` | Главная: hero, расписание, уровни, тренер Яна, абонементы, превью блога, CTA |
| `/blog.html` | Лента блога со всеми статьями |
| `/blog/kak-nachat-begat.html` | «Как начать бегать: первая неделя» |
| `/blog/tehnika-bega.html` | «Техника бега: 5 ошибок, которые делают все» |
| `/blog/pulsovye-zony.html` | «Пульсовые зоны: зачем следить за пульсом» |

## SEO

Каждая страница блога имеет:
- Уникальный `<title>` и `<meta description>`
- `<link rel="canonical">` (плейсхолдер — замени на свой домен)
- Open Graph + Twitter Card (для красивого шеринга в соцсетях)
- JSON-LD Schema.org `Article` (для Google)

Когда подключишь домен — заодно:
- Зарегистрировать в Яндекс.Вебмастере и Google Search Console
- Добавить `sitemap.xml`
- Добавить `robots.txt`

Удачи!
