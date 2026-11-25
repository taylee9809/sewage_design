"""맨홀 낙차 판정 (DROP_STRUCTURE). 기준값은 공개 CSV에서 읽어 DB 없이 돈다."""
import csv
import json
import sys
from pathlib import Path

import pytest

from engine import criteria_db as db
from engine import design as ds
from engine.generic import Req, Standard

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "db"))  # db/는 스크립트 폴더라 형제 모듈을 바로 import한다
from load_criteria import load_normalized, normalize, row_key  # noqa: E402

FILES = {"KDS_61_40_00_20251001": "kds", "TSS_WW_2026": "tenstates2026", "JP_YOKOHAMA_SEKKEI_202604": "japan",
         "CPHEEO_SEW_2013": "cpheeo", "CO_RAS_0330_2017_COMP2021": "colombia"}
PARAMS = {"drop_manhole_threshold", "max_drop_per_manhole", "junction_drop_max", "drop_pipe_diameter"}


def rows_from_csv(sid):
    """load_criteria와 같은 조건(정규화본 우선)·단위로 Row를 만든다."""
    out = []
    if sid not in FILES:  # 유량·펌프장 기준 코드 — 낙차 판정에 안 쓴다
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
    return lambda sid: Standard(sid, {"standards": {sid: {"manning_n": {"value": 0.013}}}})


def note(st, drop, nom=200, inner=200):
    return st.drop_check(drop, nom, inner)


@pytest.mark.parametrize("sid,below,at,above", [
    ("KDS_61_40_00_20251001", 0.59, True, 0.61),  # 5.1(2) 0.6 m 이상
    ("JP_YOKOHAMA_SEKKEI_202604", 0.59, True, 0.61),  # 4.1.8 0.60 m 以上
    ("CPHEEO_SEW_2013", 0.59, False, 0.61),  # 3.25 600 mm 초과
])
def test_threshold_boundary_follows_text(std, sid, below, at, above):
    st = std(sid)
    assert note(st, below) is None
    assert (note(st, 0.6) is not None) == at
    assert note(st, above)["pipe"]


def test_inch_threshold_converted(std):
    st = std("TSS_WW_2026")  # 34.2 24 in(610 mm) 이상
    assert note(st, 0.60) is None
    assert note(st, 0.61)["pipe"]


def test_colombia_threshold_exclusive(std):
    st = std("CO_RAS_0330_2017_COMP2021")  # Art.155 0.75 m 초과
    assert note(st, 0.75) is None
    assert note(st, 0.76)["pipe"]


def test_max_drop(std):
    assert not note(std("KDS_61_40_00_20251001"), 1.5)["over"]
    r = note(std("KDS_61_40_00_20251001"), 1.51)
    assert r["over"] and "경고" in r["note"]
    assert note(std("JP_YOKOHAMA_SEKKEI_202604"), 1.51)["over"]
    assert not note(std("CO_RAS_0330_2017_COMP2021"), 7.0)["over"]
    assert note(std("CO_RAS_0330_2017_COMP2021"), 7.1)["over"]
    assert not note(std("TSS_WW_2026"), 9.0)["over"]  # 상한 규정 없음


@pytest.mark.parametrize("nom,mm", [(200, 150), (300, 200), (450, 250), (600, 300)])
def test_drop_pipe_table_japan(std, nom, mm):
    assert ("부관 관경 %d mm" % mm) in note(std("JP_YOKOHAMA_SEKKEI_202604"), 1.0, nom, nom)["note"]


@pytest.mark.parametrize("inner,mm", [(300, 170), (400, 280), (800, 360)])
def test_drop_pipe_table_colombia(std, inner, mm):
    assert ("부관 관경 %d mm" % mm) in note(std("CO_RAS_0330_2017_COMP2021"), 1.0, inner, inner)["note"]


def test_special_cases(std):
    assert "전이구조" in note(std("CO_RAS_0330_2017_COMP2021"), 1.0, 1000, 1000)["note"]
    assert "300 mm 이상" in note(std("CPHEEO_SEW_2013"), 1.0, 300, 300)["note"]
    assert "분할 낙차" in note(std("CPHEEO_SEW_2013"), 1.0, 500, 500)["note"]


class Stub:
    """drop_check만 진짜 기준을 쓰는 최소 기준 객체 — 설계 흐름 확인용."""
    n = 0.013

    def __init__(self, st):
        self.drop_check = st.drop_check

    min_diameter = lambda self, P=None: 200
    vmax = lambda self: (3.0, "full", "hard")
    no_decrease = lambda self: None
    fallback = lambda self: None
    monotonic = lambda self: None
    peak_flow = lambda self, p: 0.01
    cover = lambda self, nom: 1.0
    junction = lambda self, inv, u_D, D: inv + u_D - D
    table_label = lambda self, nom, inner: nom
    dia_compare = lambda self, nom, inner: nom
    requirements = lambda self, label, inner, Q, Qi: [Req(0.003, "table", "최소경사표", "x", "standard")]
    v_check = lambda self, D, S, Q: 1.0
    spacing = lambda self, dia: None


def network(gl_mid):
    nodes = {"A": {"gl": 100.0, "p0": 10, "p1": 10}, "B": {"gl": gl_mid, "p0": 0, "p1": 0}, "C": {"gl": gl_mid - 0.2, "p0": 0, "p1": 0}}
    links = [{"id": "L1", "up": "A", "dn": "B", "L": 50.0}, {"id": "L2", "up": "B", "dn": "C", "L": 50.0}]
    return nodes, links


def test_design_flags_drop_pipe_at_junction_of_steep_run(std):
    nodes, links = network(95.0)
    st = Stub(std("KDS_61_40_00_20251001"))
    out = ds.design(st, nodes, links, [(200, 200)])
    assert out[1]["drop_pipes"] == 0

    orig = st.junction
    st.junction = lambda inv, u_D, D: orig(inv, u_D, D) - 0.8  # 접합에서 0.8 m 낮아지는 경우
    out = ds.design(st, nodes, links, [(200, 200)])
    assert out[1]["drop_pipes"] == 1
    assert "L1 유입 부관 필요" in out[1]["governing"]


def test_design_skips_lift_manhole(std):
    nodes, links = network(95.0)
    st = Stub(std("KDS_61_40_00_20251001"))
    st.junction = lambda inv, u_D, D: inv - 0.8
    out = ds.design(st, nodes, links, [(200, 200)], lifts=("B",))
    assert out[1]["drop_pipes"] == 0
