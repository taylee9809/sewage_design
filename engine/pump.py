"""펌프장·압송관 (원문 기준) — 규칙 유형 PUMP_TRIGGER·FORCE_MAIN_*·PUMP_COUNT·WET_WELL_VOLUME·PUMP_HEAD_POWER.

흐름: 자연유하 설계 → 전환 조건 판정 → 펌프장(인라인 양수장) 위치 → 하류 재설계 → 펌프장별 흡입수위·압송관·부속손실·대수·흡입관·잠김·습정·양정·동력.
추가 유형: WET_WELL_LEVEL·MINOR_LOSS·SUCTION_PIPE·PUMP_SUBMERGENCE_NPSH — 원문 수치 없으면 판정 보류. 부속 구성은 사업 파일 station_fittings(펌프장별).
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


def wet_well_level(st, inlet):
    """흡입(운전 저)수위. 반환 (수위, 설명, 판정 보류 여부). inlet = 유입관 {inv, D, S, Qavg}."""
    r = st.rule("WET_WELL_LEVEL") or {"kind": "review", "text": "규정 없음"}
    if r["kind"] == "inlet_flow_level":
        row = db.one(_rows(st, r), r["param"], r["cond"], allow=tuple(r.get("allow", ())))
        yr = h.depth_ratio_for_flow(inlet["D"], inlet["S"], st.n, inlet["Qavg"]) if inlet["Qavg"] > 0 else 0.0
        y = (yr or 1.0) * inlet["D"]
        return inlet["inv"] + y, "유입관저 + 일평균 수심 %.3f m (%s)" % (y, row.clause_ref), False
    if r["kind"] == "below_inlet_invert":
        xs = db.pick(_rows(st, r), r["param"], r["cond"], allow=tuple(r.get("allow", ())))
        row = xs[0]
        d = row.value_max if r.get("pick") == "max" and row.value_max is not None else row.value_min
        return inlet["inv"] - d, "유입관저 − %.1f m (%s %g~%g m %s)" % (d, row.clause_ref, row.value_min, row.value_max, row.binding), False
    return inlet["inv"], "판정 보류(설계자 검토): %s — 실양정은 유입관저 기준(가정)" % r.get("text", ""), True


def unit_flow(st, Q, Qavg):
    """펌프 1대 양수량과 대수 설명."""
    pr = st.rule("PUMP_COUNT")
    if not pr:
        return Q, "규정 없음"
    if pr["kind"] == "firm_capacity":
        return Q, "%d대 × %.1f L/s (1대 정지 시 첨두 처리)" % (pr.get("min", 2), Q * 1000)
    if pr["kind"] == "min_count":
        row = db.one(_rows(st, pr), pr["param"], pr.get("cond", {}))
        n = int(row.value_min)
        return Q / n, "%d대 × %.1f L/s (%s %g~%g대, 예비 규정 없음)" % (n, Q / n * 1000, row.clause_ref, row.value_min, row.value_max)
    if pr["kind"] == "dwf_multiples":
        return max(pr["multiples"]) * Qavg, " + ".join("%.1f" % (m * Qavg * 1000) for m in pr["multiples"]) + " L/s (%s)" % pr.get("text", "")
    return Q, "규정 없음"


def minor_loss(st, v, fittings):
    """부속·속도수두 손실 (m)과 설명. 부속 구성은 펌프장별 사업 입력."""
    r = st.rule("MINOR_LOSS") or {"kind": "review", "text": "규정 없음"}
    hv = v * v / (2 * 9.81)
    if r["kind"] == "c_includes_bends":
        if r.get("exit_velocity_head"):
            return hv, "C에 굴곡손실 포함 + 토출 잔류속도수두 %.3f m (%s)" % (hv, r["clause"])
        return 0.0, "C에 굴곡손실 포함 (%s)" % r["clause"]
    if r["kind"] == "k_table":
        if not fittings:
            return 0.0, "판정 보류(설계자 검토): 부속 구성 입력 없음 — %s" % r["clause"]
        K, missing = 0.0, []
        for item, cnt in fittings.items():
            xs = db.pick(_rows(st, r), r["param"], {**r["cond"], "item": item}, allow=tuple(r.get("allow", ())))
            if xs:
                K += xs[0].value_min * cnt
            else:
                missing.append(item)
        hm = K * hv + (hv if r.get("velocity_head") else 0.0)
        msg = "ΣK %.2f × v²/2g%s = %.3f m (%s)" % (K, " + 속도수두" if r.get("velocity_head") else "", hm, xs[0].clause_ref if xs else "")
        if missing:
            msg += "; 표에 없는 부속 %s → 판정 보류" % missing
        return hm, msg
    return 0.0, "판정 보류(설계자 검토): %s" % r.get("text", "")


def suction_pipe(st, q_unit):
    """흡입관경 범위 (mm) 설명과 최대 흡입관경(잠김 계산용)."""
    r = st.rule("SUCTION_PIPE") or {"kind": "review", "text": "규정 없음"}
    if r["kind"] == "formula_velocity":
        row = db.one(_rows(st, r), r["param"], r["cond"])
        qm = q_unit * 60
        d1, d2 = (r["coef"] * math.sqrt(qm / v) for v in (row.value_max, row.value_min))
        return d2, "흡입관경 %.0f~%.0f mm (V %g~%g m/s, %s)" % (d1, d2, row.value_min, row.value_max, r["clause"])
    if r["kind"] == "velocity_range":
        row = db.one(_rows(st, r), r["param"], r["cond"], allow=tuple(r.get("allow", ())))
        d1, d2 = (math.sqrt(4 * q_unit / (math.pi * v)) * 1000 for v in (row.value_max, row.value_min))
        return d2, "흡입관경 %.0f~%.0f mm (V %g~%g m/s, %s)" % (d1, d2, row.value_min, row.value_max, r["clause"])
    if r["kind"] == "min_opening":
        row = db.one(_rows(st, r), r["param"], r["cond"], allow=tuple(r.get("allow", ())))
        return None, "흡입·토출구 ≥ %.0f mm (%s)" % (row.value_min, r["clause"])
    return None, "판정 보류(설계자 검토): %s" % r.get("text", "")


def submergence_npsh(st, lwl, d_suction, project):
    r = st.rule("PUMP_SUBMERGENCE_NPSH") or {"kind": "review", "text": "규정 없음"}
    if r["kind"] == "submergence_above_pump":
        row = db.one(_rows(st, r), r["param"], r["cond"], allow=tuple(r.get("allow", ())))
        msg = "수중펌프 상단 ≤ %.2f m (저수위 − %.1f m, %s)" % (lwl - row.value_min, row.value_min, row.clause_ref)
    elif r["kind"] == "submergence_ratio":
        row = db.one(_rows(st, r), r["param"], r["cond"], allow=tuple(r.get("allow", ())))
        msg = ("흡입구 잠김 ≥ %.2f m (%g × 흡입관경 %.0f mm, %s)" % (row.value_min * d_suction / 1000, row.value_min, d_suction, row.clause_ref)
               if d_suction else "잠김 %g × 흡입관경 — 흡입관경 미정" % row.value_min)
    else:
        return "판정 보류(설계자 검토): %s" % r.get("text", "")
    if r.get("npsh"):
        npshr = project.get("npsh_required_m", {}).get("value")
        msg += "; NPSH " + ("NPSHr %.2f m 입력 — 흡입측 손실 산정 후 검토" % npshr if npshr else "판정 보류(%s)" % r["npsh"])
    return msg


def size_station(st, node, Q, Qavg, inlet, inv_out, sizes, project, fittings=None):
    lwl, lwl_msg, held = wet_well_level(st, inlet)
    out = {"node": node, "Q": Q, "Qavg": Qavg, "lwl": lwl, "lwl_note": lwl_msg, "lwl_held": held,
           "static_m": inv_out - lwl, "notes": []}
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
                "fm_len": Lfm, "hf": hf})
    hm, hm_msg = minor_loss(st, v, fittings)
    out.update({"hm": hm, "hm_note": hm_msg, "tdh": max(out["static_m"], 0) + hf + hm})
    # 펌프 대수·1대 양수량, 흡입관, 잠김·NPSH
    q_unit, out["pumps"] = unit_flow(st, Q, Qavg)
    d_suc, out["suction"] = suction_pipe(st, q_unit)
    out["submergence"] = submergence_npsh(st, lwl, d_suc, project)
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
        if ins:  # 가장 낮게 들어오는 유입관
            r_in = min(ins, key=lambda r: r["inv_dn"])
            inlet = {"inv": r_in["inv_dn"], "D": r_in["D"], "S": r_in["S"], "Qavg": st.avg_flow(p1[r_in["link"]])}
        else:
            r_out = res[l_out["id"]]
            inlet = {"inv": r_out["inv_up"], "D": r_out["D"], "S": r_out["S"], "Qavg": 0.0}
        P = p1[l_out["id"]]
        fits = project.get("station_fittings", {}).get("value", {})
        fits = fits.get(n, fits.get("*"))
        pj = dict(project["standards"].get(sid, {}))
        if terminal and n == last["up"]:  # 토구 직전 펌프장: 압송관으로 지정 관저고까지 직접 송수
            inv_to = nodes[last["dn"]]["min_inv"]
            pj["lift_main_extra_m"] = {"value": last["L"]}
            res[last["id"]]["governing"] = "압송관 (펌프장 %s → 토구 지정 관저고 %.2f m)" % (n, inv_to)
        else:
            inv_to = res[l_out["id"]]["inv_up"]
        stations.append(size_station(st, n, st.peak_flow(P), st.avg_flow(P), inlet, inv_to, sizes, pj, fits))
    return {"standard_id": sid, "lifts": sorted(lifts), "notes": notes, "stations": stations, "summary": summarize(out)}


def main(pid):
    project = load_project(pid)
    for sid in project["standards"]:
        p = plan(pid, sid)
        print("\n== %s | 펌프장 %s | 최대 매설 %.2f m" % (sid, p["lifts"] or "없음", p["summary"]["max_depth_m"]))
        for n in p["notes"]:
            print("   ·", n)
        for s in p["stations"]:
            print("   [%s] Q %.1f L/s, 흡입수위 %.2f m (%s), 실양정 %.2f m" % (s["node"], s["Q"] * 1000, s["lwl"], s["lwl_note"], s["static_m"]))
            print("        압송관 %d(내경 %.0f) v=%.2f m/s (범위 %s~%s, %s), C=%g, 마찰 %.2f m, 부속 %.3f m (%s)"
                  % (s["fm_dia"], s["fm_inner"], s["fm_v"], s["fm_v_range"][0], s["fm_v_range"][1], s["fm_clause"], s["C"], s["hf"],
                     s["hm"], s["hm_note"]))
            print("        전양정 %.2f m, 동력 %.1f kW | %s | %s" % (s["tdh"], s["power_kw"], s["suction"], s["submergence"]))
            print("        펌프: %s | 습정: %s %s" % (s["pumps"], s["wet_well"], "; ".join(s["notes"])))


if __name__ == "__main__":
    main(sys.argv[1])
