"""하수처리장(표준활성슬러지법) 원문 기준 설계 — 규칙 유형 PLANT_FLOW·INFLUENT_LOAD·PRIMARY_CLARIFIER·AERATION_TANK·
SECONDARY_CLARIFIER·EFFLUENT_LIMIT (v7, 2026-11-07).

흐름: 관망 말단 인구 → 기준별 처리장 유량(평균·최대일·시간최대·월최대) → 유입 부하 → 일차침전지 → 반응조 → 이차침전지
→ 처리수 수질 추정 → 방류수질 법령 판정.
원칙
- 값은 기준값 행에서만. 원문 수치가 없는 항목은 사업 채택값(criteria/projects)이 있으면 쓰고, 없으면 그 판정만 보류한다.
- 크기는 '모든 기준을 만족하는 최소 제원': 부하율 상한 → 최소 면적, 체류시간 하한 → 최소 용적, 수심은 범위 하한.
  그렇게 정한 제원으로 실제 부하율·체류시간을 다시 계산해 범위 안인지 판정한다(하한 미달도 표시).
- 상태값(MLSS·SRT·반송비)은 설계자가 정하는 값이라 사업 채택값, 없으면 범위 중앙(design: mid).
- 제거율이 범위면 규칙의 design(min/max)을 따른다(예: 최소 효율 범위 → 하한).
- 같은 조건에 의무·기준 행과 권장(guide) 행이 함께 있으면 의무·기준을 쓴다. 권장 행만 있으면 권장값을 쓰고 표시한다.
사용: py -3 -m engine.plant SYN01 [--population N] [--csv]
"""
import argparse
import csv
import json
import os
import re

from engine import criteria_db as db
from engine.generic import ROOT, Standard

REQ = ("mandatory", "standard")
USE = ("mandatory", "standard", "guide")
EPS = 1e-9


class Held(Exception):
    """원문에 수치가 없어 이 판정은 보류."""


# ── 기준값 고르기 ──
def pick(st, s, rows=None):
    rows = rows if rows is not None else (st.flow_rows if s.get("standard") == "flow" else st.plant_rows)
    cond = s.get("cond", {})
    got = [r for r in db.pick(rows, s["param"], cond, allow=tuple(s.get("allow", ())))
           if r.binding in USE and (r.value_min is not None or r.value_max is not None)]
    if not got:
        raise Held("%s %s 수치 없음" % (s["param"], cond or ""))
    best = max(sum(k in r.condition for k in cond) for r in got)  # 조건 키를 가장 많이 가진 행(가장 구체적인 행)
    got = [r for r in got if sum(k in r.condition for k in cond) == best]
    req = [r for r in got if r.binding in REQ]
    got = req or got
    if len(got) != 1:
        raise LookupError("%s %s → %d행: %s" % (s["param"], cond, len(got), [(g.condition, g.clause_ref) for g in got]))
    return got[0]


def value(st, s, how=None, rows=None):
    """설계에 쓰는 한 값과 출처. s가 사업 채택값이면 그 값, 아니면 행의 범위에서 how(min/max/mid)."""
    if s is None:
        raise Held("규정 없음")
    if s.get("source") == "project":
        if s["key"] not in st.choice:
            raise Held("원문 수치 없음, 사업 채택값(%s) 미입력" % s["key"])
        return st.choice[s["key"]], {"src": "사업 채택값 %s" % s["key"]}
    r = pick(st, s, rows)
    how = s.get("design") or how or "mid"
    lo, hi = r.value_min, r.value_max
    v = {"min": lo if lo is not None else hi, "max": hi if hi is not None else lo,
         "mid": (lo + hi) / 2 if lo is not None and hi is not None else (lo if lo is not None else hi)}[how]
    key = s.get("key")
    if key and key in st.choice:  # 범위 안의 설계값을 사업 파일이 정한 경우
        v = st._choice(key, r)
    return v, src(r, how)


def src(r, how=None):
    return {"clause": r.clause_ref, "binding": r.binding, "range": [r.value_min, r.value_max], **({"how": how} if how else {})}


def bounds(row, upper_only=True):
    """판정 범위. 단일값(하한=상한)은 상한으로 본다 — 부하율·F/M의 단일값은 넘지 말아야 할 값(예: 열대 조건 최고값)."""
    lo, hi = row.value_min, row.value_max
    if upper_only and lo is not None and hi is not None and abs(lo - hi) < EPS:
        return None, hi
    return lo, hi


