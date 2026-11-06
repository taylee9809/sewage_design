"""Colebrook-White 부분류 계산과 영국 DCG 규칙 연결."""
import math
import os

import pytest

from engine import hydraulics as h

CW = h.ColebrookWhite(0.0015, 1.141e-6)


def darcy_velocity(D, S, ks, nu):
    """같은 식을 마찰계수 f 고정점 반복으로 따로 풀어 대조한다 (만관)."""
    f, V = 0.03, 1.0
    for _ in range(200):
        V = math.sqrt(2 * 9.81 * D * S / f)
        Re = V * D / nu
        f = (-2 * math.log10(ks / (3.7 * D) + 2.51 / (Re * math.sqrt(f)))) ** -2
    return V


@pytest.mark.parametrize("D,S", [(0.15, 1 / 150), (0.1, 1 / 80), (0.3, 0.002), (0.9, 0.0005)])
def test_full_pipe_matches_darcy(D, S):
    assert h.velocity(D, S, CW) == pytest.approx(darcy_velocity(D, S, CW.ks, CW.nu), rel=1e-6)


def test_half_full_same_velocity_half_flow():
    assert h.velocity(0.15, 0.01, CW, 0.5) == pytest.approx(h.velocity(0.15, 0.01, CW))
    assert h.flow(0.15, 0.01, CW, 0.5) == pytest.approx(h.flow(0.15, 0.01, CW) / 2)


def test_inverse_functions_round_trip():
    S = h.slope_for_velocity(0.15, CW, 0.75)
    assert h.velocity(0.15, S, CW) == pytest.approx(0.75, rel=1e-6)
    S = h.slope_for_flow(0.15, CW, 0.01, 0.75)
    assert h.flow(0.15, S, CW, 0.75) == pytest.approx(0.01, rel=1e-6)
    S = h.slope_for_velocity_at_flow(0.15, CW, 0.75, 0.002)
    yr = h.depth_ratio_for_flow(0.15, S, CW, 0.002)
    assert h.velocity(0.15, S, CW, yr) == pytest.approx(0.75, rel=1e-5)


def test_manning_slope_for_flow_unchanged():
    assert h.slope_for_flow(0.2, 0.013, 0.01) == pytest.approx((0.01 * 0.013 / (h.area(0.2) * h.hydraulic_radius(0.2) ** (2 / 3))) ** 2)


needs_db = pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")
SID = "GB_DCG_V2_3_20231111"
PROJECT = {"material": "pvc", "standards": {SID: {k: {"value": v} for k, v in {
    "persons_per_dwelling": 2.4, "kinematic_viscosity": 1.141e-6, "capacity_basis": "depth", "wc_connected": "at_least_one",
    "street_location": "highway_unrestricted", "access_pair": "manhole-manhole"}.items()}}}


@pytest.fixture(scope="module")
def st():
    from engine.generic import Standard
    return Standard(SID, PROJECT)


@needs_db
def test_flow_per_dwelling(st):
    assert st.peak_flow(24) == pytest.approx(10 * 0.05 / 1000)
    assert st.peak_flow(25) == pytest.approx(11 * 0.05 / 1000)


@needs_db
def test_min_diameter_by_dwellings(st):
    assert st.min_diameter(24) == 100
    assert st.min_diameter(25) == 150


@needs_db
def test_alternative_slope_replaces_velocity(st):
    """10세대 150 mm: 0.75 m/s보다 1:150이 완만하면 대체 경사가 지배."""
    Q = st.peak_flow(24)
    vel = [r for r in st.requirements(150, 150, Q, Q) if r.kind == "velocity"]
    assert len(vel) == 1 and vel[0].slope == pytest.approx(1 / 150, rel=1e-3)
    assert vel[0].clause.startswith("B6.9(a)")


@needs_db
def test_no_alternative_for_225(st):
    Q = st.peak_flow(240)
    vel = [r for r in st.requirements(225, 225, Q, Q) if r.kind == "velocity"][0]
    assert h.velocity(0.225, vel.slope, st.n, h.depth_ratio_for_flow(0.225, vel.slope, st.n, Q / 3)) == pytest.approx(0.75, rel=1e-4)


@needs_db
def test_capacity_basis_flow_is_stricter_than_depth(st):
    from engine.generic import Standard
    p = {"material": "pvc", "standards": {SID: {**PROJECT["standards"][SID], "capacity_basis": {"value": "flow"}}}}
    Q = 0.02
    cap = lambda s: [r for r in s.requirements(225, 225, Q, Q) if r.kind == "capacity"][0].slope
    assert cap(Standard(SID, p)) > cap(st)


@needs_db
def test_cover_and_spacing_from_project(st):
    assert st.cover(150) == 1.2
    assert st.spacing(150) == 90
