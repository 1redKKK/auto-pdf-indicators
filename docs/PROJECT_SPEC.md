# PROJECT_SPEC.md

## Модуль M10 «Безопасность дорожного движения» (ИГИС-БДД)

Спецификация backend + frontend модуля M10 в составе информационно-аналитической системы ИГИС.

---

## 1. Контекст проекта

### 1.1. Что это
Веб-приложение для статистического мониторинга безопасности дорожного движения по г. Москва:
- KPI-дашборд (4 показателя на экране, 6 в PDF),
- контрольные карты Шухарта (c-карта, u-карта, i-карта),
- автоматическая генерация предупреждений (правила Нельсона + warning_zone) на всём видимом диапазоне,
- PDF-отчёты по периодам (месяц / квартал / год) с мини-картами топ-5 очагов,
- топ-5 очагов аварийности (DBSCAN-кластеризация) с реальной картой OSM,
- интерактивная карта ДТП с тепловой картой и кликабельными точками (popup),
- fullscreen-режим карты.

Backend на FastAPI (Python 3.12) и frontend на Next.js 14 объединены в одно
приложение: статически собранный фронт (`frontend/out/`) отдаётся через
FastAPI на том же порту, что и API. Запуск одной командой — `python run.py`
для локального dev/prod, либо `docker compose up -d` для контейнерной поставки.

### 1.2. Регион
Сервис работает с данными **только по г. Москва**. Параметры региона
(население, протяжённость УДС, количество ТС) — статичные константы в
`backend/app/config/moscow.py`.

### 1.3. Период данных
Загружается **36 месяцев**, заканчивающихся на последнем полном
календарном году в данных (по умолчанию **Янв 2023 — Дек 2025**):

- **Скрытый pool** (Янв–Дек 2023) — нужен для расчёта baseline АППГ
  (Аналогичный Период Прошлого Года) для самых ранних видимых месяцев.
  В UI не показывается.
- **Видимый диапазон** (Янв 2024 — Дек 2025) — 24 месяца:
  - **Базовый период** (Янв–Дек 2024) — расчёт UCL/CL/LCL;
  - **Отчётный период** (Янв–Дек 2025) — точки на графиках по умолчанию.

Если в источнике данных только частичный месяц на конце (например, Янв 2026
с днями 1–15) — он отбрасывается при `_crop_to_complete_window`, чтобы окно
всегда оканчивалось декабрём.

---

## 2. Технологический стек

### 2.1. Backend
- **Python 3.12** (Python 3.14 несовместим с WeasyPrint и numpy/pandas)
- **FastAPI 0.115** + **Uvicorn 0.32** + **httpx 0.27**
- **Pydantic v2** — валидация и сериализация
- **pandas 2.2** + **numpy 2.1** + **pyarrow 17** (parquet-кеш)
- **WeasyPrint 62.3** + **pydyf 0.10.0** — генерация PDF
- **Jinja2 3.1** — HTML-шаблоны для PDF
- **staticmap 0.5.7** + **Pillow** — мини-карты участков в PDF (OSM-tiles)
- **ijson 3.3** — стриминговое чтение GeoJSON

### 2.2. Frontend
- **Next.js 14** (app router, static export `output: 'export'`)
- **TypeScript** + **Tailwind CSS v4**
- **shadcn/ui** — UI-компоненты
- **Recharts** — графики
- **next-themes** — переключатель light/dark
- **Leaflet 1.9** + **leaflet.heat** — карта + тепловой слой
- Точки на карте рендерятся через **SVG renderer** (`preferCanvas: false`) —
  это даёт нативную кликабельность без overlay-канваса.

### 2.3. Запуск

**Docker (production-ready):**
```powershell
docker compose up -d
```
→ http://localhost:8000. Multi-stage образ (Node build → Python runtime),
GTK + шрифты внутри. Парквет с данными в репо — никаких ручных шагов.

**Локально, prod-режим (single-command):**
```powershell
pip install -r backend/requirements.txt
python run.py
```
→ http://localhost:8000