def when_ok(s, env):
    return "when" not in s or eval(s["when"], {"__builtins__": {}}, env)


# ── 유량 ──
def factor_interp(st, param, x):
    """평균유량 x(L/s)에 따른 첨두계수 — 표의 점(≤a, =b, >c) 사이 선형보간, 바깥은 끝값."""
    pts = []
    for r in db.pick(st.plant_rows, param, {}, allow=()):
        spec = r.condition.get("mean_flow_lps", {})
        k = next(iter(spec))
        pts.append((spec[k], r.value_min, r.clause_ref))
    pts.sort()
    if x <= pts[0][0]:
        return pts[0][1], pts[0][2]
    if x >= pts[-1][0]:
        return pts[-1][1], pts[-1][2]
    for (x0, y0, c), (x1, y1, _) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0), c


def flows(st, P):
    r = st.rule("PLANT_FLOW")
    F, info = {}, {}
    order = sorted(r["flows"], key=lambda k: 0 if r["flows"][k]["kind"] in ("sewer_no_peak", "sewer_peak") else 1)
    for k in order:
        f = r["flows"][k]
        if f["kind"] == "sewer_no_peak":
            F[k] = st.peak_flow(P, peak=False) * 86400
        elif f["kind"] == "sewer_peak":
            F[k] = st.peak_flow(P) * 86400
        elif f["kind"] == "ratio":
            row = db.one(st.flow_rows if f.get("standard") == "flow" else st.plant_rows, f["param"], {})
            F[k] = F[f["of"]] * st._choice(f["key"], row)
        elif f["kind"] == "factor_table":
            pf, c = factor_interp(st, f["param"], F[f["of"]] / 86.4)
            F[k] = F[f["of"]] * pf
            f = {**f, "clause": "%s 계수 %.2f" % (c, pf)}
        elif f["kind"] == "none":
            info[k] = "보류: " + f["why"]
            continue
        info[k] = f.get("clause", "")
    sp = r.get("small_plant")
    if sp and "average" in F:
        row = pick(st, sp)
        if F["average"] * row.value_min / 86.4 <= sp["max_lps"] + EPS:  # 설계유량(평균×계수)이 상한 이하인 소규모
            for k in [x for x in F if x != "average"] + [x for x in ("max_daily", "peak_hourly", "max_monthly") if x not in F]:
                F[k] = F["average"] * row.value_min
                info[k] = sp["clause"]
    return F, info


# ── 침전지 공통 ──
def clarifier(st, r, F, X=None, Qr=None):
    """최소 면적 = max(유량/부하율 상한, 유량×체류시간 하한/수심, (유량+반송)×MLSS/고형물부하 상한)."""
    env = {**F, "average_lps": F.get("average", 0) / 86.4}
    out = {"checks": [], "held": []}
    try:
        drow = pick(st, r["depth"])
        dlo, dhi = drow.value_min, drow.value_max
        dlo = dlo if dlo is not None else dhi
        out["depth_src"] = src(drow)
    except Held as e:
        dlo = dhi = None
        out["held"].append("수심: %s" % e)
    need, vol = [], []
    items = []
    for kind in ("loading", "solids", "time"):
        for s in r.get(kind, []):
            if not when_ok(s, env):
                continue
            Q = F.get(s["flow"])
            if Q is None:
                out["held"].append("%s(%s): %s 유량 정의 없음" % (s["param"], s["flow"], s["flow"]))
                continue
            try:
                row = pick(st, s)
            except Held as e:
                out["held"].append(str(e))
                continue
            lim = row.value_min if s.get("limit") == "min" else (row.value_max if row.value_max is not None else row.value_min)
            if kind == "loading":
                need.append(Q / lim)
            elif kind == "solids":
                if X is None or Qr is None:
                    out["held"].append("%s: MLSS 또는 반송비 없음" % s["param"])
                    continue
                q_r = Qr[s.get("return", "design")]
                need.append((Q + q_r) * X / 1000 / lim)
            else:  # 체류시간 하한 → 최소 용적
                if dlo is None or row.value_min is None:
                    continue
                vol.append(Q * row.value_min / 24)
            items.append((kind, s, row, Q))
    if not need and not (vol and dlo):
        out["held"].append("면적을 정할 기준 없음")
        return out
    # 면적은 부하율로, 수심은 범위 안에서 체류시간 용적을 채우도록. 수심 상한으로도 모자라면 면적을 키운다.
    V = max(vol, default=0.0)
    A = max(need, default=0.0)
    if dlo is None:
        d = None
    elif A <= 0:
        d, A = (dhi or dlo), V / (dhi or dlo)
    else:
        d = max(dlo, V / A)
        if dhi is not None and d > dhi + EPS:
            d, A = dhi, V / dhi
    out["area_m2"], out["depth_m"] = A, d
    out["volume_m3"] = A * d if d else None
    for kind, s, row, Q in items:
        if kind == "loading":
            x, unit = Q / A, "m3/m2/d"
        elif kind == "solids":
            x, unit = (Q + Qr[s.get("return", "design")]) * X / 1000 / A, "kg/m2/d"
        else:
            x, unit = A * d / Q * 24, "h"
        lo, hi = bounds(row)
        if s.get("limit") == "min":
            hi, lo = row.value_min, None
        ok =(lo is None or x >= lo - EPS) and (hi is None or x <= hi + EPS)
        out["checks"].append({**src(row), "item": s["param"], "flow": s["flow"], "value": x, "unit": unit, "range": [lo, hi], "ok": ok,
                              "note": "" if ok else ("범위 하한 미달" if lo is not None and x < lo else "상한 초과")})
    for s in r.get("weir", []):
        if when_ok(s, env) and s["flow"] in F:
            try:
                row = pick(st, s)
                out["weir_length_m"] = F[s["flow"]] / (row.value_max or row.value_min)
                out["weir_src"] = src(row)
            except Held as e:
                out["held"].append(str(e))
    n = 1
    for s in r.get("count", []):
        if when_ok(s, env):
            try:
                n = max(n, int(pick(st, s).value_min or 1))
            except Held:
                pass
    out["count"] = n
    return out


