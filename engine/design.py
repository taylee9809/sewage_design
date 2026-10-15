"""관망 설계 (일반 엔진판). 기준별 차이는 전부 engine/generic.Standard가 규칙 데이터에서 읽는다.

사용: py -3 -m engine.design SYN01 [--standards <standard_id> ...]
"""
import argparse
import json
import math
import os

import psycopg

from engine import hydraulics as h
from engine.generic import ROOT, Standard
from engine.network import load_network, save, summarize, topo, tributary_pop

BIND_KO = {"mandatory": "의무", "standard": "기준"}
DEFAULT_STANDARDS = ["KDS_61_40_00_20251001", "TSS_WW_2026", "JP_YOKOHAMA_SEKKEI_202604", "CPHEEO_SEW_2013"]


def load_project(pid):
    return json.loads((ROOT / "criteria" / "projects" / ("%s.json" % pid)).read_text(encoding="utf-8"))


def design(st, nodes, links, sizes, lifts=(), fm_links=()):
    """lifts: 중계펌프장을 두는 맨홀 — 그 맨홀에서 나가는 관은 유입관 깊이와 무관하게 최소토피에서 다시 시작.
    fm_links: 압송관으로 대체하는 구간 — 자연유하로 설계하지 않고, 하류 접합 계산에서도 뺀다(압송관 끝 맨홀은 최소토피에서 시작)."""
    order, into = topo(links)
    p0, p1 = tributary_pop(order, into, nodes)
    dmin = st.min_diameter()
    vmax, vstate, venf = st.vmax()
    nodec = st.no_decrease()
    fb = st.fallback()
    mono = st.monotonic()
    out, res = [], {}
    for l in order:
        if l["id"] in fm_links:
            continue
        Q, Qi = st.peak_flow(p1[l["id"]]), st.peak_flow(p0[l["id"]])
        ups = [res[i["id"]] for i in into.get(l["up"], []) if i["id"] not in fm_links]
        # 하류 관경 감소 금지: 의무(hard)는 항상, 기준(standard)은 사업 파일에 근거 있는 예외(allow_decrease)가 없으면 적용
        enforce_nodec = nodec == "hard" or (nodec == "standard" and "allow_decrease" not in st.choice)
        floor_inner = max((u["D"] * 1000 for u in ups), default=0) if enforce_nodec else 0
        gl_up, gl_dn = nodes[l["up"]]["gl"], nodes[l["dn"]]["gl"]
        main_up = max(ups, key=lambda u: u["Q"]) if ups else None  # 합류점: 유량 최대 유입관을 상류 기준으로
        S_mono = main_up["S"] if (mono and main_up and l["up"] not in lifts) else None  # 하류 경사 점감 상한

        def trial(nom, inner):
            D = inner / 1000
            cover = st.cover(nom)
            inv_up = gl_up - cover - D
            if l["up"] not in lifts:
                for u in ups:
                    inv_up = min(inv_up, st.junction(u["inv_dn"], u["D"], D))
            S_cover = (inv_up - (gl_dn - cover - D)) / l["L"]
            reqs = [r for r in st.requirements(st.table_label(nom, inner), inner, Q, Qi) if r.binding in ("mandatory", "standard")]
            flush = False
            if fb and fb["applies_to"] == "VELOCITY_MIN":
                vel = [r for r in reqs if r.kind == "velocity"]
                rest = [r for r in reqs if r.kind != "velocity"]
                if vel and max(r.slope for r in vel) > max([S_cover] + [r.slope for r in rest]):
                    reqs, flush = rest, True
            cap = [r for r in reqs if r.kind == "capacity"]
            other = [r for r in reqs if r.kind != "capacity"]
            ok = max((r.slope for r in cap), default=0) <= max(S_cover, max((r.slope for r in other), default=0))
            if S_mono is not None:  # 요구 경사가 상류 경사보다 급하면 관경을 키워 낮춘다
                ok = ok and max(r.slope for r in reqs) <= S_mono + 1e-12
            return {"dia": nom, "D": D, "cover": cover, "inv_up": inv_up, "S_cover": S_cover, "gov": max(reqs, key=lambda r: r.slope),
                    "ok": ok, "flush": flush}

        t = None
        for nom, inner in sizes:
            if st.dia_compare(nom, inner) < dmin - 1e-6 or inner < floor_inner - 1e-6:
                continue
            t = trial(nom, inner)
            if t["ok"]:
                break
        D, cover, inv_up, gov, dia = t["D"], t["cover"], t["inv_up"], t["gov"], t["dia"]
        S = max(gov.slope, t["S_cover"])
        drop = 0.0
        governing = "%s %s" % (gov.clause, gov.reason)
        S_vmax = None
        if venf == "hard":  # 최대유속을 넘지 않는 경사 상한 (판정 상태별: 만관·설계수심 또는 실수심)
            S_vmax = (h.slope_for_velocity_at_flow(D, st.n, vmax, max(Q, 1e-6)) if vstate == "actual"
                      else h.slope_for_velocity(D, st.n, vmax, st.design_depth()[0] if vstate == "design_depth" else 1.0))
        S_cap = min([x for x in (S_vmax, S_mono) if x is not None], default=None)
        if S_cap is not None and S > S_cap:
            S = max(gov.slope, S_cap)
            need = (gl_dn - cover - D) + S * l["L"]
            if inv_up > need:
                drop, inv_up = inv_up - need, need
            why = ("최대유속 %.1f m/s" % vmax) if S_cap == S_vmax else ("하류 경사 점감(%s %s)" % (mono["clause"], BIND_KO[mono["binding"]]))
            governing = "%s로 경사 제한, 상류 맨홀 낙차 %.2f m" % (why, drop)
        elif S == t["S_cover"] and t["S_cover"] > gov.slope:
            governing = "지반 따라 최소토피 유지(요구 경사 %.2f‰보다 급함)" % (gov.slope * 1000)
        if not t["ok"]:
            governing += " [규격 최대 관경으로도 지반 경사 내 통수 불가]"
        if t["flush"]:
            governing += " [자기세정 유속 미확보 → 플러싱 장치 필요(%s)]" % fb["clause"]
        if nodec == "warn" and ups and dia < max(u["dia"] for u in ups):
            r = st.rule("NO_DECREASE")
            governing += " [경고: 하류 관경 감소 — %s %s]" % (r["clause"], r.get("text", ""))
        if S_mono is not None and gov.slope > S_mono + 1e-12:
            governing += " [경고: 요구 경사가 상류 경사보다 급함 — 경사 점감 미충족(%s)]" % mono["clause"]
        # 배수설비 연결점: 본관이 오수받이에서 연결관으로 받을 수 있을 만큼 깊어야 한다 → 경사 유지한 채 구간을 낮춤
        conn_low = 0.0
        held = None
        for c in l.get("conns", []):
            lim, why = st.house_connection(c["z"], c["Lc"], D)
            if lim is None:
                held = why
                continue
            over = (inv_up - S * c["x"]) - lim
            if over > conn_low + 1e-9:
                conn_low, conn_why = over, "배수설비 %s: %s" % (c["id"], why)
        if conn_low > 5e-4:
            inv_up -= conn_low
            governing += " [배수설비 연결 위해 %.3f m 낮춤 — %s]" % (conn_low, conn_why)
        if held:
            governing += " [배수설비 연결 %s]" % held
        v_here = st.v_check(D, S, Q)
        if mono and main_up and mono.get("velocity") == "non_decreasing" and v_here < main_up["v"] - 1e-9:
            governing += " [참고: 유속 점증 미충족 %.2f<%.2f m/s(%s)]" % (v_here, main_up["v"], mono["clause"])
        inv_dn = inv_up - S * l["L"]
        sp = st.spacing(dia)
        r = {"link": l["id"], "dia": dia, "D": D, "S": S, "Q": Q, "Qi": Qi, "inv_up": inv_up, "inv_dn": inv_dn,
             "cover_up": gl_up - inv_up - D, "cover_dn": gl_dn - inv_dn - D, "v": st.v_check(D, S, Q),
             "extra_mh": max(0, math.ceil(l["L"] / sp) - 1) if sp else None, "drop": drop, "governing": governing, "L": l["L"]}
        res[l["id"]] = r
        out.append(r)
    return out


def run(pid, standards=None, dsn=None):
    dsn = dsn or os.environ["SEWAGE_DB_DSN"]
    project = load_project(pid)
    results = {}
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        nodes, links = load_network(cur, pid)
        for sid in standards or list(project["standards"]):  # 기본: 사업 파일에 채택값이 있는 기준 전부
            st = Standard(sid, project, dsn)
            results[sid] = design(st, nodes, links, st.pipe_sizes(cur))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--standards", nargs="*")
    a = ap.parse_args()
    for sid, out in run(a.project, a.standards).items():
        print(sid, summarize(out))


if __name__ == "__main__":
    main()
