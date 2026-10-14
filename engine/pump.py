"""펌프장·압송관 (원문 기준) — 규칙 유형 PUMP_TRIGGER·FORCE_MAIN_*·PUMP_COUNT·WET_WELL_VOLUME·PUMP_HEAD_POWER.

흐름: 자연유하 설계 → 전환 조건 판정 → 펌프장(인라인 양수장) 위치 → 하류 재설계 → 펌프장별 압송관·대수·습정·양정·동력.
- 전환 조건 kind: depth_limit(매설 깊이 한도 초과 시 자동 배치) | review(수치 없음 → 판정 보류·설계자 검토 표시) | none
- 사업 파일 "pump_stations"에 맨홀을 지정하면 기준과 무관하게 그 위치에 둔다(정해진 펌프장 위치)
- 모델 한계: 인라인 양수장(양수 후 같은 맨홀에서 자연유하 재개). 압송관 길이 = 실양정 + 사업값 lift_main_extra_m
사용: py -3 -m engine.pump SYN02
"""
import math
import os
import sys

import psycopg

from engine import criteria_db as db
from engine import hydraulics as h
from engine.design import design, load_project
from engine.generic import Standard
from engine.network import load_network, summarize, topo, tributary_pop

RHO_G = 9.81  # kN/m3


def _rows(st, r):
    return st.pump_rows if r.get("standard") == "pump" else st.rows


def depth(r):
    return max(r["cover_up"], r["cover_dn"]) + r["D"]


def outfall_check(out, nodes, links):
    """토구 지정 관저고(min_invert_el)보다 낮게 도착하면 자연유하 불가."""
    L = {l["id"]: l for l in links}
    msgs = []
    for r in out:
        n = nodes[L[r["link"]]["dn"]]
        if n["kind"] == "outfall" and n.get("min_inv") is not None and r["inv_dn"] < n["min_inv"] - 1e-6:
            msgs.append("토구 %s 도착 관저고 %.2f < 지정 %.2f → 자연유하 불가" % (L[r["link"]]["dn"], r["inv_dn"], n["min_inv"]))
    return msgs


def place_lifts(st, nodes, links, sizes, fixed):
    """전환 조건으로 펌프장 위치를 정한다. 반환: (lifts, 설계 결과, 판정 메모)."""
    trig = st.rule("PUMP_TRIGGER") or {"kind": "none"}
    lifts = set(fixed)
    out = design(st, nodes, links, sizes, lifts)
    notes = []
    if trig["kind"] == "depth_limit":
        row = [x for x in db.pick(_rows(st, trig), trig["param"], trig.get("cond", {}), allow=tuple(trig.get("allow", ())))
               if x.binding in ("mandatory", "standard")][0]
        limit = row.value_max
        for _ in range(len(links)):
            over = next((r for r in out if depth(r) > limit + 1e-9), None)
            if not over:
                break
            up = next(l["up"] for l in links if l["id"] == over["link"])
            if up in lifts:
                notes.append("%s: 펌프장 다음 구간도 한도 초과" % over["link"])
                break
            lifts.add(up)
            notes.append("%s 매설 %.2f m > %.1f m (%s) → %s에 중계펌프장" % (over["link"], depth(over), limit, row.clause_ref, up))
            out = design(st, nodes, links, sizes, lifts)
    elif trig["kind"] == "review":
        deep = max(out, key=depth)
        notes.append("판정 보류(설계자 검토): %s — 최대 매설 %.2f m (%s)" % (trig.get("text", ""), depth(deep), deep["link"]))
    # 물리적 필요: 토구 지정 관저고에 자연유하로 못 닿으면 토구 직전 맨홀에 펌프장 (기준 판단 아님)
    for _ in range(3):
        bad = outfall_check(out, nodes, links)
        if not bad:
            break
        last = next(l for l in links if nodes[l["dn"]]["kind"] == "outfall")
        if last["up"] in lifts:
            break
        lifts.add(last["up"])
        notes.append("물리적 필요(토구 관저고): %s → %s에 펌프장" % (bad[0], last["up"]))
        out = design(st, nodes, links, sizes, lifts)
    return lifts, out, notes