**Локально, dev-режим (hot-reload и React/Next DevTools):**
```powershell
cd frontend && npm install
cd ..
python run.py --dev
```
→ http://localhost:3000 (фронт с HMR), http://localhost:8000 (API)

Подробные требования к локальному запуску (GTK3 Runtime для Windows,
версия Python и т.п.) — в [`README.md`](../README.md).

### 2.4. Совместимость и ограничения
- Аутентификация: **отсутствует** (открытые эндпоинты — авторизация
  планируется на стороне общего reverse-proxy ИГИС-БДД).
- Регион: только Москва.
- Интернет: нужен для OSM-тайлов на странице карты и для генерации PDF
  с мини-картами участков. Без интернета PDF всё равно соберётся, но
  вместо PNG-фрагментов карт будут текстовые координаты.

---

## 3. Структура проекта

```
project-root/
├── README.md
├── run.py                         # точка входа (prod + --dev)
├── Dockerfile                     # multi-stage: node build → python runtime
├── docker-compose.yml             # сервис m10 на :8000 + volumes
├── .dockerignore
├── docs/
│   └── PROJECT_SPEC.md            # этот файл
├── frontend/                      # Next.js 14
│   ├── app/                       # /, /alerts, /reports
│   ├── components/
│   │   ├── dashboard/             # KPI, control-chart, map (CrashMap)
│   │   ├── alerts/                # list + detail panel
│   │   ├── reports/               # form + table
│   │   ├── period-picker.tsx
│   │   └── theme-toggle.tsx
│   ├── lib/api.ts                 # типизированный async-клиент
│   ├── next.config.mjs            # output='export'
│   └── out/                       # собранный статический фронт (коммитится)
└── backend/
    ├── requirements.txt
    ├── pytest.ini                 # asyncio_mode=auto + auto-coverage
    ├── data/
    │   ├── raw/moskva_full.geojson    # gitignore, ~197 МБ (опционально)
    │   └── processed/moscow_3y.parquet # ← в репо, 1.4 МБ, 36 мес
    ├── storage/reports/                # gitignore, сгенерированные PDF
    ├── htmlcov/                        # gitignore, HTML coverage report
    ├── tests/                          # 62 pytest теста
    └── app/
        ├── main.py                # FastAPI + StaticFiles mount + middleware
        ├── config/
        │   ├── settings.py
        │   └── moscow.py
        ├── core/
        │   ├── data_loader.py     # стрим GeoJSON → DataFrame → parquet
        │   ├── indicators.py      # формулы 2.1–2.4 ВКР
        │   ├── shewhart.py        # c-карта, u-карта, i-карта
        │   ├── nelson.py          # правила Нельсона 2/3/4
        │   ├── periods.py         # baseline / report диапазоны
        │   └── period_window.py   # (period, periodicity) → окно
        ├── api/                   # роутеры FastAPI (14 endpoints)
        ├── models/                # Pydantic схемы
        ├── services/              # singleton-сервисы (Data/Indicator/Alert/
        │                          #   Hotspot/Heatmap/Report)
        └── reports/
            ├── templates/         # monthly.html + styles.css (Jinja2)
            ├── index.json         # gitignore, реестр PDF
            └── alerts_state.json  # gitignore, статусы acknowledged
```

---

## 4. Параметры региона (Москва)

```python
MOSCOW_PROFILE = {
    "code": "moscow",
    "name": "г. Москва",
    "population": 13_149_803,
    "network_length_km": 3620.0,
    "vehicles_count": 4_080_000,
    "annual_mileage_vehkm": 6.5e10,
    "bbox": {
        "lat_min": 55.142, "lat_max": 56.021,
        "lon_min": 36.803, "lon_max": 37.967,
    },
}
```

---

## 5. Формулы и алгоритмы (соответствуют ВКР гл. 2)