def removal(st, s, out, name):
    try:
        v, sr = value(st, s, "min")
        out[name] = {"value": v, **sr}
        return v
    except Held as e:
        out.setdefault("held", []).append("%s: %s" % (name, e))
        return None


# ── 방류수질 ──
NUM = re.compile(r"[-+]?\d[\d.,]*")


def _num(s):
    m = NUM.search(s or "")
    if not m:
        return None
    t = m.group(0)
    t = t.replace(".", "").replace(",", ".") if re.fullmatch(r"\d{1,3}(\.\d{3})*(,\d+)?", t) and "," in t else t.replace(",", "")
    return float(t)


def in_band(spec, x):
    """'>=10000' '500~<10000' '<50' '>625 y <=3000' '<=625' 같은 원문 구간 표기."""
    spec = spec.replace(" ", "")
    m = re.fullmatch(r"([\d.]+)~<([\d.]+)", spec)
    if m:
        return float(m.group(1)) <= x < float(m.group(2))
    for part in re.split(r"y", spec):
        m = re.fullmatch(r"(>=|<=|>|<)([\d.]+)", part)
        if not m:
            raise ValueError("구간 표기 해석 불가: %s" % spec)
        op, v = m.group(1), float(m.group(2))
        if not {">=": x >= v, "<=": x <= v, ">": x > v, "<": x < v}[op]:
            return False
    return True


def effluent_limits(st, env):
    r = st.rule("EFFLUENT_LIMIT")
    if not r:
        return None
    rows = [x for x in csv.DictReader(open(ROOT / "criteria" / "effluent_limits.csv", encoding="utf-8-sig")) if x["country"] == r["country"]]
    groups = {}
    for x in rows:
        c = json.loads(x["condition"]) if x["condition"].strip() else {}
        if any(c.get(k) != v for k, v in r.get("match", {}).items()):
            continue
        if any(not str(c.get(k, "")).startswith(v) for k, v in r.get("match_prefix", {}).items()):
            continue
        if any(v not in str(c.get(k, "")) for k, v in r.get("match_contains", {}).items()):
            continue
        if "averaging" in r and not re.search(r["averaging"], x["averaging"]):
            continue
        if not x["unit"].lower().startswith("mg/l"):
            continue
        cap = r.get("capacity")
        if cap and cap["key"] in c and not in_band(c[cap["key"]], env[cap["from"]]):
            continue
        for p, pat in r["params"].items():
            if re.search(pat, x["parameter"]):
                g = c.get(r["group"], "") if r.get("group") else ""
                groups.setdefault(g, {})[p] = {"limit": _num(x["value_max"]), "law": x["law"], "article": x["article"]}
    return groups


