# Backend модуля M10 ИГИС-БДД

## Запуск

```
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

## Зависимости
- Python 3.12
- См. requirements.txt

## Данные
Если хотите пересобрать кеш с более свежими данными, скачайте
`moskva_full.geojson` с [dtp-stat.ru](https://dtp-stat.ru), положите в
`backend/data/raw/`, удалите `moscow_3y.parquet` и перезапустите — кеш пересоздастся.