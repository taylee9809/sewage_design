"""검토 모드: 정해진 관로·펌프장(기존 시설 또는 신설 설계안)이 기준과 채택 실무값을 만족하는지 판정한다.

설계 엔진(design.py)은 관경·경사를 정하고, 검토 모드는 관경·경사·유량을 받아 판정만 한다. 판정 방식이 같으므로
당초/변경(유량 증가) 비교에도, 신설 설계안 검증에도 쓴다 — 시나리오 이름과 개수는 검토 파일이 정한다.

입력: 검토 파일(JSON) — 기준(standard_id), 시나리오, 채택값(adopt), 자연유하 구간(sections), 펌프장(stations).
기준값은 DB 없이 criteria/*_sewer.csv에서 읽는다(criteria_db.load_csv).
채택값(adopt)은 원문에 수치가 없거나 범위만 있는 항목에서 사업이 정한 값이다. 항상 근거(rationale, 근거 기준)를
함께 적고, 보고서에서 기준값과 따로 표시한다.

자연유하관 (관마다, 시나리오마다)
- 사용률 = 실유량(시간최대 누가유량) ÷ 만관유량(Manning). 한도는 기준 CAPACITY 규칙(만류면 100%),
  adopt.capacity_margin이 있으면 1/(1+여유율)
- 유속은 기준 VELOCITY_MIN/MAX 규칙이 정한 수리상태(설계수심·만관·실수심)에서 본다. 실수심 유속은 참고로 함께 낸다
- 판정: 사용률 초과·최대유속 초과 → NG / 최소유속 미달 → adopt.low_velocity가 있으면 그 분류(예: 지속관리 구간), 없으면 NG
- 구간의 지배관 = 그 시나리오에서 사용률이 가장 큰 관

펌프장 (시나리오마다)
- 용량: 정격 토출량 > 시간최대 유입량 (흡수정 월류 방지)
- 기동횟수: Q* = min(Qh, q/2), N = 60 / (V/Q* + V/(q−Q*)) ≤ adopt.pump_starts_per_hour (채택값 없으면 판정 보류)
- 양정: 실양정(압송관 최고 관저고 − LWL) + Hazen-Williams 손실 + 부속손실 ≤ 설치양정 (펌프 정격 기준이라 유입량과 무관)

사용: py -3 -m engine.check <검토 파일.json> [출력.md]
"""
import json
import math
import sys
from pathlib import Path

from engine import criteria_db as db
from engine import hydraulics as h

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("mandatory", "standard")
DAY = 86400.0
G = 9.81
STATE_KO = {"design_depth": "설계수심", "full": "만관", "actual": "실수심"}
DOC_KO = {"law": "법령", "regulation": "고시·규정", "design_standard": "설계기준", "guideline": "지침",
          "legacy_commentary": "구 기준 해설", "local_study": "지자체 연구", "paper": "논문"}


