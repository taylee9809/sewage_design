"""하수처리장(표준활성슬러지법) 설계 — 원문 표 값을 정답지로. 기준값은 공개 CSV에서 읽어 DB 없이 돈다."""
import json
from pathlib import Path

import pytest

from engine import criteria_db as db
from engine import csv_rows
from engine import plant as pl
from engine.generic import Standard

ROOT = Path(__file__).parent.parent
KDS, TSS, IN, CO = "KDS_61_40_00_20251001", "TSS_WW_2026", "CPHEEO_SEW_2013", "CO_RAS_0330_2017_COMP2021"
P = 7845  # SYN01 계획인구 합


@pytest.fixture
def std(monkeypatch):
    monkeypatch.setattr(db, "load", lambda sid, dsn=None: csv_rows.rows_from_csv(sid))
    project = json.loads((ROOT / "criteria" / "projects" / "SYN01.json").read_text(encoding="utf-8"))

    def make(sid, **extra):
        p = json.loads(json.dumps(project))
        p["standards"][sid].update({k: {"value": v} for k, v in extra.items()})
        return Standard(sid, p)
    return make


def check(part, item, flow=None):
    return next(c for c in part["checks"] if c["item"] == item and (flow is None or c["flow"] == flow))


def test_kds_flows_follow_1_7_2(std):
    st = std(KDS)
    F, _ = pl.flows(st, P)
    assert F["max_daily"] == pytest.approx(P * 0.300 * 1.2)  # 1인1일최대 300 L(사업) × 지하수 20%(상한)
    assert F["average"] == pytest.approx(F["max_daily"] * 0.80)  # 1.7.2 (5) 70~80% 상한
    assert F["peak_hourly"] == pytest.approx(F["max_daily"] * 1.8)  # 1.7.2 (6) 1.3~1.8 상한


def test_kds_primary_minimum_area_within_ranges(std):
    r = pl.plant_design(std(KDS), P)
    p, Q = r["primary"], r["flows_m3d"]["max_daily"]
    # 3.1.3 표면부하율 ≤70 → 면적, 3.1.5 침전시간 ≥2 h를 3.1.4 수심 2.5~4 m 안에서 → 수심 상한으로도 모자라 면적 확대
    assert p["depth_m"] == pytest.approx(4.0)
    assert p["area_m2"] == pytest.approx(Q * 2 / 24 / 4.0)
    assert check(p, "primary_surface_loading")["ok"] and 35 <= check(p, "primary_surface_loading")["value"] <= 70
    assert p["count"] == 2  # 3.1.1 (3)
    assert p["weir_length_m"] == pytest.approx(Q / 250)  # 3.1.9 (3)


def test_kds_holds_without_unit_loads_then_uses_project_values(std):
    r = pl.plant_design(std(KDS), P)
    assert r["effluent_mgL"]["bod"] is None
    assert any("bod_per_capita_kg" in h for h in r["held"])
    st = std(KDS, bod_per_capita_kg=0.05, ss_per_capita_kg=0.05, primary_bod_removal=0.3, primary_ss_removal=0.5,
             asp_bod_removal=0.9, asp_ss_removal=0.9, return_ratio=0.5)
    r = pl.plant_design(st, P)
    c = 0.05 * P / r["flows_m3d"]["average"] * 1000  # 1.7.3 (2) 부하량 ÷ 계획1일평균오수량
    assert r["influent_mgL"]["bod"] == pytest.approx(c)
    assert r["effluent_mgL"]["bod"] == pytest.approx(c * 0.7 * 0.1)
    assert set(r["effluent_judgement"]) == {"Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ"}  # 지역은 입력 없이 넷 다 판정
    assert r["effluent_judgement"]["Ⅰ"]["bod"]["limit"] == 5  # 별표 1 (2029-12-01~) 500~1만 m3/일 Ⅰ지역
    assert r["effluent_judgement"]["Ⅲ"]["bod"]["limit"] == 10
    sol = check(r["secondary"], "secondary_solids_loading")  # 3.2.4, 반송비가 생기면 판정
    assert sol["range"] == [40, 125]


def test_tss_influent_per_capita_11_253(std):
    r = pl.plant_design(std(TSS), P)
    assert r["bod_per_capita_kg"]["value"] == pytest.approx(0.077, abs=1e-4)
    assert r["influent_mgL"]["bod"] == pytest.approx(0.077 * P / r["flows_m3d"]["average"] * 1000, rel=1e-3)
    assert r["primary"]["bod_removal"]["value"] == pytest.approx(0.333, abs=1e-3)  # 72.21 약 1/3