# ── 처리장 전체 ──
def plant_design(st, P):
    F, finfo = flows(st, P)
    res = {"population": P, "flows_m3d": F, "flows_src": finfo, "held": []}
    il = st.rule("INFLUENT_LOAD")
    load = {}
    for p in ("bod", "ss"):
        try:
            v, sr = value(st, il[p], "mid")
            load[p] = v * P  # kg/d
            res["%s_per_capita_kg" % p] = {"value": v, **sr}
        except Held as e:
            res["held"].append("유입 %s: %s" % (p.upper(), e))
    Qc = F[il["concentration_flow"]]
    conc = {p: load[p] / Qc * 1000 for p in load}  # mg/L
    res["influent_mgL"], res["influent_kgd"] = conc, load

    pr = st.rule("PRIMARY_CLARIFIER")
    prim = clarifier(st, pr, F)
    rb = removal(st, pr.get("bod_removal"), prim, "bod_removal")
    rs = removal(st, pr.get("ss_removal"), prim, "ss_removal")
    res["primary"] = prim
    S1 = conc["bod"] * (1 - rb) if "bod" in conc and rb is not None else None  # 반응조 유입 BOD
    SS1 = conc["ss"] * (1 - rs) if "ss" in conc and rs is not None else None

    ar = st.rule("AERATION_TANK")
    aer = {"held": []}
    Q = F.get(ar["flow"])
    aer["flow"] = ar["flow"]
    X = Xv = None
    for key in ("mlss", "mlvss"):
        if key in ar:
            try:
                v, sr = value(st, ar[key], "mid")
                aer[key] = {"value": v, **sr}
            except Held as e:
                aer["held"].append("%s: %s" % (key, e))
    X = aer.get("mlss", {}).get("value")
    Xv = aer.get("mlvss", {}).get("value")
    if Xv is None and X is not None and "mlvss_ratio" in ar:
        try:
            Xv = X * value(st, ar["mlvss_ratio"], "mid")[0]
        except Held:
            pass
    need = []
    if Q is None:
        aer["held"].append("%s 유량 정의 없음" % ar["flow"])
    else:
        if "hrt" in ar:
            row = pick(st, ar["hrt"])
            need.append(("HRT 하한", Q * row.value_min / 24, row))
        if "lv" in ar:
            row = pick(st, ar["lv"])
            if S1 is None:
                aer["held"].append("BOD 용적부하: 반응조 유입 BOD 없음")
            else:
                need.append(("BOD 용적부하 상한", Q * S1 / 1000 / (row.value_max or row.value_min), row))
        if "fm" in ar:
            row = pick(st, ar["fm"])
            Xb = Xv if ar["fm"].get("basis") == "mlvss" else X
            if S1 is None or Xb is None:
                aer["held"].append("F/M: %s" % ("반응조 유입 BOD 없음" if S1 is None else "%s 없음" % ar["fm"].get("basis", "mlss").upper()))
            else:
                need.append(("F/M 상한", Q * S1 / ((row.value_max or row.value_min) * Xb), row))
    if need:
        name, V, row = max(need, key=lambda t: t[1])
        aer["volume_m3"], aer["governing"] = V, "%s (%s)" % (name, row.clause_ref)
        aer["hrt_h"] = V / Q * 24
        if S1 is not None:
            aer["lv_kgm3d"] = Q * S1 / 1000 / V
            Xb = Xv if ar.get("fm", {}).get("basis") == "mlvss" else X
            if Xb:
                aer["fm"] = Q * S1 / (V * Xb)
        aer["checks"] = []
        for label, k, s in (("HRT", "hrt_h", ar.get("hrt")), ("BOD 용적부하", "lv_kgm3d", ar.get("lv")), ("F/M", "fm", ar.get("fm"))):
            if s and k in aer:
                row = pick(st, s)
                lo, hi = bounds(row)
                ok = (lo is None or aer[k] >= lo - EPS) and (hi is None or aer[k] <= hi + EPS)
                aer["checks"].append({**src(row), "item": label, "value": aer[k], "range": [lo, hi], "ok": ok,
                                      "note": "" if ok else ("범위 하한 미달" if lo is not None and aer[k] < lo else "상한 초과")})
    elif Q is not None:
        aer["held"].append("용적을 정할 기준 없음")
    ra = removal(st, ar.get("bod_removal"), aer, "bod_removal")
    rsa = removal(st, ar.get("ss_removal"), aer, "ss_removal")
    S = S1 * (1 - ra) if S1 is not None and ra is not None else None
    # 상태값
    for key in ("srt", "return"):
        if key in ar:
            try:
                v, sr = value(st, ar[key], "mid")
                aer[key] = {"value": v, **sr}
            except Held as e:
                aer["held"].append("%s: %s" % (key, e))
    # 잉여슬러지 (Yobs = Y/(1+kd·θc), A = Q·Yobs·(S0−S), 잉여 = A/계수)
    if "sludge" in ar:
        try:
            Y = value(st, ar["yield"])[0]
            kd = value(st, ar["decay"])[0]
            th = aer["srt"]["value"]
            div = value(st, ar["sludge"]["divisor"])[0]
            if S is None:
                raise Held("처리수 BOD 없음")
            yobs = Y / (1 + kd * th)
            aer["sludge_kgd"] = Q * yobs * (S1 - S) / 1000 / div
            aer["yobs"] = yobs
        except (Held, KeyError) as e:
            aer["held"].append("잉여슬러지: %s" % e)
    # 필요산소량
    ox = ar.get("oxygen")
    if ox:
        try:
            k, sr = value(st, ox, ox.get("design", "max"))
            if S1 is None:
                raise Held("반응조 유입 BOD 없음")
            if ox["kind"] == "per_bod_removed":
                if S is None:
                    raise Held("처리수 BOD 없음")
                aer["oxygen_kgd"] = k * Q * (S1 - S) / 1000
            else:  # 부하 기준(첨두시간 등) — 유입 농도 일정 가정
                aer["oxygen_kgd"] = k * F[ox["load_flow"]] * S1 / 1000
            aer["oxygen_src"] = sr
        except Held as e:
            aer["held"].append("필요산소량: %s" % e)
    res["aeration"] = aer

    sr_ = st.rule("SECONDARY_CLARIFIER")
    Rd = aer.get("return", {})
    Qr = None
    if Rd:
        Qr = {"design": Rd["value"] * F["average"], "max": (Rd["range"][1] if Rd.get("range") and Rd["range"][1] is not None else Rd["value"]) * F["average"]}
    res["secondary"] = clarifier(st, sr_, F, X=X, Qr=Qr)

    # 처리수 수질 추정
    eff = {"bod": S, "ss": SS1 * (1 - rsa) if SS1 is not None and rsa is not None else None}
    res["effluent_mgL"] = eff
    env = {**F, "bod_load_kg_d": load.get("bod", 0)}
    lim = effluent_limits(st, env)
    if lim is not None:
        judge = {}
        for g, ps in lim.items():
            judge[g or "-"] = {p: {**v, "estimate": eff.get(p),
                                   "ok": None if eff.get(p) is None else eff[p] <= v["limit"] + EPS} for p, v in ps.items()}
        res["effluent_judgement"] = judge
    for part in ("primary", "aeration", "secondary"):
        res["held"] += ["%s: %s" % (part, h) for h in res[part].get("held", [])]
    return res