### 5.1. KPI (формулы 2.1–2.4)
```
K_L = N_дтп / L_сети                       (2.1) — частота на км сети
K_p = N_дтп / P × 10⁸                      (2.2) — на единицу пробега (только в PDF)
K_T = N_пог / (N_пог + N_ран)              (2.3) — коэф. тяжести (×100 в UI)
R_S = N_пог / P_нас × 10⁵                  (2.4) — социальный риск
```

**Семантика для произвольного окна:**
- `value` = сумма за выбранное окно (period total)
- `baseline` = АППГ — то же окно, сдвинутое ровно на −12 месяцев
  (Дек 2025 vs Дек 2024, Q4 2025 vs Q4 2024, 2025 vs 2024)
- `delta_pct = (value − baseline) / baseline × 100`

### 5.2. Контрольные карты Шухарта
**C-карта** (формулы 2.5–2.7) — для абсолютных счётчиков:
```
CL = c̄, UCL = c̄ + 3√c̄, LCL = max(0, c̄ − 3√c̄)
```
**U-карта** (формулы 2.8–2.11) — для нормированных показателей:
```
ū = Σx_i / Σn_i, UCL_i = ū + 3√(ū / n_i), LCL_i = max(0, ū − 3√(ū / n_i))
```
**I-карта** — для индивидуальных значений (severity, social_risk).

Базовый период — первые 12 месяцев видимого диапазона (Янв–Дек 2024 при
дефолтных данных). UCL/CL/LCL рассчитываются один раз и применяются ко
всем точкам.

### 5.3. Алгоритм генерации алертов (ВКР 2.2.3, рис. 2.3)
Для каждой точки видимого диапазона (24 мес):
1. `x > UCL` → `ucl_exceeded` (CRITICAL, тип A или C)
2. `CL+2σ < x ≤ UCL` → `warning_zone` (WARNING, тип A или C)
3. `x < LCL` → `lcl_exceeded` (INFO, тип A или C)
4. Иначе — проверка правил Нельсона на полном ряду (включая hidden pool):
   - `nelson_rule_2`: 9 точек подряд по одну сторону CL → WARNING тип B
   - `nelson_rule_3`: 6 монотонных точек → WARNING тип B
   - `nelson_rule_4`: 14 чередующихся точек → WARNING тип B

**Тип-маппинг:**
- `accidents`, `network_freq`, `social_risk` → A (аномалия уровня)
- `severity` → C (тяжесть)
- любое срабатывание Нельсона → B (тренд)

Алерты сортируются по дате (newest first); уровень виден бейджем в UI.

### 5.4. Очаги аварийности (hotspots)
DBSCAN-кластеризация координат ДТП за выбранное окно с радиусом ~150 м.
Для каждого кластера считается:
- `accidents` — число ДТП
- `dead` / `injured` — суммарные потери
- `severity` — коэффициент тяжести по формуле 2.3
- `dominant_type` — самый частый `crash_type` в кластере
- `frequency_per_km` — частота по длине УДС города

Топ-N сортируется по числу ДТП (по умолчанию `limit=5`).

---

## 6. Источник данных

### 6.1. Входной файл
`backend/data/raw/moskva_full.geojson` — выгрузка с dtp-stat.ru. ~197 МБ.
В Git **не коммитится**. Уже скачанный кеш `moscow_3y.parquet` (1.4 МБ)
коммитится.

### 6.2. Конвейер обработки
1. Стримово (через `ijson`) читаем GeoJSON.
2. Фильтруем по `parent_region == "Москва"` и периоду
   `[max_date − 42 месяца, max_date]`.
3. Преобразуем в DataFrame, сохраняем `data/processed/moscow_3y.parquet`.
4. **`_crop_to_complete_window`**: обрезаем до ровно 36 месяцев,
   заканчивающихся на последнем полном календарном году. Partial
   trailing year (например, январь 2026 без целого года) отбрасывается.

---

## 7. API — 14 эндпоинтов под префиксом `/api/m10`

