"""End-to-end API tests через async httpx.AsyncClient + ASGITransport.

- pytest-asyncio (auto-mode) — поддержка async test-функций;
- httpx.AsyncClient + ASGITransport — отправляет запросы напрямую в FastAPI app
  без поднятия реального сокета, что нужно для текста ВКР § «Тестирование»;
- lifespan приложения запускается через app.router.lifespan_context, что
  заставляет indicator/alert services инициализироваться на синтетике;
- Data layer и WeasyPrint замоканы — GTK и большой geojson не нужны.
"""

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def synthetic_df():
    rows = []
    for year in [2023, 2024, 2025]:
        for month in range(1, 13):
            for i in range(100):
                rows.append({
                    "crash_id": f"{year}-{month:02d}-{i}",
                    "datetime": pd.Timestamp(year=year, month=month, day=15),
                    "year": year,
                    "month": month,
                    "lat": 55.75,
                    "lon": 37.62,
                    "dead_count": 1 if i < 5 else 0,
                    "injured_count": 1 if i < 50 else 0,
                    "severity": "minor",
                    "severity_raw": "Лёгкий",
                    "district": "Центр",
                    "crash_type": "столкновение",
                    "road_condition": None,
                    "address": "Main Street",
                    "year_month": f"{year}-{month:02d}",
                })
    return pd.DataFrame(rows)


@pytest.fixture
async def client(monkeypatch, tmp_path, synthetic_df):
    """Async FastAPI client with mocked data layer + isolated storage."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app" / "reports").mkdir(parents=True, exist_ok=True)

    from app.services import data_service as ds_mod
    monkeypatch.setattr(ds_mod.data_service, "df", synthetic_df, raising=False)
    monkeypatch.setattr(ds_mod.data_service, "loaded_at", pd.Timestamp.now(), raising=False)
    monkeypatch.setattr(ds_mod.data_service, "load", lambda: None)
    monkeypatch.setattr(ds_mod.data_service, "get_df", lambda: synthetic_df)

    # Reset alert/report singletons, чтобы изолированные прогоны не делили state.
    from app.services.alert_service import alert_service
    from app.services.report_service import ReportService
    alert_service._alerts = []
    alert_service._ack_state = {}
    alert_service._loaded_state = True
    ReportService._instance = None

    # Mock WeasyPrint render — без GTK.
    from app.services import report_service as rs_mod
    monkeypatch.setattr(rs_mod, "_render_pdf", lambda html, base_url: b"%PDF-1.4 test\n%%EOF")

    from app.main import app

    transport = ASGITransport(app=app)
    # lifespan_context запускает наш @asynccontextmanager lifespan: load() →
    # indicator_service.recompute() → alert_service.recompute() с уже
    # подменёнными данными.
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# ----- system -----

async def test_health(client):
    r = await client.get("/api/m10/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_meta(client):
    r = await client.get("/api/m10/meta")
    assert r.status_code == 200
    body = r.json()
    assert "period" in body
    assert "available_periods" in body
    assert body["period"]["baseline_months"] == 12
    assert len(body["available_periods"]) == 24


# ----- indicators -----

async def test_indicators_default(client):
    r = await client.get("/api/m10/indicators")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "Москва"
    codes = [c["code"] for c in body["cards"]]
    assert codes == ["accidents", "severity", "social_risk", "network_freq"]


async def test_indicators_with_period(client):
    r = await client.get("/api/m10/indicators?period=2025-12&periodicity=month")
    assert r.status_code == 200
    body = r.json()
    assert body["period"]["report_start"] == "2025-12-01"
    assert body["period"]["report_end"] == "2026-01-01"


async def test_indicators_calculate_post(client):
    r = await client.post("/api/m10/indicators/calculate")
    assert r.status_code == 200
    assert len(r.json()["cards"]) == 4


# ----- trend -----

async def test_trend_accidents(client):
    r = await client.get("/api/m10/trend?indicator=accidents")
    assert r.status_code == 200
    body = r.json()
    assert body["indicator"] == "accidents"
    assert body["chart_type"] == "c-chart"
    assert body["baseline_months"] == 12
    assert "ucl" in body and "cl" in body and "lcl" in body


async def test_trend_unknown_indicator_400(client):
    r = await client.get("/api/m10/trend?indicator=nonexistent")
    assert r.status_code == 400


# ----- alerts -----

async def test_alerts_list(client):
    r = await client.get("/api/m10/alerts")
    assert r.status_code == 200
    body = r.json()
    assert "total" in body
    assert "alerts" in body


async def test_alerts_filter_by_level(client):
    r = await client.get("/api/m10/alerts?level=critical")
    assert r.status_code == 200
    for a in r.json()["alerts"]:
        assert a["level"] == "critical"


async def test_alerts_acknowledge_404(client):
    r = await client.patch("/api/m10/alerts/alrt_999/acknowledge")
    assert r.status_code == 404


# ----- hotspots -----

async def test_hotspots_default(client):
    r = await client.get("/api/m10/hotspots/top")
    assert r.status_code == 200
    body = r.json()
    assert "hotspots" in body
    assert "period_label" in body


async def test_hotspots_with_period(client):
    r = await client.get("/api/m10/hotspots/top?period=2025-12&periodicity=month&limit=3")
    assert r.status_code == 200
    body = r.json()
    assert len(body["hotspots"]) <= 3
    assert body["period_months"] == 1


# ----- heatmap -----

async def test_heatmap_default(client):
    r = await client.get("/api/m10/heatmap")
    assert r.status_code == 200
    body = r.json()
    assert "total" in body
    assert "points" in body
    assert "period_label" in body
    # Каждая точка имеет lat/lon/severity и расширенные поля для popup
    if body["points"]:
        p = body["points"][0]
        assert {"lat", "lon", "severity", "datetime", "dead", "injured"} <= set(p)


async def test_heatmap_with_period_and_limit(client):
    r = await client.get("/api/m10/heatmap?period=2025-12&periodicity=month&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["period_months"] == 1
    assert len(body["points"]) <= 10


async def test_heatmap_invalid_periodicity_400(client):
    r = await client.get("/api/m10/heatmap?period=2025-12&periodicity=decade")
    assert r.status_code in (400, 422)   # FastAPI validation: 422; ValueError из service: 400


# ----- reports -----

async def test_reports_full_flow(client):
    # 1. Empty list
    r = await client.get("/api/m10/reports")
    assert r.status_code == 200
    assert r.json()["total"] == 0

    # 2. Generate
    r = await client.post(
        "/api/m10/reports/generate",
        json={"region": "moscow", "period": "2025-12", "periodicity": "month"},
    )
    assert r.status_code == 201
    item = r.json()
    assert item["file_name"] == "BDD_Moscow_M_Dec_2025.pdf"
    rid = item["id"]

    # 3. List has 1
    r = await client.get("/api/m10/reports")
    assert r.json()["total"] == 1

    # 4. Download
    r = await client.get(f"/api/m10/reports/{rid}/download")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "BDD_Moscow_M_Dec_2025.pdf" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")

    # 5. Unknown id → 404
    r = await client.get("/api/m10/reports/rpt_999/download")
    assert r.status_code == 404


async def test_reports_unknown_region_400(client):
    r = await client.post(
        "/api/m10/reports/generate",
        json={"region": "spb", "period": "2025-12", "periodicity": "month"},
    )
    assert r.status_code == 400
