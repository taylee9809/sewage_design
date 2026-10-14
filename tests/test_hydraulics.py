"""원문 표를 정답지로 수리 계산을 검증한다. 표는 criteria/clauses의 조문 원문에서 직접 읽는다."""
import json
import re
from pathlib import Path

import pytest

from engine import hydraulics as h

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "db"))
from paths import CLAUSE_DIRS, jsonl_files  # noqa: E402


def body(standard_id, clause_no):
    """조문 원문. 재배포 불가 기준은 비공개 폴더에 있으며, 없으면 해당 테스트를 건너뛴다."""
    for f in jsonl_files(CLAUSE_DIRS):
        for l in open(f, encoding="utf-8"):
            o = json.loads(l)
            if o["standard_id"] == standard_id and o["clause_no"] == clause_no:
                return o["body_text"]
    pytest.skip("원문 없음(비공개 폴더 필요): %s %s" % (standard_id, clause_no))


# ── 요코하마 표3.24 관거 표준구배 일람표 (만관 유속·유량, 正誤 2026-04-17 반영본) ──
def yokohama_324():
    t = body("JP_YOKOHAMA_SEKKEI_202604", "3.5.4 解説")
    t = t[t.index("表3.24 管きょの標準勾配一覧表"):t.index("[正誤 2026-04-17 反映]")]
    rows = []
    for line in t.splitlines():
        c = [x.strip().replace(",", "") for x in line.split("|")]
        if len(c) == 7 and re.fullmatch(r"\d+", c[0]):
            D = float(c[0]) / 1000
            rows.append((D, 0.013, float(c[1]) / 1000, float(c[2]), float(c[3])))  # 剛性管
            rows.append((D, 0.010, float(c[4]) / 1000, float(c[5]), float(c[6])))  # 可とう性管
    return rows


Y324 = yokohama_324()


def test_yokohama_324_parsed():
    assert len(Y324) == 38


@pytest.mark.parametrize("D,n,S,V,Q", Y324)
def test_yokohama_324_full_flow(D, n, S, V, Q):
    # 표는 소수 셋째 자리까지 인쇄 → 반올림 오차 0.0005 + 계산 여유
    assert h.velocity(D, S, n) == pytest.approx(V, abs=0.0015)
    assert h.flow(D, S, n) == pytest.approx(Q, abs=0.0015)


# ── 인도 CPHEEO Table 3.12 원형관 수리특성 (n 일정) ──
def cpheeo_312():
    t = body("CPHEEO_SEW_2013", "3.15.5")
    t = t[t.index("Table 3.12 Hydraulic properties"):]
    rows = []
    for line in t.splitlines()[2:12]:
        left = line.split("||")[0]
        # 원문 인쇄 오타 '1 120', '0 776', '0,088'은 자리표시만 깨진 것 → 숫자로 정규화
        c = [x.strip().replace(",", ".").replace(" ", ".") if re.fullmatch(r"\d[ ,]\d+", x.strip()) else x.strip()
             for x in left.split("|")]
        rows.append(tuple(float(x) for x in c))
    return rows


C312 = cpheeo_312()


def test_cpheeo_312_parsed():
    assert len(C312) == 10 and C312[0] == (1.0, 1.0, 1.0)


CPHEEO_KNOWN = {
    # 원문 Table 3.12의 d/D=0.8 q/Q 0.968은 원형 단면 기하로 0.977. 같은 매뉴얼 3.15.5 본문은 0.98로 적어 표 쪽 인쇄값이 어긋남.
    0.8: "원문 표 q/Q 0.968 ≠ 기하 계산 0.977 (본문 3.15.5는 0.98)",
}


@pytest.mark.parametrize("yr,vV,qQ", [
    pytest.param(*r, marks=pytest.mark.xfail(reason=CPHEEO_KNOWN[r[0]], strict=True)) if r[0] in CPHEEO_KNOWN else r
    for r in C312])
def test_cpheeo_312_hydraulic_elements(yr, vV, qQ):
    D, S, n = 0.3, 0.003, 0.013  # 비율이라 D·S·n과 무관
    assert h.velocity(D, S, n, yr) / h.velocity(D, S, n) == pytest.approx(vV, abs=0.002)
    assert h.flow(D, S, n, yr) / h.flow(D, S, n) == pytest.approx(qQ, abs=0.002)


# ── 미국 Ten States 2026 §33.41 최소경사표 ↔ 만관 2.0 ft/s (n=0.013) ──
def tss_3341():
    t = body("TSS_WW_2026", "33.41")
    rows = []
    for line in t.splitlines():
        m = re.match(r"\s*(\d+) inch \((\d+) mm\)\s*\|\s*([\d.]+)\s*$", line)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)) / 1000, float(m.group(3)) / 100))
    return rows


T3341 = tss_3341()


def test_tss_3341_parsed():
    assert len(T3341) == 13


@pytest.mark.parametrize("d_in,D_mm,S", T3341)
def test_tss_3341_full_velocity(d_in, D_mm, S):
    # 표의 경사로 만관 유속을 내면 2.0 ft/s(0.61 m/s) 이상이어야 하고, 표가 그 하한에 맞춰 만들어졌으면 크게 넘지 않는다
    v = h.velocity(d_in * 0.0254, S, 0.013)
    assert 0.60 <= v <= 0.70, v


# ── 역계산 일관성 ──
def test_depth_ratio_roundtrip():
    D, S, n = 0.25, 0.005, 0.013
    for yr in (0.1, 0.3, 0.5, 0.8, 0.9):
        assert h.depth_ratio_for_flow(D, S, n, h.flow(D, S, n, yr)) == pytest.approx(yr, abs=1e-6)


def test_slope_for_velocity_examples():
    # 200mm, n=0.013: 만관 0.6 m/s 경사 ≈ 0.33%, 수심 30%에서 0.6 m/s 경사 ≈ 0.55% (대화 중 수기 계산값)
    assert h.slope_for_velocity(0.2, 0.013, 0.6) == pytest.approx(0.0033, abs=0.00005)
    assert h.slope_for_velocity(0.2, 0.013, 0.6, 0.3) == pytest.approx(0.00549, abs=0.0001)


def test_cpheeo_appendix_a34_example1():
    # CPHEEO 부록 A 3.4 A 예제 1: D=200mm, 1 in 250, n=0.013 → 만관 0.67 m/s·1260 lpm(노모그램 판독), d/D 0.8에서 v=0.76 m/s
    D, S, n = 0.2, 1 / 250, 0.013
    assert h.velocity(D, S, n) == pytest.approx(0.67, abs=0.015)
    assert h.flow(D, S, n) * 60000 == pytest.approx(1260, rel=0.03)
    assert h.velocity(D, S, n, 0.8) == pytest.approx(0.76, abs=0.015)


def test_slope_for_velocity_at_flow_is_minimal_not_decade_step():
    # 회귀: 예전 구현은 통수 불가 구간을 10배씩 건너뛰며 1e-2 같은 값을 그대로 돌려줬다
    D, n, Q = 0.182, 0.010, 0.0123
    S = h.slope_for_velocity_at_flow(D, n, 0.6, Q)
    yr = h.depth_ratio_for_flow(D, S, n, Q)
    assert h.velocity(D, S, n, yr) == pytest.approx(0.6, abs=1e-6)
    S = h.slope_for_shear_at_flow(D, n, 1.0, Q)
    yr = h.depth_ratio_for_flow(D, S, n, Q)
    assert h.shear_stress(D, S, n, yr) == pytest.approx(1.0, abs=1e-6)