class Criteria:
    """검토에 쓰는 기준 규칙·기준값·채택값."""

    def __init__(self, case):
        self.sid = case["standard_id"]
        dt = db.doc_type(self.sid)
        if dt not in db.JUDGING_DOC_TYPES:
            raise ValueError("%s는 %s(%s) — 판정 기준은 %s만, 실무 근거는 adopt로" % (
                self.sid, DOC_KO.get(dt, dt), dt, "/".join(db.JUDGING_DOC_TYPES)))
        self.spec = json.loads((ROOT / "criteria" / "rules" / ("%s.json" % self.sid)).read_text(encoding="utf-8"))
        self.rows = db.load_csv(self.sid)
        self.adopt = case.get("adopt", {})
        self.system = case.get("system", "separate")
        self.regulations = case.get("regulations", [])  # 구속력 있는 규정(law·regulation) — 채택값과 대조
        self.area = case.get("area", {})  # 규정 적용범위 판단용 지역 조건 (예: flood_risk_area: true/false/null=미확인)
        self.by_type = {}
        for r in self.spec["rules"]:
            self.by_type.setdefault(r["type"], []).append(r)
        self._other = {}

    def rule(self, t):
        got = self.by_type.get(t, [])
        return got[0] if got else None

    def other_rows(self, sid):
        if sid not in self._other:
            self._other[sid] = db.load_csv(sid)
        return self._other[sid]

    def manning_n(self, material):
        got = [x for x in db.pick(self.rows, "manning_n", {"material": material, "shape": "circular"})
               if x.binding in REQUIRED] if material else []
        if got:
            return got[0].value_min, "%s %s" % (self.sid, got[0].clause_ref)
        a = self.adopt.get("manning_n")
        if a:
            return a["value"], "채택: " + a["rationale"]
        raise LookupError("조도계수 없음: 재질 %r — 기준에 행이 없으면 adopt.manning_n 필요" % material)

    def design_depth(self):
        r = self.rule("CAPACITY")
        if r and r["kind"] == "depth_ratio":
            row = db.one(self.rows, r["param"], r["cond"])
            return row.value_max or row.value_min, row.clause_ref
        return 1.0, None

    def usage_limit(self, dia):
        """사용률 한도. 반환 {limit, note, base_limit, base_note}. 채택 여유율이 있으면 그것이 판정 한도다."""
        r = self.rule("CAPACITY")
        base, note = 1.0, "만관 이내"
        if r and r["kind"] == "depth_ratio":
            yr, cl = self.design_depth()
            base = h.flow(1.0, 1.0, 1.0, yr) / h.flow(1.0, 1.0, 1.0)
            note = "설계수심 y/D ≤ %.2f (%s %s)" % (yr, self.sid, cl)
        elif r and r["kind"] == "margin":
            m = db.one(self.rows, r["param"], r["cond"])
            base, note = 1 / (1 + m.value_min), "여유율 %.0f%% (%s %s)" % (m.value_min * 100, self.sid, m.clause_ref)
        out = {"limit": base, "note": note, "base_limit": base, "base_note": note}
        a = self.adopt.get("capacity_margin")
        if a:
            got = db.pick(self.other_rows(a["standard_id"]), "capacity_margin", {"system": self.system, "dia_mm": dia})
            if len(got) != 1:
                raise LookupError("채택 여유율 표(%s)에 관경 %s mm 행이 %d개" % (a["standard_id"], dia, len(got)))
            row = got[0]
            if row.value_max is not None and row.value_max != row.value_min and "pick" not in a:
                raise LookupError("여유율이 범위(%g~%g)라 adopt.capacity_margin.pick(min|max) 필요" % (row.value_min, row.value_max))
            m = row.value_max if a.get("pick") == "max" and row.value_max is not None else row.value_min
            out["limit"] = 1 / (1 + m)
            out["note"] = "여유율 %.0f%% (%s %s, %s) — 채택: %s" % (m * 100, a["standard_id"], row.clause_ref, row.binding, a["rationale"])
        return out

    def velocity_limits(self, dia, material):
        """(최소유속, 수리상태, 근거), (최대유속, 수리상태, 근거). 규정 없으면 값 None."""
        ctx = {"dia_mm": dia, "material": material, "shape": "circular"}
        out = []
        for t, side, agg in (("VELOCITY_MIN", "value_min", max), ("VELOCITY_MAX", "value_max", min)):
            r = self.rule(t)
            rows = [x for x in db.pick(self.rows, r["param"], {**r.get("cond", {}), **ctx}, allow=tuple(r.get("allow", ())))
                    if x.binding in REQUIRED and getattr(x, side) is not None] if r else []
            v = agg(getattr(x, side) for x in rows) if rows else None
            out.append((v, r["state"] if r else None, "%s %s" % (self.sid, rows[0].clause_ref) if rows else "규정 없음"))
        return out

    def state_ko(self, state):
        if state == "design_depth":
            return "설계수심 y/D=%.2f" % self.design_depth()[0]
        return STATE_KO.get(state, "-")

    def maintenance_tier(self, D, S, n, Q, std_state):
        """adopt.maintenance_tiers: 판정 유속이 below 미만인 첫 등급, 없으면 else. state가 standard면 기준 최소유속 규칙의 수리상태."""
        t = self.adopt.get("maintenance_tiers")
        if not t:
            return None
        state = std_state if t.get("state", "standard") == "standard" else t["state"]
        v = self.velocity(D, S, n, Q, state)
        for x in sorted(t["tiers"], key=lambda x: x["below"]):
            if v < x["below"] - 1e-12:
                return {**x, "v": v, "state": state}
        return {**t["else"], "v": v, "state": state}

    def source_label(self, a):
        sid = a.get("standard_id")
        return "%s (%s)" % (DOC_KO.get(db.doc_type(sid), "?"), sid) if sid else "사업 채택"

    def velocity(self, D, S, n, Q, state):
        if state == "actual":
            yr = h.depth_ratio_for_flow(D, S, n, Q) if Q > 0 else None
            return h.velocity(D, S, n, yr) if yr else h.velocity(D, S, n)
        return h.velocity(D, S, n, self.design_depth()[0] if state == "design_depth" else 1.0)

    def hazen_c(self, dia):
        a = self.adopt.get("hazen_c")
        if a:
            return a["value"], "채택: " + a["rationale"]
        r = self.rule("FORCE_MAIN_FRICTION")
        if not r:
            raise LookupError("Hazen-Williams C 규정 없음 — adopt.hazen_c 필요")
        rows = [x for x in db.pick(self.rows, r["param"], {**r["cond"], "dia_mm": dia}, allow=tuple(r.get("allow", ())))
                if x.binding != "none"]
        vals = [x.value_min if x.value_min is not None else x.value_max for x in rows]
        c = min(vals) if r.get("pick") == "min" else max(vals)
        return c, "%s %s" % (self.sid, rows[0].clause_ref)

    def minor_loss(self, v, sum_k):
        hv = v * v / (2 * G)
        if sum_k is not None:
            return sum_k * hv, "ΣK %.2f × v²/2g (검토 파일 입력)" % sum_k
        r = self.rule("MINOR_LOSS") or {"kind": "review"}
        if r["kind"] == "c_includes_bends":
            if r.get("exit_velocity_head"):
                return hv, "C에 굴곡손실 포함 + 토출 속도수두 (%s %s)" % (self.sid, r["clause"])
            return 0.0, "C에 굴곡손실 포함 (%s %s)" % (self.sid, r["clause"])
        return None, "판정 보류: 부속손실 규정·입력 없음 (force_main.sum_k 필요)"


