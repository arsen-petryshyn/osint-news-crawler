# OSINT News Crawler — Ukrinform.ua

Простий pipeline для збору новин з [Ukrinform.ua](https://www.ukrinform.ua) за допомогою Crawl4AI.

## Архітектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ config.json │────>│ worker-html  │────>│ data/raw/*.html  │
│ (URLs)      │     │ (Crawl4AI +  │     │ data/norm/*.json │
└─────────────┘     │  BS4 parser) │     └─────────────────┘
                    └──────────────┘
```

**worker-html** — контейнер, який:
1. Відкриває listing-сторінки рубрик
2. Збирає посилання на статті
3. Завантажує кожну статтю
4. Зберігає raw HTML + normalized JSON

## JSON-формат (normalized)

```json
{
  "url": "https://www.ukrinform.ua/rubric-polytics/...",
  "title": "Заголовок статті",
  "fetched_at": "2026-05-04T12:00:00+00:00",
  "source": "ukrinform.ua",
  "content": "Текст статті...",
  "links": ["https://..."]
}
```

## Запуск

### Через Docker Compose (рекомендовано)

```bash
docker compose up --build
```

Результати з'являться в `data/raw/` та `data/normalized/`.

### Локально (без Docker)

```bash
pip install -r requirements.txt
crawl4ai-setup
python worker_html.py
```

## Структура проекту

```
.
├── compose.yaml          # Docker Compose конфігурація
├── Dockerfile            # Образ для worker-html
├── config.json           # Налаштування: URLs, ліміти
├── worker_html.py        # Основний парсер
├── requirements.txt      # Python залежності
├── data/
│   ├── raw/              # Сирий HTML
│   └── normalized/       # Нормалізований JSON
└── README.md
```

## Коли потрібен worker-js?

Worker-js потрібен для сайтів, де контент рендериться через JavaScript (SPA, React, Vue тощо).
Ukrinform.ua віддає контент у звичайному HTML, тому worker-html достатньо.
Приклади, де знадобився б worker-js:
- Twitter/X — стрічка завантажується через JS API
- Facebook — контент рендериться клієнтським React
- Сайти з infinite scroll або lazy loading

Crawl4AI підтримує JS-rendering через Playwright, тому для worker-js достатньо увімкнути `wait_for` або `js_code` параметри в `CrawlerRunConfig`.