### 7.1. Системные
| Метод | URL | Описание |
|---|---|---|
| GET | `/health` | Проверка живости |
| GET | `/meta` | Период (baseline/report) + `available_periods` (24 видимых месяца, отсортированы по убыванию) |

### 7.2. KPI
| Метод | URL | Описание |
|---|---|---|
| GET | `/indicators?period=&periodicity=` | 4 KPI. Без параметров — за весь report. С параметрами — за окно, baseline = АППГ |
| POST | `/indicators/calculate` | Принудительный пересчёт |

### 7.3. Тренд
| Метод | URL | Описание |
|---|---|---|
| GET | `/trend?indicator=&end_period=` | Точки графика. С `end_period=YYYY-12` — 12 точек выбранного календарного года. UCL/CL/LCL фиксированные (по baseline) |

### 7.4. Алерты
| Метод | URL | Описание |
|---|---|---|
| GET | `/alerts?status=&level=&period=&q=&limit=` | Список, sorted: newest first by date. `q` — поиск по тексту и региону |
| PATCH | `/alerts/{id}/acknowledge` | Пометить как рассмотренное |
| PATCH | `/alerts/{id}/unacknowledge` | Вернуть в нерассмотренные |

### 7.5. Очаги
| Метод | URL | Описание |
|---|---|---|
| GET | `/hotspots/top?limit=&period=&periodicity=` | Топ-N очагов за окно (с `dominant_type`, `frequency_per_km`) |

### 7.6. Карта
| Метод | URL | Описание |
|---|---|---|
| GET | `/heatmap?period=&periodicity=&limit=` | Точки ДТП с расширенными полями для popup (см. ниже), sample до 5000 |

`HeatmapPoint` содержит: `lat`, `lon`, `severity`, `datetime`, `address`,
`district`, `crash_type`, `dead`, `injured` — этих полей достаточно
фронту, чтобы открыть полнотекстовый popup по клику без дополнительных
запросов.

### 7.7. Отчёты
| Метод | URL | Описание |
|---|---|---|
| GET | `/reports` | Список ранее сгенерированных PDF |
| POST | `/reports/generate` | Body: `{region, period, periodicity}`, HTTP 201 |
| GET | `/reports/{id}/download` | Streams PDF, имя `BDD_Moscow_*.pdf` |
| DELETE | `/reports/{id}` | Удалить файл и запись в реестре, HTTP 204 |

### 7.8. Прочее
- `GET /favicon.ico` → 204 (заглушка, чтобы не было 404 в access-log)
- `GET /_vercel/insights/{rest}` → 204 (заглушка для @vercel/analytics)
- Middleware `next_prefetch_rewrite` переписывает пути prefetcher'а Next.js 16
  (`/X/__next.X.__PAGE__.txt` → `/X/__next.X/__PAGE__.txt`) до того, как
  StaticFiles вернёт 404.

### 7.9. Соглашение об ошибках
- `200`/`201`/`204` — успех
- `400` — некорректные параметры
- `404` — не найдено
- `503` — сервис не готов (кеш ещё не построен)
- Тело ошибки: `{"detail": "..."}` (стандарт FastAPI)

---

## 8. PDF-отчёт

### 8.1. Шаблон
`backend/app/reports/templates/monthly.html` (Jinja2) +
`styles.css` (CSS для WeasyPrint, A4 portrait, нумерация страниц).

### 8.2. Состав
1. **Титульная страница** (регион, период, дата формирования)
2. **Сводка по 6 показателям** с дельтой к АППГ:
   - Число ДТП, шт.
   - Погибло, чел.
   - Ранено, чел.
   - Коэффициент тяжести последствий
   - Социальный риск (на 100 тыс.)
   - Частота на км сети, ДТП/км
3. **Топ-5 очагов аварийности** (таблица)
4. **Выявленные предупреждения** за период
5. **Карты участков топ-5 очагов** (на отдельной странице): 5 PNG-фрагментов
   карты OSM 500×300 пикселей с красной точкой на координатах очага.
   Если интернет недоступен — fallback на текст с координатами.