def test_tss_primary_two_flow_conditions_and_aeration_loading(std):
    r = pl.plant_design(std(TSS), P)
    F, p = r["flows_m3d"], r["primary"]
    # 72.21 평균 ≤1,000 gpd/ft2(41), 첨두시간 1,500~2,000 중 엄격한 1,500(61.1) → 큰 면적
    assert p["area_m2"] == pytest.approx(max(F["average"] / 41.0, F["peak_hourly"] / 61.1187), rel=1e-4)
    a = r["aeration"]
    S1 = r["influent_mgL"]["bod"] * (1 - r["primary"]["bod_removal"]["value"])
    assert a["volume_m3"] == pytest.approx(max(F["average"] * S1 / 1000 / 0.64, 0), rel=1e-3)  # 92.31 40 lb/1000 ft3/d
    assert a["oxygen_kgd"] == pytest.approx(1.1 * F["peak_hourly"] * S1 / 1000)  # 92.331 첨두시간 BOD5당 1.1
    assert any("최대일유량" in h or "max_daily" in h for h in r["held"])  # 72.232 고형물부하 판정 보류


def test_cpheeo_table_5_9_and_sludge(std):
    r = pl.plant_design(std(IN), P)
    a, F = r["aeration"], r["flows_m3d"]
    assert r["influent_mgL"]["bod"] == pytest.approx(27.0e-3 * P / F["average"] * 1000)  # Table 5.4 27 g
    S1 = r["influent_mgL"]["bod"] * (1 - 0.35)  # 5.7.5 설계 35%
    X = (1500 + 3000) / 2
    assert a["volume_m3"] == pytest.approx(F["average"] * S1 / (0.4 * X))  # F/M 상한 0.4가 HRT 4 h보다 큼
    assert a["yobs"] == pytest.approx(0.5 / (1 + 0.06 * 6.5))  # Y 0.5·kd 0.06·θc 5~8 중앙
    S = S1 * (1 - 0.85)
    assert a["sludge_kgd"] == pytest.approx(F["average"] * a["yobs"] * (S1 - S) / 1000 / 0.8)
    assert a["oxygen_kgd"] == pytest.approx(1.0 * F["average"] * (S1 - S) / 1000)
    j = r["effluent_judgement"]["-"]["bod"]
    assert j["limit"] == 10 and j["ok"] is False  # NGT 2019 BOD 10 — 표준법만으로 미달


def test_colombia_peak_factor_interpolation(std):
    st = std(CO)
    assert pl.factor_interp(st, "plant_peak_factor_hourly", 10)[0] == 4
    assert pl.factor_interp(st, "plant_peak_factor_hourly", 50)[0] == pytest.approx(4 + (2.9 - 4) * 40 / 80)
    assert pl.factor_interp(st, "plant_peak_factor_daily", 1000)[0] == 1.5


def test_colombia_small_plant_uses_three_times_average(std):
    st = std(CO)
    F, info = pl.flows(st, 5000)
    assert F["average"] * 3 / 86.4 <= 30
    assert F["peak_hourly"] == pytest.approx(F["average"] * 3) and F["max_monthly"] == pytest.approx(F["average"] * 3)
    assert "Art.166" in info["peak_hourly"]


def test_colombia_tropical_loading_and_effluent(std):
    r = pl.plant_design(std(CO), P)
    a = r["aeration"]
    assert a["flow"] == "max_monthly"  # Tabla 22 반응조 = 월최대
    lv = next(c for c in a["checks"] if c["item"] == "BOD 용적부하")
    assert lv["value"] <= 0.7 + 1e-9 and lv["range"] == [None, 0.7]  # 열대 최고값은 상한
    assert r["effluent_judgement"]["-"]["bod"]["limit"] == 90  # Res. 0631 Art.8 ≤625 kg/d
    assert r["effluent_mgL"]["bod"] == pytest.approx(r["influent_mgL"]["bod"] * 0.7 * 0.2)  # Tabla 29 하한 30%·80%


@pytest.mark.parametrize("spec,x,ok", [(">=10000", 10000, True), ("500~<10000", 10000, False), ("500~<10000", 2800, True),
                                       ("<50", 49, True), (">625 y <=3000", 625, False), (">625 y <=3000", 3000, True), ("<=625", 600, True)])
def test_band_notation(spec, x, ok):
    assert pl.in_band(spec, x) is ok


def test_no_country_branches_in_plant_engine():
    src = (ROOT / "engine" / "plant.py").read_text(encoding="utf-8")
    for token in ('"KR"', '"US"', '"IN"', '"CO"', "KDS_", "TSS_", "CPHEEO", "RAS_"):
        assert token not in src, token