def hazen_c(st, dia):
    r = st.rule("FORCE_MAIN_FRICTION")
    if r.get("kind") == "project":
        return st.choice[r["key"]], "사업 채택값(%s)" % r.get("text", "")
    rows = [x for x in db.pick(st.rows, r["param"], {**r["cond"], "dia_mm": dia}, allow=tuple(r.get("allow", ())))
            if x.binding != "none"]
    vals = [x.value_min if x.value_min is not None else x.value_max for x in rows]
    c = min(vals) if r.get("pick") == "min" else max(vals)
    return c, rows[0].clause_ref + (" — " + r["resolution"] if r.get("resolution") else "")


def fm_velocity_range(st):
    r = st.rule("FORCE_MAIN_VELOCITY")
    bf = r.get("binding_filter")

    def pick(param, side):
        xs = [x for x in db.pick(st.rows, param, r["cond"], allow=tuple(r.get("allow", ())))
              if x.binding in ((bf,) if bf else ("mandatory", "standard")) and "rule" not in str(x.condition)]
        vals = [getattr(x, side) for x in xs if getattr(x, side) is not None]
        return (max(vals) if side == "value_min" else min(vals)) if vals else None, (xs[0].clause_ref if xs else "")
    vmin, c1 = pick(r["min_param"], "value_min")
    vmax, c2 = pick(r["max_param"], "value_max")
    return vmin, vmax, "%s / %s" % (c1, c2)


def size_station(st, node, Q, Qavg, inv_in, inv_out, sizes, project):
    out = {"node": node, "Q": Q, "Qavg": Qavg, "static_m": inv_out - inv_in, "notes": []}
    # 압송관 관경: 유속 범위를 만족하는 가장 작은 관
    vmin, vmax, vcl = fm_velocity_range(st)
    mr = st.rule("FORCE_MAIN_MIN_DIAMETER")
    dmin = 0
    if mr:
        xs = [x for x in db.pick(st.rows, mr["param"], mr["cond"], allow=tuple(mr.get("allow", ()))) if x.value_min]
        dmin = max((x.value_min for x in xs), default=0)
    pick = None
    for nom, inner in sizes:
        if inner < dmin - 1e-6:
            continue
        v = Q / (math.pi * (inner / 1000) ** 2 / 4)
        if (vmax is None or v <= vmax) and (vmin is None or v >= vmin):
            pick = (nom, inner, v)
            break
    if pick is None:  # 범위를 동시에 만족하는 규격이 없으면 최대유속만 지키는 가장 작은 관
        for nom, inner in sizes:
            v = Q / (math.pi * (inner / 1000) ** 2 / 4)
            if inner >= dmin - 1e-6 and (vmax is None or v <= vmax):
                pick = (nom, inner, v)
                out["notes"].append("최소유속 %.2f m/s 미달(유량 작음) — 설계자 검토" % vmin)
                break
    nom, inner, v = pick
    C, ccl = hazen_c(st, nom)
    Lfm = max(out["static_m"], 0) + project.get("lift_main_extra_m", {}).get("value", 10.0)
    hf = 10.67 * Lfm * Q ** 1.852 / (C ** 1.852 * (inner / 1000) ** 4.87)
    out.update({"fm_dia": nom, "fm_inner": inner, "fm_v": v, "fm_v_range": (vmin, vmax), "fm_clause": vcl, "C": C, "C_clause": ccl,
                "fm_len": Lfm, "hf": hf, "tdh": max(out["static_m"], 0) + hf})
    # 펌프 대수
    pr = st.rule("PUMP_COUNT")
    if not pr:
        out["pumps"] = "규정 없음"
    elif pr["kind"] == "firm_capacity":
        out["pumps"] = "%d대 × %.1f L/s (1대 정지 시 첨두 처리)" % (pr.get("min", 2), Q * 1000)
    elif pr["kind"] == "min_count":
        row = db.one(_rows(st, pr), pr["param"], pr.get("cond", {}))
        n = int(row.value_min)
        out["pumps"] = "%d대 × %.1f L/s (%s %g~%g대, 예비 규정 없음)" % (n, Q / n * 1000, row.clause_ref, row.value_min, row.value_max)
    elif pr["kind"] == "dwf_multiples":
        out["pumps"] = " + ".join("%.1f" % (m * Qavg * 1000) for m in pr["multiples"]) + " L/s (%s)" % pr.get("text", "")
    # 습정 용량
    wr = st.rule("WET_WELL_VOLUME") or {"kind": "review"}
    if wr["kind"] == "fill_time_max":
        row = [x for x in db.pick(st.rows, wr["param"], {}) if x.binding == "mandatory"][0]
        out["wet_well"] = "유효용량 ≤ %.1f m³ (평균유량 충수 ≤ %g분, %s)" % (Qavg * 60 * row.value_max, row.value_max, row.clause_ref)
    elif wr["kind"] == "cycle_formula":
        row = [x for x in db.pick(st.rows, wr["cycle_param"], {}) if x.binding in ("mandatory", "standard")][0]
        T = row.value_min
        out["wet_well"] = "V = T·Q/4 = %.1f m³ (T=%g분, %s)" % (T * 60 * Q / 4, T, wr["clause"])
    elif wr["kind"] == "multiple_of_pumping_rate":
        row = db.one(st.rows, wr["param"], wr["cond"])
        V = row.value_min * 60 * Q
        ret = db.one(st.rows, wr["retention_param"], wr["cond"]).value_max
        t = V / (Qavg * 60) if Qavg else 0
        out["wet_well"] = "V ≥ %.1f m³ (양수량 × %g분), 평균유량 체류 %.1f분 %s %g분 (%s)" % (
            V, row.value_min, t, "≤" if t <= ret else ">", ret, wr["clause"])
    else:
        out["wet_well"] = "판정 보류(설계자 검토): " + wr.get("text", "")
    # 동력
    eff = st.choice.get("pump_efficiency", 0.7)
    out["power_kw"] = RHO_G * Q * out["tdh"] / eff
    return out