### 8.3. Имена файлов
- Месяц: `BDD_Moscow_M_<EnMonAbbr>_<YYYY>.pdf` (`BDD_Moscow_M_Dec_2025.pdf`)
- Квартал: `BDD_Moscow_Q_<EnMonAbbr>_<YYYY>.pdf` (anchor = последний месяц)
- Год: `BDD_Moscow_Y_<EnMonAbbr>_<YYYY>.pdf` (anchor = декабрь)

### 8.4. Хранение
- PDF: `backend/storage/reports/{id}.pdf`
- Реестр: `backend/app/reports/index.json` (с дедупликацией по id)

В Docker оба пути смонтированы как named-volumes (`m10-storage`,
`m10-state`) — данные переживают `docker compose down`.

---

## 9. Frontend

### 9.1. Страницы
- **`/` Показатели** — фильтры period/periodicity, 4 KPI с базой АППГ,
  карта (heatmap + scatter), контрольная карта по году, таблица топ-5
  очагов.
- **`/alerts` Предупреждения** — фильтры по уровню/периоду/статусу,
  полнотекстовый поиск (по `description` и `region`), acknowledge /
  unacknowledge, детальная панель с мини-графиком.
- **`/reports` Отчёты** — форма генерации, список, скачивание, удаление.
  После «Сформировать» в таблице сразу появляется строка «Формируется»
  с прогресс-баром (optimistic UI), пока POST не вернёт реальный id.

### 9.2. Особенности UX
- Тема light/dark — переключатель в шапке sidebar (next-themes).
- Регион фиксирован = «Москва».
- Period dropdown адаптируется к periodicity (только полные периоды):
  - `month` → «Январь 2024»
  - `quarter` → «1 кв. 2024»
  - `year` → «2024»
  - Сортировка: **newest first** (самый свежий период сверху).
- Trend chart показывает 12 точек выбранного календарного года.
- Карта: heatmap-слой + scatter-точки (оба ON по умолчанию). Точки
  рендерятся SVG-рендерером (`preferCanvas: false`), что даёт нативную
  кликабельность. Fullscreen toggle (Esc сворачивает).
- **Popup ДТП-точки**: дата, адрес, район, тип ДТП, погибло, ранено,
  коэффициент тяжести, статус severity.
- **Popup очага**: «№ X из 5», координаты, число ДТП, погибло, ранено,
  доминирующий тип ДТП, период, частота на км сети.
- Алерты сортируются по дате (newest first), есть кнопка «Вернуть в
  нерассмотренные» в детальной панели.

### 9.3. API_BASE
По умолчанию `/api/m10` (relative — same-origin). Для dev-режима
оверрайд через `frontend/.env.local`:
`NEXT_PUBLIC_API_BASE=http://localhost:8000/api/m10`.

---

## 10. Тесты

`backend/tests/` — **62 pytest теста**, текущее покрытие — **78%**:

| Файл | Тестов |
|---|---|
| `test_indicators_and_shewhart.py` | 15 |
| `test_indicator_service.py` | 3 |
| `test_periods.py` | 3 |
| `test_period_window.py` | 5 |
| `test_nelson.py` | 13 |
| `test_report_service.py` | 6 |
| `test_api.py` | 17 (async-клиент на все API endpoints) |

### 10.1. Стек
- **pytest** + **pytest-asyncio** (`asyncio_mode = auto`) — любая
  async-функция автоматически считается asyncio-тестом, без декоратора
  `@pytest.mark.asyncio` на каждом.
- **httpx.AsyncClient** + **ASGITransport** — запросы напрямую в FastAPI app
  без поднятия реального сокета. Lifespan приложения запускается через
  `app.router.lifespan_context`, что прогревает singleton-сервисы
  (Data / Indicator / Alert) на синтетическом DataFrame.
- **pytest-cov** — отчёт о покрытии (term-missing + html), подключён
  через `addopts` в `backend/pytest.ini`. HTML-отчёт пишется в
  `backend/htmlcov/index.html`.

