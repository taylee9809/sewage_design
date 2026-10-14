"""공통 지표 M1~M5 — 일반 엔진(규칙 데이터)으로 계산. 기준 이름 분기 없음.

M1 요구 최소경사(D, Q, Qi)  M2 허용 최대유량(D, S)  M3 계획 첨두유량(P)  M4 맨홀 최대간격(D)  M5 최소 매설깊이(D)
관경은 호칭을 내경으로 보고 계산한다(지표 비교용). 실제 규격 내경 설계는 engine/design.py.
사용: py -3 -m engine.metrics SYN01 --dia 200 250 300 --q 0.002 --q-initial 0.0008
"""
import argparse
import math

from engine import criteria_db as db
from engine import hydraulics as h
from engine.design import DEFAULT_STANDARDS, load_project
from engine.generic import Standard


def m1(st, dia, Q, Qi=None):
    reqs = st.requirements(st.table_label(dia, dia), dia, Q, Qi if Qi is not None else Q)
    req = [r for r in reqs if r.binding in ("mandatory", "standard")]
    gov = max(req, key=lambda r: r.slope)
    return {"slope": gov.slope, "governing": gov, "rules": reqs}


def m2(st, dia, S):
    D, r = dia / 1000, st.rule("CAPACITY")
    if r["kind"] == "depth_ratio":
        yr, cl = st.design_depth()
        return {"Q": h.flow(D, S, st.n, yr), "basis": "설계수심 y/D=%.1f" % yr, "clause": cl}
    if r["kind"] == "margin":
        m = db.one(st.rows, r["param"], r["cond"])
        return {"Q": h.flow(D, S, st.n) / (1 + m.value_min), "basis": "만관 ÷ (1+여유 %.0f%%)" % (m.value_min * 100), "clause": m.clause_ref}
    return {"Q": h.flow(D, S, st.n), "basis": "만관", "clause": r.get("clause")}


def m3(st, P):
    return {"Q": st.peak_flow(P)}


def m4(st, dia):
    sp = st.spacing(dia)
    return {"spacing_m": sp, "per_km": math.ceil(1000 / sp)} if sp else {"error": "해당 관경 규정 없음"}


def m5(st, dia):
    c = st.cover(dia)
    return {"cover_m": c, "depth_m": c + dia / 1000}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--dia", type=int, nargs="+", default=[200, 250, 300])
    ap.add_argument("--q", type=float, default=0.002)
    ap.add_argument("--q-initial", type=float, default=None)
    ap.add_argument("--standards", nargs="*")
    a = ap.parse_args()
    project = load_project(a.project)
    sts = [Standard(s, project) for s in (a.standards or DEFAULT_STANDARDS)]
    for d in a.dia:
        print("\n== D=%d mm, Q=%.1f L/s" % (d, a.q * 1000))
        for st in sts:
            r = m1(st, d, a.q, a.q_initial)
            g = r["governing"]
            print("  %-28s M1 %.2f‰ ← %s [%s]  M4 %s  M5 %s" % (st.sid, r["slope"] * 1000, g.reason[:50], g.clause,
                                                                m4(st, d).get("spacing_m"), m5(st, d)["cover_m"]))


if __name__ == "__main__":
    main()
