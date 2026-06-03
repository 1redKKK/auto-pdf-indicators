# Модуль M10 «Безопасность дорожного движения» (ИГИС-БДД)

Веб-приложение для статистического мониторинга безопасности дорожного движения
по г. Москва. Включает KPI-дашборд, контрольные карты Шухарта, автоматические
предупреждения по правилам Нельсона, интерактивную карту ДТП и генерацию
PDF-отчётов с мини-картами участков.

Полная спецификация — [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md).

---

## Запуск

Доступны два пути: **через Docker** (рекомендуется — ничего ставить не надо)
и **локальный** (Python + Node, для разработки).

### 1. Через Docker (рекомендуется)

Единственное требование — установленный **Docker Desktop**.

```powershell
docker compose up -d
```

Откройте http://localhost:8000

Первая сборка ~3 минуты (npm + apt + pip), потом образ кешируется. Парквет с
данными (`backend/data/processed/moscow_3y.parquet`, 1.4 МБ, 36 месяцев
Янв 2023 — Дек 2025) лежит в репо — никаких дополнительных файлов не нужно.
GTK для PDF, шрифты, всё что нужно — внутри образа.

Команды:

```powershell
docker compose logs -f m10        # логи в реальном времени
docker compose restart m10        # рестарт
docker compose down               # остановить и снести контейнер
docker compose down -v            # + удалить volumes (PDF и acknowledged-статусы)
docker compose build --no-cache   # принудительная пересборка
```

PDF-отчёты (`m10-storage`) и acknowledged-статусы алертов (`m10-state`)
персистентны: переживают `restart` и `down`/`up`. Удаляются только при `down -v`.

### 2. Локальный запуск (Windows, для разработки)

**Требования:**
- **Python 3.12** (Python 3.14 несовместим с WeasyPrint и pandas)
- **GTK3 Runtime для Windows** — нужен WeasyPrint для PDF (см. ниже)
- **Node.js 20+** — только если планируете править фронт
- Интернет нужен только для OSM-тайлов на карте и мини-картах в PDF

#### Установить GTK3 Runtime

Скачайте инсталлятор и поставьте с дефолтами:
[GTK-for-Windows-Runtime-Environment-Installer / Releases](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)

Перезагрузите терминал. Проверка:
```powershell
python -c "import weasyprint; print(weasyprint.__version__)"
```
должно вывести `62.3` без ошибок.

#### Зависимости + старт

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
python run.py
```

`python run.py` запускает FastAPI на 8000, который отдаёт API + статический фронт
(собранный билд лежит в `frontend/out/`). Открывайте http://localhost:8000.

#### Свежие данные (опционально)

Если хотите пересобрать кеш с обновлёнными данными:
1. Скачайте `moskva_full.geojson` с [dtp-stat.ru](https://dtp-stat.ru), положите
   в `backend/data/raw/`.
2. Удалите `backend/data/processed/moscow_3y.parquet`.
3. Перезапустите — кеш пересоздастся (~1 минута).

---

## Что внутри

| URL | Что |
|---|---|
| http://localhost:8000/ | Фронтенд (Next.js 14, статический билд) |
| http://localhost:8000/api/m10/* | REST API (FastAPI) |
| http://localhost:8000/docs | Swagger UI (нажать «Try it out» → «Execute») |

### Фронтенд: 3 страницы

- **`/` Показатели** — 4 KPI карточки (Число ДТП, К. тяжести, Социальный риск,
  Частота на км сети) с дельтой к **АППГ** + контрольная карта Шухарта за
  выбранный год + интерактивная карта ДТП (тепловой слой + точки с popup) +
  таблица топ-5 очагов.
- **`/alerts` Предупреждения** — алерты за все 24 видимых месяца, фильтры по
  уровню/периоду/статусу, полнотекстовый поиск, кнопка «Отметить /
  вернуть в нерассмотренные», детальная панель с мини-графиком.
- **`/reports` Отчёты** — генерация PDF, скачивание, удаление. При
  «Сформировать» в таблице сразу появляется строка «Формируется» с
  прогресс-баром.

### Backend: 14 API endpoints под префиксом `/api/m10/`

`/health`, `/meta`, `/indicators`, `/indicators/calculate`, `/trend`,
`/alerts`, `/alerts/{id}/acknowledge`, `/alerts/{id}/unacknowledge`,
`/hotspots/top`, `/heatmap`, `/reports`, `/reports/generate`,
`/reports/{id}/download`, `DELETE /reports/{id}`.

### PDF-отчёт включает

1. Титульная страница (регион, период, дата формирования).
2. Сводка по 6 показателям (Число ДТП, Погибло, Ранено, К. тяжести,
   Социальный риск, Частота на км сети) с дельтой к АППГ.
3. Топ-5 очагов аварийности (таблица).
4. Выявленные предупреждения за период.
5. **Мини-карты участков** топ-5 очагов (5 PNG-фрагментов через OSM-tiles).

---

## Тесты

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

**62 теста**, все зелёные. Текущее покрытие — **78%**, отчёт автоматически
сохраняется в `backend/htmlcov/index.html`.

Стек:

- **pytest** + **pytest-asyncio** (auto-mode) — async-тесты без декораторов
- **httpx.AsyncClient + ASGITransport** — запросы к FastAPI без подъёма сокета
- **pytest-cov** — отчёт о покрытии (term-missing + html), подключён через
  `addopts` в `backend/pytest.ini`

WeasyPrint и OSM-tile-fetcher замоканы — GTK и интернет на этапе тестов не нужны.

---

## Разработка фронта (dev-режим)

Для правок фронта с hot-reload и React/Next DevTools:

```powershell
cd frontend
npm install        # один раз
cd ..
python run.py --dev
```

- http://localhost:3000 — фронт с hot-reload и DevTools
- http://localhost:8000 — API (uvicorn --reload)
- `Ctrl+C` останавливает оба процесса

После правок — пересоберите статику для production:

```powershell
cd frontend
npm run build      # обновляет frontend/out/
```

---

## Интеграция в общую среду ИГИС-БДД через Nginx

Контейнер слушает только порт 8000 без своего Nginx — пусть им рулит
общий reverse-proxy ИГИС-БДД. Пример блока для Nginx:

```nginx
upstream m10_backend {
    server m10:8000;        # имя из docker-compose или IP контейнера
}