def check_pipe(cr, p, scenarios):
    D = p.get("D_inner_mm", p["D_mm"]) / 1000
    S = p["S_permil"] / 1000
    n, n_note = cr.manning_n(p.get("material"))
    qf = h.flow(D, S, n)
    lim = cr.usage_limit(p["D_mm"])
    (vmin, smin, cmin), (vmax, smax, cmax) = cr.velocity_limits(p["D_mm"], p.get("material"))
    low = cr.adopt.get("low_velocity")
    out = {"id": p["id"], "label": p.get("label", p["id"]), "D_mm": p["D_mm"], "S_permil": p["S_permil"], "n": n, "n_note": n_note,
           "qf_m3d": qf * DAY, "v_full": h.velocity(D, S, n), "limit": lim, "vmin": (vmin, smin, cmin), "vmax": (vmax, smax, cmax),
           "by": {}}
    for sc in scenarios:
        f = p["flow"][sc]
        Q = f["hourly_max_m3d"] / DAY
        u = Q / qf
        yr = h.depth_ratio_for_flow(D, S, n, Q) if Q > 0 else None
        v_lo = cr.velocity(D, S, n, Q, smin) if vmin is not None else None
        v_hi = cr.velocity(D, S, n, Q, smax) if vmax is not None else None
        tier = cr.maintenance_tier(D, S, n, Q, smin) if smin else None
        why, judge = [], "OK"
        if u > lim["limit"] + 1e-12:
            why.append("사용률 %.1f%% > %.0f%%" % (u * 100, lim["limit"] * 100))
            judge = "NG"
        if vmax is not None and v_hi > vmax + 1e-12:
            why.append("%s 유속 %.2f > %.1f m/s" % (cr.state_ko(smax), v_hi, vmax))
            judge = "NG"
        if vmin is not None and v_lo < vmin - 1e-12:
            why.append("%s 유속 %.2f < %.1f m/s" % (cr.state_ko(smin), v_lo, vmin))
            if judge == "OK":
                judge = low["label"] if low else (tier["label"] if tier else "NG")
        out["by"][sc] = {"daily_max_m3d": f.get("daily_max_m3d"), "hourly_max_m3d": f["hourly_max_m3d"], "usage": u,
                         "v_check_min": v_lo, "v_actual": h.velocity(D, S, n, yr) if yr else None, "depth_ratio": yr,
                         "judge": judge, "why": why, "tier": tier}
    return out


