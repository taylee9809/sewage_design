"""원형관 자연유하 수리 계산 (Manning 공식, 부분류 포함).

모든 입력·출력은 SI: D[m], y[m], S[m/m], n[-], V[m/s], Q[m3/s].
기준별 판정 규칙(어떤 유량·수심에서 유속을 볼지 등)은 engine/standards/에 두고, 여기선 순수 기하·수리만 계산한다.
"""
import math

# 원형관 최대 유량이 나는 수심비 (dQ/dy=0). 이보다 깊으면 유량이 줄어 만관 유량과 겹친다.
Y_QMAX = 0.9382


def _theta(yr):
    """수심비 y/D → 수면이 만드는 중심각 θ[rad] (0 < y/D ≤ 1)."""
    if not 0 < yr <= 1:
        raise ValueError("수심비는 0 초과 1 이하: %r" % yr)
    return 2 * math.acos(1 - 2 * yr)


def area(D, yr=1.0):
    t = _theta(yr)
    return D * D * (t - math.sin(t)) / 8


def wetted_perimeter(D, yr=1.0):
    return D * _theta(yr) / 2


def hydraulic_radius(D, yr=1.0):
    return area(D, yr) / wetted_perimeter(D, yr)


def velocity(D, S, n, yr=1.0):
    """수심비 yr에서의 평균유속 V = (1/n)·R^(2/3)·S^(1/2)."""
    return hydraulic_radius(D, yr) ** (2 / 3) * math.sqrt(S) / n


def flow(D, S, n, yr=1.0):
    return area(D, yr) * velocity(D, S, n, yr)


def depth_ratio_for_flow(D, S, n, Q, tol=1e-10):
    """유량 Q가 흐를 때의 수심비. 0 < y/D ≤ Y_QMAX 구간에서 이분법. Q가 최대 유량을 넘으면 None."""
    if Q <= 0:
        raise ValueError("Q는 양수")
    if Q > flow(D, S, n, Y_QMAX):
        return None
    lo, hi = 1e-9, Y_QMAX
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if flow(D, S, n, mid) < Q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def slope_for_velocity(D, n, V, yr=1.0):
    """수심비 yr에서 유속 V가 나오는 경사."""
    return (V * n / hydraulic_radius(D, yr) ** (2 / 3)) ** 2


def _bisect_slope(metric, target, s_hi=1.0, tol=1e-12):
    """metric(S) ≥ target 이 되는 최소 경사. metric이 None(그 경사로는 유량을 못 흘림)이면 목표 미달로 본다.
    통수 가능 여부와 metric은 모두 경사에 대해 단조 증가."""
    lo, hi = 1e-9, s_hi
    m = metric(hi)
    if m is None or m < target:
        return None
    while hi - lo > tol * max(1.0, hi):
        mid = (lo + hi) / 2
        m = metric(mid)
        if m is None or m < target:
            lo = mid
        else:
            hi = mid
    return hi


def slope_for_velocity_at_flow(D, n, V, Q, s_hi=1.0, tol=1e-12):
    """유량 Q가 흐를 때(실수심) 유속이 V가 되는 경사."""
    def v_at(S):
        yr = depth_ratio_for_flow(D, S, n, Q)
        return None if yr is None else velocity(D, S, n, yr)
    return _bisect_slope(v_at, V, s_hi, tol)


RHO_G = 1000.0 * 9.81  # 물 단위중량 N/m3


def shear_stress(D, S, n, yr=1.0):
    """평균 벽면 전단응력 τ = ρ·g·R·S [Pa]."""
    return RHO_G * hydraulic_radius(D, yr) * S


def slope_for_shear_at_flow(D, n, tau, Q, s_hi=1.0, tol=1e-12):
    """유량 Q가 흐를 때(실수심) 평균 전단응력이 tau가 되는 경사."""
    def t_at(S):
        yr = depth_ratio_for_flow(D, S, n, Q)
        return None if yr is None else shear_stress(D, S, n, yr)
    return _bisect_slope(t_at, tau, s_hi, tol)
