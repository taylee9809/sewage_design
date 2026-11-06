"""추가 맨홀 종단 배치 (place_manholes). 기준값은 공개 CSV에서 읽어 DB 없이 돈다."""
import csv
import json
import sys
from pathlib import Path

import pytest

from engine import criteria_db as db
from engine import design as ds
from engine.generic import Standard
from engine.network import depth_x_len

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "db"))
from load_criteria import load_normalized, normalize, row_key  # noqa: E402

FILES = {"KDS_61_40_00_20251001": "kds", "JP_YOKOHAMA_SEKKEI_202604": "japan", "CO_RAS_0330_2017_COMP2021": "colombia"}
PARAMS = {"manhole_max_spacing", "junction_drop_min", "drop_manhole_threshold", "max_drop_per_manhole",
          "junction_drop_max", "drop_pipe_diameter"}
KDS, JP, CO = FILES


def rows_from_csv(sid):
    out = []
    if sid not in FILES:
        return out
    norm = load_normalized()
    for r in csv.DictReader((ROOT / "criteria" / (FILES[sid] + "_sewer.csv")).open(encoding="utf-8")):
        if r["param_key"] not in PARAMS:
            continue
        lo, hi, _ = normalize(r)
        nz = norm.get(row_key(r), {}).get("condition")
        cond = nz if nz is not None else (json.loads(r["condition"]) if r["condition"].strip() else {})
        out.append(db.Row(sid, r["param_key"], cond, {}, lo, hi, r["binding"], r["clause_no"]))
    return out


@pytest.fixture
def std(monkeypatch):
    monkeypatch.setattr(db, "load", lambda sid, dsn=None: rows_from_csv(sid))
    choice = {KDS: {"junction": {"value": "crown"}}}
    return lambda sid: Standard(sid, {"standards": {sid: {"manning_n": {"value": 0.013}, **choice.get(sid, {})}}})


def place(st, L, S=0.004, dia=200, gl_up=100.0, gl_dn=99.0, inv_up=98.0):
    sp = st.spacing(dia)
    return sp, ds.place_manholes(st, L, sp, inv_up, S, dia / 1000, dia, gl_up, gl_dn)


def test_kds_equal_split_within_max_spacing(std):
    sp, (mhs, inv_dn) = place(std(KDS), 160.0)  # 7.1(1)② 600 mm 이하 75 m → 3등분
    assert sp == 75
    assert [round(m["x"], 2) for m in mhs] == [53.33, 106.67]
    assert all(m["drop"] == 0 for m in mhs)  # 관정접합, 같은 관경 → 낙차 없음
    assert inv_dn == pytest.approx(98.0 - 0.004 * 160)


def test_ground_interpolated_and_depth(std):
    _, (mhs, _) = place(std(KDS), 160.0)
    m = mhs[0]
    assert m["gl"] == pytest.approx(100.0 - 1.0 * 53.333333 / 160, abs=1e-6)
    assert m["depth"] == pytest.approx(m["gl"] - m["inv_out"])
    assert m["cover"] == pytest.approx(m["depth"] - 0.2)


def test_length_equal_to_spacing_needs_no_manhole(std):
    _, (mhs, inv_dn) = place(std(KDS), 75.0)
    assert mhs == []
    assert inv_dn == pytest.approx(98.0 - 0.004 * 75)


def test_colombia_min_drop_not_at_straight_through(std):
    st = std(CO)  # Art.154 120 m, Art.137 "손실 ≤ 0일 때" 관정 간 최소 0.02 m → 직선 통과(손실 > 0)는 해당 없음
    sp, (mhs, inv_dn) = place(st, 250.0)
    assert sp == 120
    assert len(mhs) == 2
    assert all(m["drop"] == 0 for m in mhs)
    assert inv_dn == pytest.approx(98.0 - 0.004 * 250)


def test_colombia_min_drop_kept_at_confluence(std):
    st = std(CO)  # 합류 맨홀은 손실 계산 미구현이라 종전대로 항상 적용
    assert st.junction(98.0, 0.2, 0.2) == pytest.approx(98.0 - 0.02)
    assert st.junction(98.0, 0.2, 0.2, straight=True) == pytest.approx(98.0)


class Unconditional:
    """조건 없는 관정 간 최소 낙차 0.02 m를 가진 가상 기준 — 맨홀 낙차 누적 확인용."""
    junction = staticmethod(lambda inv, u_D, D, straight=False: inv + u_D - D - 0.02)
    drop_check = staticmethod(lambda drop, nom, inner: None)


def test_unconditional_min_drop_accumulates():
    mhs, inv_dn = ds.place_manholes(Unconditional, 250.0, 120, 98.0, 0.004, 0.2, 200, 100.0, 99.0)
    assert [m["drop"] for m in mhs] == pytest.approx([0.02, 0.02])
    assert inv_dn == pytest.approx(98.0 - 0.004 * 250 - 0.04)


def test_japan_intermediate_drop_guide_not_applied(std):
    _, (mhs, inv_dn) = place(std(JP), 120.0)  # 4.1.2 표4.1 50 m, 3.5.9(3) 中間人孔 3 cm는 guide → 미적용
    assert len(mhs) == 2
    assert all(m["drop"] == 0 for m in mhs)
    assert inv_dn == pytest.approx(98.0 - 0.004 * 120)


def test_depth_x_len_integrates_manhole_drops():
    L, S, D = 250.0, 0.004, 0.2
    mhs, inv_dn = ds.place_manholes(Unconditional, L, 120, 98.0, S, D, 200, 100.0, 99.0)
    r = {"L": L, "D": D, "inv_up": 98.0, "inv_dn": inv_dn, "cover_up": 100.0 - 98.0 - D,
         "cover_dn": 99.0 - inv_dn - D, "manholes": mhs}
    # 맨홀 낙차가 없을 때의 사다리꼴 + 낙차가 그 뒤 구간을 깊게 한 만큼(0.02 m × 남은 연장)
    no_drop = L * ((100.0 - 98.0) + (99.0 - (98.0 - S * L))) / 2
    extra = 0.02 * (L - L / 3) + 0.02 * (L - 2 * L / 3)
    assert depth_x_len(r) == pytest.approx(no_drop + extra)
    r0 = {**r, "manholes": []}
    assert depth_x_len(r0) == pytest.approx(L * ((r["cover_up"] + r["cover_dn"]) / 2 + D))