def check_section(cr, s, scenarios):
    pipes = [check_pipe(cr, p, scenarios) for p in s["pipes"]]
    gov = {sc: max(pipes, key=lambda x: x["by"][sc]["usage"]) for sc in scenarios}
    judge = {}
    for sc in scenarios:  # 구간 판정: NG가 하나라도 있으면 NG, 아니면 OK 아닌 분류(지속관리 등), 아니면 OK
        js = [x["by"][sc]["judge"] for x in pipes]
        judge[sc] = "NG" if "NG" in js else next((j for j in js if j != "OK"), "OK")
    return {"id": s["id"], "label": s.get("label", ""), "pipes": pipes, "governing": gov, "judge": judge}


def check_station(cr, s, scenarios):
    q = s["q_m3min"]
    ww = s["wet_well"]
    V = ww["volume_m3"] if "volume_m3" in ww else math.pi / 4 * ww["D_m"] ** 2 * ww["h_m"]
    fm = s["force_main"]
    Dm = fm["D_mm"] / 1000
    Qs = q / 60
    v = Qs / (math.pi * Dm ** 2 / 4)
    C, c_note = cr.hazen_c(fm["D_mm"])
    hl = h.hazen_williams_loss(fm["L_m"], Qs, C, Dm)
    hm, hm_note = cr.minor_loss(v, fm.get("sum_k"))
    ha = fm["top_invert"] - s["lwl"]
    H = None if hm is None else ha + hl + hm
    head = "판정 보류" if H is None else ("OK" if H <= s["installed_head_m"] + 1e-12 else "NG")
    lim = cr.adopt.get("pump_starts_per_hour")
    out = {"id": s["id"], "q_m3min": q, "V_m3": V, "t_min": V / q, "fm_v": v, "C": C, "C_note": c_note, "ha": ha, "hl": hl,
           "hm": hm, "hm_note": hm_note, "H": H, "installed_head_m": s["installed_head_m"], "head_judge": head,
           "starts_limit": lim, "by": {}}
    for sc in scenarios:
        Qh = s["inflow"][sc]["hourly_max_m3d"] / 1440
        Qx = min(Qh, q / 2)
        N = 60 / (V / Qx + V / (q - Qx)) if Qx > 0 else 0.0
        cap = "OK" if q > Qh else "NG"
        starts = "판정 보류" if not lim else ("OK" if N <= lim["value"] + 1e-12 else "NG")
        out["by"][sc] = {"daily_max_m3d": s["inflow"][sc].get("daily_max_m3d"), "Qh_m3min": Qh, "Q_star": Qx, "N": N,
                         "cap_judge": cap, "starts_judge": starts}
    return out


def check_regulations(cr):
    """구속력 있는 규정(case.regulations)의 mandatory 행을 채택 유지관리 등급과 대조. 반환 [{judge, text}].
    적용범위는 행 조건과 case.area로 판단: 모두 일치 → 적용, 하나라도 불일치 → 해당 없음, 값 없음 → 적용 여부 미확인."""
    t = cr.adopt.get("maintenance_tiers")
    grades = (t["tiers"] + [t["else"]]) if t else []
    out = []
    for sid in cr.regulations:
        for r in [x for x in cr.other_rows(sid) if x.binding == "mandatory"]:
            got = {k: cr.area.get(k) for k in r.condition}
            if any(g is not None and g != r.condition[k] for k, g in got.items()):
                scope = "해당 없음"
            elif all(g == r.condition[k] for k, g in got.items()):
                scope = "적용"
            else:
                scope = "적용 여부 미확인"
            ref = "%s %s (%s)" % (sid, r.clause_ref, DOC_KO.get(db.doc_type(sid), "?"))
            if r.param_key == "sewer_cleaning_min_frequency" and grades:
                for g in grades:
                    f = g.get("dredge_per_year")
                    if f is not None and f < r.value_min - 1e-12:
                        out.append({"judge": {"적용": "NG", "적용 여부 미확인": "확인 필요"}.get(scope, "해당 없음"),
                                    "text": "%s 준설 %g회/년 < %g회/년 — %s, 적용범위: %s" % (g["label"], f, r.value_min, ref, scope)})
            else:
                out.append({"judge": "참고" if scope != "해당 없음" else "해당 없음",
                            "text": "%s — %s, 적용범위: %s" % (r.value_text or r.param_key, ref, scope)})
    return out


