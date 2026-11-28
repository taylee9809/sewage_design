"""워싱턴주 Orange Book(WA_ECY_CSWD_2023) — 원문 값을 정답지로. 공개 CSV로 DB 없이 돈다."""
import json
import math
from pathlib import Path

import pytest

from engine import criteria_db as db
from engine import csv_rows
from engine import plant as pl
from engine.generic import STANDARDS, Standard

ROOT = Path(__file__).parent.parent
WA = "WA_ECY_CSWD_2023"
P = 7845
GPDSF = 0.0407458


@pytest.fixture
def st(monkeypatch):
    monkeypatch.setattr(db, "load", lambda sid, dsn=None: csv_rows.rows_from_csv(sid))
    project = json.loads((ROOT / "criteria" / "projects" / "SYN01.json").read_text(encoding="utf-8"))
    return Standard(WA, project)


def test_registered_as_design_method_values_only():
    m = STANDARDS[WA]
    assert m["doc_role"] == "design_method" and m["redistributable"] == "values_only"


def test_public_csvs_carry_no_source_quotes():
    import csv
    for f in ("wa_sewer.csv", "wa_pump_sewer.csv", "wa_treatment_sewer.csv"):
        assert all(not r["quote_short"] for r in csv.DictReader((ROOT / "criteria" / f).open(encoding="utf-8"))), f


def test_peak_factor_figure_c1_1_with_floor_2_5(st):
    for pop in (500, 7845):
        x = math.sqrt(pop / 1000)
        assert st.peak_flow(pop) / st.peak_flow(pop, peak=False) == pytest.approx((18 + x) / (4 + x))
    assert st.peak_flow(100000) / st.peak_flow(100000, peak=False) == pytest.approx(2.5)  # C1-3.3.2 2.5 미만 불가


def test_per_capita_100_gpd_includes_infiltration(st):
    assert st.peak_flow(1000, peak=False) * 86400 * 1000 / 1000 == pytest.approx(378.5, abs=1)  # L/인/일 (100 gpd)


def test_primary_sized_by_table_t2_2_upper_limits(st):
    r = pl.plant_design(st, P)
    F, p = r["flows_m3d"], r["primary"]
    assert p["area_m2"] == pytest.approx(max(F["average"] / (1200 * GPDSF), F["peak_hourly"] / (3000 * GPDSF)), rel=1e-3)
    t = next(c for c in p["checks"] if c["item"] == "primary_detention_time")
    assert t["range"] == [None, 2.5] and t["ok"]  # T2-2.1.3 평균유량 2.5 h 이하
    assert r["primary"]["bod_removal"]["value"] == pytest.approx(0.30)  # T2-2.1.1 30~35% 하한


def test_aeration_held_on_max_week_flow(st):
    r = pl.plant_design(st, P)
    assert r["aeration"]["flow"] == "max_week"  # Table G2-1 이차처리 기준 반응조 = MWDF
    assert any("max_week" in h for h in r["aeration"]["held"])  # 산정 계수 없음


def test_secondary_peak_overflow_table_t3_2(st):
    r = pl.plant_design(st, P)
    s = r["secondary"]
    assert s["area_m2"] == pytest.approx(r["flows_m3d"]["peak_hourly"] / 48.9, rel=1e-3)


def test_sbr_values_present_for_later_sbr_rule(st):
    sbr = {x.param_key: x for x in st.plant_rows if x.condition.get("process") == "sbr"}
    assert sbr["sbr_basin_count_min"].value_min == 3
    assert (sbr["sbr_oxic_srt"].value_min, sbr["sbr_oxic_srt"].value_max) == (8, 15)
    assert sbr["asp_fm_ratio"].value_max == pytest.approx(0.10)
    assert sbr["asp_volumetric_bod_loading"].value_max == pytest.approx(0.24)