def summary(res):
    a = res["aeration"]
    return {"Q_avg": round(res["flows_m3d"].get("average", 0)), "Q_design_aeration": a["flow"],
            "primary_area_m2": round(res["primary"].get("area_m2", 0) or 0, 1),
            "aeration_volume_m3": round(a.get("volume_m3", 0) or 0), "secondary_area_m2": round(res["secondary"].get("area_m2", 0) or 0, 1),
            "effluent_bod_mgL": None if res["effluent_mgL"]["bod"] is None else round(res["effluent_mgL"]["bod"], 1),
            "held": len(res["held"])}


def total_population(pid):
    import psycopg
    from engine.network import load_network
    with psycopg.connect(os.environ["SEWAGE_DB_DSN"]) as con, con.cursor() as cur:
        nodes, _ = load_network(cur, pid)
    return sum(n["p1"] for n in nodes.values())


def run(pid, standards=None, population=None):
    from engine.design import load_project
    project = load_project(pid)
    P = population if population is not None else total_population(pid)
    out = {}
    for sid in standards or list(project["standards"]):
        st = Standard(sid, project)
        if st.rule("PLANT_FLOW"):
            out[sid] = plant_design(st, P)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--standards", nargs="*")
    ap.add_argument("--population", type=float)
    ap.add_argument("--csv", action="store_true", help="기준값을 DB 대신 공개 CSV에서 읽기")
    a = ap.parse_args()
    if a.csv:
        from engine import csv_rows
        csv_rows.use_csv()
    for sid, r in run(a.project, a.standards, a.population).items():
        print(sid, summary(r))
        for h in r["held"]:
            print("   보류:", h)


if __name__ == "__main__":
    main()