def run(case):
    cr = Criteria(case)
    sc = case["scenarios"]
    return {"case": case, "criteria": cr, "sections": [check_section(cr, s, sc) for s in case.get("sections", [])],
            "stations": [check_station(cr, s, sc) for s in case.get("stations", [])], "regulations": check_regulations(cr)}


def _f(x, fmt="%.1f"):
    return "-" if x is None else fmt % x


def report(res):
    case, cr, sc = res["case"], res["criteria"], res["case"]["scenarios"]
    L = ["# 시설 검토 — %s" % case["check_id"], ""]
    if case.get("note"):
        L += [case["note"], ""]
    L += ["- 기준: %s (%s)" % (cr.sid, DOC_KO[db.doc_type(cr.sid)]), "- 시나리오: %s" % " → ".join(sc)]
    if cr.regulations:
        L.append("- 대조 규정: %s" % ", ".join("%s (%s)" % (s, DOC_KO[db.doc_type(s)]) for s in cr.regulations))
    L.append("")
    if cr.adopt:
        L += ["## 채택값 (기준값 아님)", "", "| 항목 | 값 | 출처 종류 | 근거 |", "|---|---|---|---|"]
        for k, a in cr.adopt.items():
            if k == "low_velocity":
                val = a["label"]
            elif k == "maintenance_tiers":
                val = " / ".join("%s < %g m/s" % (x["label"], x["below"]) for x in sorted(a["tiers"], key=lambda x: x["below"]))
                val += " / 그 외 %s" % a["else"]["label"]
            else:
                val = a.get("value", a.get("standard_id", ""))
            if k == "capacity_margin" and a.get("pick"):
                val = "%s (범위면 %s)" % (val, a["pick"])
            L.append("| %s | %s | %s | %s |" % (k, val, cr.source_label(a), a.get("rationale", "")))
        L.append("")
    if res["sections"]:
        L += ["## 자연유하관", ""]
        L.append("| 구간 | 지배관 | D(mm) | S(‰) | n | 만관유량(㎥/일) | 만관유속(m/s) | " +
                 " | ".join("%s 시간최대(㎥/일) | %s 사용률(%%) | %s 판정" % (s, s, s) for s in sc) + " |")
        L.append("|" + "---|" * (7 + 3 * len(sc)))
        notes = []
        for s in res["sections"]:
            g = s["governing"][sc[-1]]
            cells = []
            for x in sc:
                gx = s["governing"][x]["by"][x]
                cells += [_f(gx["hourly_max_m3d"]), _f(gx["usage"] * 100), s["judge"][x]]
            L.append("| %s %s | %s | %d | %s | %.3f | %s | %.2f | %s |" % (
                s["id"], s["label"], g["label"], g["D_mm"], _f(g["S_permil"]), g["n"], "{:,.0f}".format(g["qf_m3d"]), g["v_full"],
                " | ".join(cells)))
            for p in s["pipes"]:
                for x in sc:
                    if p["by"][x]["why"]:
                        notes.append("- %s %s (%s): %s → %s" % (s["id"], p["label"], x, ", ".join(p["by"][x]["why"]), p["by"][x]["judge"]))
        p0 = res["sections"][0]["pipes"][0]
        vmin, smin, cmin = p0["vmin"]
        vmax, smax, cmax = p0["vmax"]
        L += ["", "주1. 만관유량 Q = (1/n)·A·R^(2/3)·S^(1/2) (Manning). n: %s" % p0["n_note"],
              "주2. 사용률 = 시간최대 누가유량 ÷ 만관유량. 한도: %s → %.0f%% 이하 (기준 자체 한도: %s → %.0f%%)" % (
                  p0["limit"]["note"], p0["limit"]["limit"] * 100, p0["limit"]["base_note"], p0["limit"]["base_limit"] * 100),
              "주3. 유속: 최소 %s m/s(%s, %s), 최대 %s m/s(%s, %s)" % (
                  _f(vmin), cr.state_ko(smin), cmin, _f(vmax), cr.state_ko(smax), cmax)]
        low = cr.adopt.get("low_velocity")
        if low:
            L.append("주4. 최소유속 미달은 [%s]으로 분류 (채택: %s)" % (low["label"], low["rationale"]))
        if notes:
            L += ["", "판정 사유", ""] + notes
        L.append("")
    t = cr.adopt.get("maintenance_tiers")
    if t and res["sections"]:
        L += ["## 유지관리 등급", "",
              "| 구간 | " + " | ".join("%s 판정관 | %s 유속(m/s) | %s 등급 | %s 준설(회/년) | %s 시기" % (s, s, s, s, s) for s in sc) + " |",
              "|" + "---|" * (1 + 5 * len(sc))]
        for s in res["sections"]:
            cells = []
            for x in sc:
                p = min(s["pipes"], key=lambda q: q["by"][x]["tier"]["v"])  # 구간에서 판정 유속이 가장 낮은 관
                g = p["by"][x]["tier"]
                cells += [p["label"], "%.2f" % g["v"], g["label"], _f(g.get("dredge_per_year"), "%g"), g.get("timing", "-")]
            L.append("| %s %s | %s |" % (s["id"], s["label"], " | ".join(cells)))
        st = res["sections"][0]["pipes"][0]["by"][sc[0]]["tier"]["state"]
        L += ["", "주1. 판정 유속: %s (채택: %s)" % (cr.state_ko(st), t.get("rationale", "")), ""]
    if res["regulations"]:
        L += ["### 규정 대조", ""] + ["- [%s] %s" % (x["judge"], x["text"]) for x in res["regulations"]] + [""]
    if res["stations"]:
        L += ["## 펌프장", "", "### 용량·기동횟수", "",
              "| 펌프장 | 정격(㎥/min) | 흡수정(㎥) | " + " | ".join(
                  "%s 시간최대(㎥/min) | %s 기동(회/h) | %s 용량 | %s 기동" % (s, s, s, s) for s in sc) + " |",
              "|" + "---|" * (3 + 4 * len(sc))]
        for st in res["stations"]:
            cells = []
            for x in sc:
                b = st["by"][x]
                cells += [_f(b["Qh_m3min"], "%.3f"), _f(b["N"]), b["cap_judge"], b["starts_judge"]]
            L.append("| %s | %.2f | %.3f | %s |" % (st["id"], st["q_m3min"], st["V_m3"], " | ".join(cells)))
        lim = res["stations"][0]["starts_limit"]
        L += ["", "주1. 용량: 정격 토출량 > 시간최대 유입량",
              "주2. 기동횟수 N = 60 ÷ [V/Q* + V/(q−Q*)], Q* = min(시간최대, q/2). 한도: %s" % (
                  "%g회/h (채택: %s)" % (lim["value"], lim["rationale"]) if lim else "기준 수치 없음 → 판정 보류"),
              "", "### 압송관 양정", "",
              "| 펌프장 | 유속(m/s) | C | 실양정(m) | 마찰손실(m) | 부속손실(m) | 소요양정(m) | 설치양정(m) | 판정 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for st in res["stations"]:
            L.append("| %s | %.2f | %g | %.2f | %.2f | %s | %s | %g | %s |" % (
                st["id"], st["fm_v"], st["C"], st["ha"], st["hl"], _f(st["hm"], "%.2f"), _f(st["H"], "%.2f"),
                st["installed_head_m"], st["head_judge"]))
        s0 = res["stations"][0]
        L += ["", "주1. 마찰손실 hf = 10.67·L·Q^1.852/(C^1.852·D^4.87) (Hazen-Williams, 정격 토출량). C: %s" % s0["C_note"],
              "주2. 부속손실: %s" % s0["hm_note"], "주3. 실양정 = 압송관 최고 관저고 − 흡수정 LWL", ""]
    return "\n".join(L)


def main(path, out=None):
    case = json.loads(Path(path).read_text(encoding="utf-8"))
    md = report(run(case))
    if out:
        Path(out).write_text(md, encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(md)


if __name__ == "__main__":
    main(*sys.argv[1:3])