def plan(pid, sid, dsn=None):
    dsn = dsn or os.environ["SEWAGE_DB_DSN"]
    project = load_project(pid)
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        nodes, links = load_network(cur, pid)
        cur.execute("SELECT node_id, min_invert_el::float FROM network.node WHERE project_id=%s", (pid,))
        for n, v in cur.fetchall():
            nodes[n]["min_inv"] = v
        st = Standard(sid, project, dsn)
        sizes = st.pipe_sizes(cur)
    fixed = project.get("pump_stations", {}).get("value", [])
    lifts, out, notes = place_lifts(st, nodes, links, sizes, fixed)
    last = next(l for l in links if nodes[l["dn"]]["kind"] == "outfall")
    terminal = last["up"] in lifts and nodes[last["dn"]].get("min_inv") is not None
    if not terminal:
        notes += ["남은 문제: " + m for m in outfall_check(out, nodes, links)]
    order, into = topo(links)
    _, p1 = tributary_pop(order, into, nodes)
    res = {r["link"]: r for r in out}
    stations = []
    for n in sorted(lifts):
        l_out = next(l for l in links if l["up"] == n)
        ins = [res[i["id"]] for i in into.get(n, [])]
        inv_in = min(r["inv_dn"] for r in ins) if ins else res[l_out["id"]]["inv_up"]
        P = p1[l_out["id"]]
        pj = dict(project["standards"].get(sid, {}))
        if terminal and n == last["up"]:  # 토구 직전 펌프장: 압송관으로 지정 관저고까지 직접 송수
            inv_to = nodes[last["dn"]]["min_inv"]
            pj["lift_main_extra_m"] = {"value": last["L"]}
            res[last["id"]]["governing"] = "압송관 (펌프장 %s → 토구 지정 관저고 %.2f m)" % (n, inv_to)
        else:
            inv_to = res[l_out["id"]]["inv_up"]
        stations.append(size_station(st, n, st.peak_flow(P), st.avg_flow(P), inv_in, inv_to, sizes, pj))
    return {"standard_id": sid, "lifts": sorted(lifts), "notes": notes, "stations": stations, "summary": summarize(out)}


def main(pid):
    project = load_project(pid)
    for sid in project["standards"]:
        p = plan(pid, sid)
        print("\n== %s | 펌프장 %s | 최대 매설 %.2f m" % (sid, p["lifts"] or "없음", p["summary"]["max_depth_m"]))
        for n in p["notes"]:
            print("   ·", n)
        for s in p["stations"]:
            print("   [%s] Q %.1f L/s, 실양정 %.2f m, 압송관 %d(내경 %.0f) v=%.2f m/s (범위 %s~%s, %s), C=%g, 전양정 %.2f m, 동력 %.1f kW"
                  % (s["node"], s["Q"] * 1000, s["static_m"], s["fm_dia"], s["fm_inner"], s["fm_v"], s["fm_v_range"][0],
                     s["fm_v_range"][1], s["fm_clause"], s["C"], s["tdh"], s["power_kw"]))
            print("        펌프: %s | 습정: %s %s" % (s["pumps"], s["wet_well"], "; ".join(s["notes"])))


if __name__ == "__main__":
    main(sys.argv[1])