### 10.2. Мокинг внешних зависимостей
- `data_service.df` подменяется на синтетический DataFrame (3 года, 100
  ДТП/мес, 5 fatal, 50 injured).
- `report_service._render_pdf` замоканный — возвращает `b"%PDF-1.4 test"`.
  GTK не требуется на этапе тестов.
- `_render_hotspot_snippet` (OSM-tile fetcher) тоже замоканный — интернет
  не нужен.

### 10.3. Команда запуска
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```
Без дополнительных флагов: покрытие, term-missing и HTML-отчёт собираются
автоматически.

---

## 11. Docker

### 11.1. Архитектура образа
Multi-stage `Dockerfile`:
1. **Stage 1 (node:20-alpine)**: `npm ci` + `npm run build` →
   `frontend/out/` (статический экспорт).
2. **Stage 2 (python:3.12-slim-bookworm)**: `apt install libpango-1.0-0
   libpangoft2-1.0-0 libcairo2 libffi-dev shared-mime-info fonts-dejavu`
   + `pip install -r requirements.txt`. Копируется backend и `out/`
   из первой стадии. CMD — `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### 11.2. docker-compose
```yaml
services:
  m10:
    build: .
    ports: ["8000:8000"]
    volumes:
      - m10-storage:/app/backend/storage    # PDF
      - m10-state:/app/backend/app/reports  # index.json + alerts_state.json
volumes:
  m10-storage:
  m10-state:
```

### 11.3. Интеграция в общую среду ИГИС-БДД через Nginx
Контейнер слушает только порт 8000 без своего Nginx — пусть им рулит
общий reverse-proxy ИГИС-БДД. Пример блока:
```nginx
upstream m10_backend { server m10:8000; }

location /api/m10/ {
    proxy_pass http://m10_backend;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /m10/ {
    proxy_pass http://m10_backend/;
}
```

---

## 12. Что НЕ делаем (вне scope)

- Аутентификация / JWT / роли пользователей (планируется на стороне
  общего reverse-proxy ИГИС-БДД).
- База данных (PostgreSQL, SQLite) — всё in-memory + JSON.
- Другие регионы кроме Москвы.
- WebSocket / real-time обновления.
- Email/Telegram-рассылка алертов.
- Хостинг своих OSM-tiles (используем публичные tile.openstreetmap.org).

---

## 13. Соответствие ВКР

| Глава | Реализация |
|---|---|
| 1.4.1 FR-01–04 (KPI) | `app/services/indicator_service.py`, `frontend/app/page.tsx` |
| 1.4.1 FR-05–08 (предупреждения) | `app/core/nelson.py`, `app/services/alert_service.py` |
| 1.4.1 FR-09 (очаги) | `app/services/hotspot_service.py` |
| 1.4.1 FR-10–11 (PDF) | `app/services/report_service.py` |
| 2.1.4 (14 API эндпоинтов) | `app/api/*.py` |
| 2.2.1 (формулы 2.1–2.4) | `app/core/indicators.py` |
| 2.2.2 (формулы 2.5–2.11) | `app/core/shewhart.py` |
| 2.2.3 (алгоритм алертов, рис. 2.3) | `app/services/alert_service.py` |
| 3.1 (архитектура) | вся структура `backend/app/` + `frontend/` |
| 3.2 (API контракт) | `tests/test_api.py` (17 async-кейсов через httpx.AsyncClient) |
| 3.3 (фронтенд) | `frontend/` (Next.js 14 + shadcn/ui + Recharts + Leaflet) |
| 3.4 (PDF) | `app/reports/templates/` (Jinja2 + WeasyPrint + staticmap) |
| 3.5 (тестирование) | `tests/` (62 теста, 78% покрытие, pytest + pytest-asyncio + httpx.AsyncClient + pytest-cov) |
| 3.6 (контейнеризация) | `Dockerfile`, `docker-compose.yml`, `.dockerignore` |