# API + статический фронт по своему префиксу
location /api/m10/ {
    proxy_pass http://m10_backend;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Если хочется отдавать SPA под префиксом /m10/
location /m10/ {
    proxy_pass http://m10_backend/;
}
```

---

## Структура проекта

```
project-root/
├── README.md
├── run.py                       # точка входа (prod + --dev)
├── Dockerfile                   # multi-stage: node build → python runtime
├── docker-compose.yml           # сервис m10 на :8000 + volumes
├── .dockerignore
├── docs/
│   └── PROJECT_SPEC.md          # полная спецификация
├── frontend/                    # Next.js 14
│   ├── app/                     # /, /alerts, /reports
│   ├── components/              # UI: dashboard/, alerts/, reports/, period-picker, theme-toggle
│   ├── lib/api.ts               # типизированный async-клиент к backend
│   ├── next.config.mjs          # output='export'
│   └── out/                     # собранный статический фронт (в репо)
└── backend/
    ├── data/
    │   ├── raw/                 # сюда положить moskva_full.geojson (опционально)
    │   └── processed/
    │       └── moscow_3y.parquet  # в репо, 36 месяцев данных
    ├── storage/reports/         # сгенерированные PDF (gitignore)
    ├── app/
    │   ├── main.py              # FastAPI + StaticFiles mount + middleware
    │   ├── api/                 # 14 endpoints
    │   ├── core/                # формулы, контрольные карты, Nelson, periods
    │   ├── models/              # Pydantic схемы
    │   ├── services/            # singleton-сервисы (Data / Indicator / Alert / Hotspot / Heatmap / Report)
    │   └── reports/templates/   # Jinja2 PDF-шаблон + styles.css
    ├── tests/                   # 62 pytest теста
    └── pytest.ini               # asyncio_mode=auto + auto-coverage
```

---

## Решение типичных проблем

### `Fatal error in launcher: Unable to create process using ".venv\Scripts\python.exe"`
После переименования папки проекта `.venv` ломается. Пересоздать:
```powershell
cd backend
deactivate
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### `ERROR: порт 8000 уже занят`
Старый процесс держит порт:
```powershell
netstat -ano | findstr :8000
taskkill /F /PID <PID из строки LISTENING>
```

### `GLib-GIO-WARNING` в логе при работе с PDF
Безвредные сообщения от GIO о метаданных UWP-приложений Windows (Outlook,
PythonManager). На функциональность не влияют.

### Карта ДТП пустая или выглядит как мокап
Браузер закешировал старый HTML. **Hard refresh** — `Ctrl+F5`.

### Можно ли работать офлайн?
- Дашборд + API + PDF-сводка + алерты — **да**.
- Карта на странице «Показатели» (OSM-тайлы) — **нужен интернет**.
- Мини-карты участков в PDF — **нужен интернет** (OSM tile-сервер).
  Без интернета PDF всё равно сгенерируется, но вместо PNG будут
  текстовые координаты.

### Почему GTK3 нельзя через `pip install`?
`requirements.txt` — список Python-пакетов; GTK3 — системные DLL
(libpango, libcairo). Альтернативы (xhtml2pdf, pdfkit+wkhtmltopdf,
playwright+chromium) либо не поддерживают наш CSS, либо требуют другого
системного бинарника. В Docker эта проблема снята — GTK ставится через `apt`
внутри образа автоматически.

---

## Лицензия данных

- Данные ДТП: [dtp-stat.ru](https://dtp-stat.ru)
- Карты: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright)
