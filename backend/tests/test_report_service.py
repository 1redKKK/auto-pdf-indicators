"""ReportService tests with WeasyPrint mocked.

Real PDF rendering needs GTK and is too slow for CI; we just verify the
template renders, the index updates, and files land where expected.
"""

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from app.services.data_service import data_service
from app.services.indicator_service import indicator_service
from app.services.alert_service import alert_service
from app.services.report_service import ReportService


FAKE_PDF = b"%PDF-1.4 fake content for tests\n%%EOF"


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
def isolated_storage(tmp_path, monkeypatch):
    """Settings is frozen, so isolate by chdir-ing into a tmp dir.

    Settings paths are relative (e.g. 'storage/reports', 'app/reports/index.json'),
    so they resolve under the current working dir.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app" / "reports").mkdir(parents=True, exist_ok=True)
    yield tmp_path


@pytest.fixture
def services_ready(monkeypatch, synthetic_df):
    from app.services import data_service as ds_mod
    from app.services import report_service as rs_mod
    monkeypatch.setattr(ds_mod.data_service, "get_df", lambda: synthetic_df)
    monkeypatch.setattr(ds_mod.data_service, "df", synthetic_df, raising=False)
    # Skip OSM tile fetching in tests — keeps the suite fast and offline-safe.
    monkeypatch.setattr(rs_mod, "_render_hotspot_snippet", lambda lat, lon: None)
    indicator_service.recompute()
    alert_service.recompute()


def test_generate_creates_pdf_and_index(monkeypatch, isolated_storage, services_ready):
    from app.services import report_service as rs_mod
    monkeypatch.setattr(rs_mod, "_render_pdf", lambda html, base_url: FAKE_PDF)

    svc = ReportService()
    svc._reports = []
    svc._loaded = True   # skip loading from disk

    item = svc.generate(region="moscow", period="2025-12", periodicity="month")

    assert item.id == "rpt_001"
    assert item.file_name == "BDD_Moscow_M_Dec_2025.pdf"
    assert item.region == "moscow"
    assert item.region_label == "Москва"
    assert item.period_label == "Декабрь 2025"
    assert item.size_bytes == len(FAKE_PDF)

    # PDF on disk (under settings.REPORTS_DIR, relative to cwd)
    from app.config.settings import settings as s
    pdf_path = Path(s.REPORTS_DIR) / "rpt_001.pdf"
    assert pdf_path.exists()
    assert pdf_path.read_bytes() == FAKE_PDF

    # Index on disk
    index_path = Path(s.REPORTS_INDEX_PATH)
    assert index_path.exists()
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["id"] == "rpt_001"


def test_filename_for_quarter_and_year(monkeypatch, isolated_storage, services_ready):
    from app.services import report_service as rs_mod
    monkeypatch.setattr(rs_mod, "_render_pdf", lambda html, base_url: FAKE_PDF)

    svc = ReportService()
    svc._reports = []
    svc._loaded = True

    q = svc.generate(region="moscow", period="2025-09", periodicity="quarter")
    assert q.file_name == "BDD_Moscow_Q_Sep_2025.pdf"
    assert q.period_label == "Июль 2025 — Сентябрь 2025"

    y = svc.generate(region="moscow", period="2025-12", periodicity="year")
    assert y.file_name == "BDD_Moscow_Y_Dec_2025.pdf"
    assert y.period_label == "Январь 2025 — Декабрь 2025"


def test_unknown_region_raises(isolated_storage, services_ready):
    svc = ReportService()
    svc._reports = []
    svc._loaded = True
    with pytest.raises(ValueError):
        svc.generate(region="spb", period="2025-12", periodicity="month")


def test_get_path_returns_file(monkeypatch, isolated_storage, services_ready):
    from app.services import report_service as rs_mod
    monkeypatch.setattr(rs_mod, "_render_pdf", lambda html, base_url: FAKE_PDF)
    svc = ReportService()
    svc._reports = []
    svc._loaded = True

    item = svc.generate(region="moscow", period="2025-12", periodicity="month")
    path = svc.get_path(item.id)
    assert path.endswith("rpt_001.pdf")
    assert os.path.exists(path)


def test_get_path_unknown_raises(isolated_storage):
    svc = ReportService()
    svc._reports = []
    svc._loaded = True
    with pytest.raises(KeyError):
        svc.get_path("nonexistent")


def test_id_does_not_collide_after_delete(monkeypatch, isolated_storage, services_ready):
    """Regression: id used to be `rpt_{len+1}` which collided after deletion."""
    from app.services import report_service as rs_mod
    monkeypatch.setattr(rs_mod, "_render_pdf", lambda html, base_url: FAKE_PDF)

    svc = ReportService()
    svc._reports = []
    svc._loaded = True

    a = svc.generate(region="moscow", period="2025-12", periodicity="month")
    b = svc.generate(region="moscow", period="2025-11", periodicity="month")
    c = svc.generate(region="moscow", period="2025-10", periodicity="month")
    assert a.id == "rpt_001"
    assert b.id == "rpt_002"
    assert c.id == "rpt_003"

    # Удалить средний — раньше следующая генерация переиспользовала бы rpt_003.
    svc.delete("rpt_002")
    d = svc.generate(region="moscow", period="2025-09", periodicity="month")
    assert d.id == "rpt_004"

    ids = [r.id for r in svc.list_reports()]
    assert len(ids) == len(set(ids)), "ids must remain unique"
