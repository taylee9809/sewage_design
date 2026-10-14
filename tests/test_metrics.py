"""공통 지표 M1~M5 (일반 엔진). 로컬 DB 필요(SEWAGE_DB_DSN)."""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")

from engine import hydraulics as h  # noqa: E402
from engine.design import load_project  # noqa: E402
from engine.generic import Standard  # noqa: E402
from engine.metrics import m1, m2, m3, m4, m5  # noqa: E402

P = load_project("SYN01")
KR, US, JP, IN = "KDS_61_40_00_20251001", "TSS_WW_2026", "JP_YOKOHAMA_SEKKEI_202604", "CPHEEO_SEW_2013"
ST = {}


def st(sid):
    if sid not in ST:
        ST[sid] = Standard(sid, P)
    return ST[sid]


def test_kds_velocity_resolved_by_design_depth_full():
    r = m1(st(KR), 250, 0.002)
    assert r["slope"] == pytest.approx(h.slope_for_velocity(0.25, 0.011, 0.6, 1.0))
    assert r["governing"].clause == "1.3 (1) ①"


def test_tss_small_flow_governed_by_table():
    r = m1(st(US), 200, 0.002)
    assert r["slope"] == pytest.approx(0.004) and r["governing"].clause == "33.41"


def test_yokohama_margin():
    r = m1(st(JP), 200, 0.03)
    assert h.flow(0.2, r["slope"], 0.010) == pytest.approx(0.06, rel=1e-6)
    assert m2(st(JP), 300, 0.003)["Q"] == pytest.approx(h.flow(0.3, 0.003, 0.010) / 2)


def test_cpheeo_max_of_required_and_depth08():
    r = m1(st(IN), 300, 0.03, 0.012)
    assert r["slope"] == max(x.slope for x in r["rules"] if x.binding in ("mandatory", "standard"))
    assert m2(st(IN), 300, 0.003)["Q"] == pytest.approx(h.flow(0.3, 0.003, 0.010, 0.8))


def test_guide_rules_not_required():
    assert m1(st(JP), 250, 0.002)["governing"].binding != "guide"


def test_m3_flows():
    pf = (18 + 5 ** 0.5) / (4 + 5 ** 0.5)
    assert m3(st(US), 5000)["Q"] == pytest.approx(5000 * 379 / 1000 / 86400 * pf, rel=1e-3)
    assert m3(st(KR), 5000)["Q"] == pytest.approx(5000 * 300 * 1.2 / 1000 / 86400 * 1.8)  # 사업 채택값: 300 L·상한


def test_m4_m5():
    assert m4(st(KR), 600)["spacing_m"] == 75 and m4(st(KR), 601)["spacing_m"] == 100
    assert m4(st(JP), 300)["spacing_m"] == 50 and m4(st(IN), 300)["spacing_m"] == 30
    assert m5(st(KR), 200)["cover_m"] == 1.0 and m5(st(JP), 450)["cover_m"] == 1.8
