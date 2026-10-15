"""설계기준 보고서(Design Criteria Report) 자동 생성 — 사업·기준 목록을 받아 Markdown으로.

구성: 1 적용 기준(판본·최신 여부·공개 조건) / 2 기준별 설계 항목 채택값(값·조항·구속력·원문 구절) /
      3 사업 채택값(원문에 없거나 선택지인 값과 근거) / 4 기준 비교(같은 basis끼리만 나란히) /
      5 설계 결과 요약과 결정 조항(펌프장 반영) / 5-2 펌프장·압송관 / 6 원문 한계·주의
사용: py -3 -m engine.report SYN01 docs/SYN01_design_criteria_report.md
"""
import collections
import json
import os
import sys

import psycopg

from engine.design import load_project
from engine.network import summarize
from engine.pump import plan

ITEMS = [  # (param_key, 한글명) — 보고서 2·4절 순서
    ("per_capita_wastewater", "1인1일 오수량"), ("per_capita_water_net", "1인1일 순급수량"), ("return_coefficient", "회귀계수"),
    ("peak_factor_hourly", "시간최대(첨두) 계수"), ("infiltration_allowance", "지하수·침입수"), ("min_design_flow", "구간 최소 설계유량"),
    ("min_velocity", "최소유속"), ("min_wall_shear_stress", "최소 벽면 전단응력"), ("max_velocity", "최대유속"),
    ("min_slope", "최소경사"), ("max_depth_ratio", "설계수심비"), ("capacity_margin", "여유율"), ("manning_n", "조도계수 n"),
    ("min_pipe_diameter", "최소관경"), ("min_cover", "최소토피"), ("manhole_max_spacing", "맨홀 최대간격"),
    ("drop_manhole_threshold", "부관(낙차맨홀) 기준 낙차"), ("junction_method", "관 접합"), ("pipe_size_no_decrease", "하류 관경 감소"),
]
BIND = {"mandatory": "의무", "standard": "기준", "guide": "참고", "none": "규정 없음"}


def fmt_val(r, hide_text=False):
    """hide_text: 재배포 불가 기준은 수치만 싣고 원문 문장은 싣지 않는다."""
    lo, hi, u = r[0], r[1], r[2] or ""
    if hide_text and lo is None and hi is None:
        return "(원문 비공개)" if r[3] else ""
    if lo is not None and hi is not None and lo != hi:
        return "%g~%g %s" % (lo, hi, u)
    v = lo if lo is not None else hi
    return ("%g %s" % (v, u)).strip() if v is not None else (r[3] or "")


def cond_txt(c):
    if not c:
        return ""
    parts = []
    for k, v in c.items():
        if isinstance(v, dict):
            v = " ".join("%s%s" % ({"ge": "≥", "gt": ">", "le": "≤", "lt": "<", "eq": "="}.get(a, a), b) for a, b in v.items() if b is not None)
        parts.append("%s %s" % (k, v))
    return ", ".join(parts)


def basis_txt(b):
    if not b:
        return ""
    b = {k: v for k, v in b.items() if k != "note"}  # basis 메모는 원문 구절일 수 있어 싣지 않음
    return "/".join(str(b[k]) for k in ("flow", "horizon", "hydraulic_state", "per") if b.get(k))


def _scrub(sid, msg, hide):
    """재배포 불가 기준은 규칙 설명 문장(rules의 text)을 빼고 수치·조항만 남긴다."""
    if not hide:
        return msg
    for r in _rules(sid):
        if r.get("text"):
            msg = msg.replace(r["text"], "원문 수치 없음")
    return msg


def _rules(sid):
    from engine.generic import ROOT
    return json.loads((ROOT / "criteria" / "rules" / ("%s.json" % sid)).read_text(encoding="utf-8"))["rules"]


def pump_section(w, plans, hidden):
    w("## 5-2. 펌프장·압송관\n")
    w("전환 조건에 원문 수치가 있으면 자동 배치, 없으면 판정 보류(설계자 검토)로 표시한다. 토구 지정 관저고에 자연유하로 닿지 못하면 "
      "기준과 무관한 물리적 필요로 토구 직전에 펌프장을 둔다. 원문에 없는 항목(흡입수위·부속손실·잠김 등)은 판정 보류이며, "
      "부속 구성은 펌프장마다 사업 입력(`station_fittings`)이다. 펌프장 칸의 A→B는 원거리 압송관(사이 구간은 압송관으로 대체되어 "
      "5절 자연유하 굴착 지표에서 빠짐), 화살표 없는 것은 인라인 양수장(압송관 길이 = 실양정 + 사업값)이다.\n")
    w("| 기준 | 펌프장 | 판정 메모 |\n|---|---|---|")
    for sid, p in plans.items():
        notes = "<br>".join(_scrub(sid, n, hidden[sid]) for n in p["notes"]) or "—"
        w("| %s | %s | %s |" % (sid, ", ".join(p["lifts"]) or "없음", notes.replace("|", "/")))
    rows = [(sid, s) for sid, p in plans.items() for s in p["stations"]]
    if not rows:
        w("")
        return
    w("\n### 양정·동력\n")
    w("| 기준 | 펌프장 | 첨두 Q (L/s) | 실양정 (m) | 압송관 (내경) × 연장 | 유속 (m/s) / 원문 범위 | C | 마찰 (m) | 부속 (m) | 전양정 (m) | 동력 (kW) |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for sid, s in rows:
        lo, hi = s["fm_v_range"]
        w("| %s | %s | %.1f | %.2f | %d (%.0f) × %.0f m | %.2f / %s~%s | %g | %.2f | %s | %.2f | %.1f |" % (
            sid, s["node"] + ("→" + s["to"] if s["mode"] == "remote" else ""), s["Q"] * 1000, s["static_m"], s["fm_dia"], s["fm_inner"], s["fm_len"], s["fm_v"], lo, hi, s["C"], s["hf"],
            "보류" if s["hm_note"].startswith("판정 보류") else "%.2f" % s["hm"], s["tdh"], s["power_kw"]))
    w("\n### 흡입수위·펌프·흡수정\n")
    w("| 기준 | 펌프장 | 흡입수위 | 부속손실 | 펌프 대수 | 흡입관 | 잠김·NPSH | 흡수정 |\n|---|---|---|---|---|---|---|---|")
    for sid, s in rows:
        h = hidden[sid]
        cells = ["%.2f m — %s" % (s["lwl"], s["lwl_note"]), s["hm_note"], s["pumps"], s["suction"], s["submergence"], s["wet_well"]]
        w("| %s | %s | %s |" % (sid, s["node"], " | ".join(_scrub(sid, c, h).replace("|", "/") for c in cells)))
    w("")


def main(pid, out_path):
    dsn = os.environ["SEWAGE_DB_DSN"]
    project = load_project(pid)
    sids = list(project["standards"])
    plans = {sid: plan(pid, sid, dsn) for sid in sids}  # 펌프장 판정 포함 설계 (펌프장 없으면 자연유하 설계와 같음)
    results = {sid: p["out"] for sid, p in plans.items()}
    hidden = {}
    L = []
    w = L.append
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        cur.execute("SELECT name, synthetic, note FROM network.project WHERE project_id=%s", (pid,))
        pname, synth, pnote = cur.fetchone()
        w("# 설계기준 보고서 — %s\n" % pname)
        w("> 자동 생성 (engine/report.py). %s 사업 ID `%s`. 원문 값은 DB `criteria.criterion`, 해석 규칙은 `criteria/rules/`, "
          "사업 채택값은 `criteria/projects/%s.json`에서 읽었다.\n" % ("가상 관망 —" if synth else "", pid, pid))
        # 1
        w("## 1. 적용 기준\n")
        w("| 기준 | 판본 | 최신 | 공개 조건 | 비고 |\n|---|---|---|---|---|")
        for sid in sids:
            cur.execute("SELECT title, edition, is_latest, redistributable, license_note, note FROM criteria.standard WHERE standard_id=%s", (sid,))
            t, ed, latest, red, lic, note = cur.fetchone()
            w("| %s<br>`%s` | %s | %s | %s | %s |" % (t, sid, ed or "", "예" if latest else "아니오", red, (note or "").replace("|", "/")))
            hidden[sid] = red != "full_text"
        w("")
        # 2
        w("## 2. 기준별 설계 항목 (원문 그대로)\n")
        w("원문 구절은 재배포 가능한 기준(공개 조건 full_text)만 싣는다.\n")
        for sid in sids:
            cur.execute("SELECT redistributable FROM criteria.standard WHERE standard_id=%s", (sid,))
            show_quote = cur.fetchone()[0] == "full_text"
            w("### %s\n" % sid)
            w("| 항목 | 조건 | 값 | 정의 조건(basis) | 조항 | 구속력 | 원문 구절 |\n|---|---|---|---|---|---|---|")
            for key, name in ITEMS:
                cur.execute("""SELECT value_min::float, value_max::float, unit_si, value_text, condition, basis, clause_ref, binding, quote_short
                               FROM criteria.criterion WHERE standard_id=%s AND param_key=%s
                                 AND NOT (coalesce(condition,'{}'::jsonb) ?| array['exception','sewer_type','item'])
                               ORDER BY criterion_id""", (sid if key not in ("per_capita_wastewater", "peak_factor_hourly", "infiltration_allowance")
                                                          or not sid.startswith("KDS") else "KDS_61_10_00_20251001", key))
                for r in cur.fetchall():
                    w("| %s | %s | %s | %s | %s | %s | %s |" % (name, cond_txt(r[4]), fmt_val(r, not show_quote), basis_txt(r[5]), r[6] or "",
                                                                 BIND.get(r[7], r[7]), (r[8] or "").replace("|", "/")[:80] if show_quote else ""))
            w("")
        # 3
        w("## 3. 사업 채택값 (원문에 수치가 없거나 선택지를 주는 값)\n")
        w("| 기준 | 항목 | 채택값 | 근거 |\n|---|---|---|---|")
        for sid, ch in project["standards"].items():
            for k, v in ch.items():
                if k == "pipe_product":
                    continue
                w("| %s | %s | `%s` | %s |" % (sid, k, v["value"], v["rationale"]))
        w("")
        # 4
        w("## 4. 기준 비교 — 같은 정의 조건끼리만\n")
        w("값 옆 괄호는 정의 조건(유량/시점/수리 상태/분모). 정의 조건이 다르면 숫자가 같아도 같은 기준이 아니다. "
          "실제 영향은 5절의 같은 관망 설계 결과로 비교한다.\n")
        w("| 항목 | " + " | ".join(sids) + " |\n|---|" + "---|" * len(sids))
        for key, name in ITEMS:
            cells = []
            for sid in sids:
                ssid = "KDS_61_10_00_20251001" if sid.startswith("KDS") and key in ("per_capita_wastewater", "peak_factor_hourly",
                                                                                     "infiltration_allowance") else sid
                cur.execute("""SELECT value_min::float, value_max::float, unit_si, value_text, basis, binding FROM criteria.criterion
                               WHERE standard_id=%s AND param_key=%s
                                 AND NOT (coalesce(condition,'{}'::jsonb) ?| array['exception','sewer_type','item','location','pipe_role','other'])
                                 AND coalesce(condition->>'system','separate') IN ('separate','["separate", "combined"]')
                               ORDER BY criterion_id LIMIT 3""", (ssid, key))
                rs = cur.fetchall()
                cur.execute("SELECT redistributable FROM criteria.standard WHERE standard_id=%s", (ssid,))
                hide = cur.fetchone()[0] != "full_text"
                cells.append("<br>".join("%s (%s)" % (fmt_val(r, hide), basis_txt(r[4])) if r[5] != "none" else "규정 없음" for r in rs) or "—")
            w("| %s | %s |" % (name, " | ".join(c.replace("|", "/") for c in cells)))
        w("")
    # 5
    w("## 5. 같은 관망 설계 결과 (%s)\n" % pid)
    w("| 기준 | 굴착 지표(m²) | 최대 관경 | 최대 매설깊이(m) | 추가 맨홀 | 부관 | 플러싱 장치 | 경고 |\n|---|---|---|---|---|---|---|---|")
    for sid, out in results.items():
        s = summarize(out)
        w("| %s | %s | %s | %s | %s | %s | %s | %s |" % (sid, s["depth_x_len_m2"], s["max_dia"], s["max_depth_m"], s["extra_manholes"],
                                                     s["drops"], s["flushing_devices"], s["warnings"]))
    w("\n### 경사·관경을 결정한 조항 (구간 수)\n")
    for sid, out in results.items():
        c = collections.Counter(o["governing"].split(" — ")[0].split(" [")[0][:70] for o in out)
        w("- **%s**: " % sid + "; ".join("%s ×%d" % (k, v) for k, v in c.most_common(4)))
    w("")
    hc = {sid: [o for o in out if "배수설비" in o["governing"]] for sid, out in results.items()}
    if any(hc.values()):
        w("### 배수설비 연결점 (오수받이 관저고 → 연결관 → 본관)\n")
        w("연결관 최소경사와 본관 접속 높이(원문)로 본관 관저고 상한을 구하고, 넘으면 경사를 유지한 채 구간을 낮춘다. "
          "접속 높이 수치가 없는 기준은 판정 보류.\n")
        w("| 기준 | 낮춘 구간 | 최대 낮춤 (m) | 판정 보류 구간 |\n|---|---|---|---|")
        for sid, rs in hc.items():
            low = [(o["link"], float(o["governing"].split("배수설비 연결 위해 ")[1].split(" m")[0])) for o in rs if "연결 위해" in o["governing"]]
            held = [o["link"] for o in rs if "배수설비 연결 판정 보류" in o["governing"]]
            w("| %s | %s | %s | %s |" % (sid, ", ".join(x for x, _ in low) or "—", "%.3f" % max(v for _, v in low) if low else "—",
                                        ", ".join(held) or "—"))
        w("")
    pump_section(w, plans, hidden)
    # 6
    w("## 6. 원문 한계·주의\n")
    w("- 각 기준의 판정 규칙 해석(원문 미지정 해소)은 `criteria/rules/<기준>.json`의 `resolution`에 근거 조항과 함께 적혀 있다.")
    w("- 이미지·수식 판독 신뢰도가 낮은 항목은 DB `criteria.asset.confidence='low'`로 표시된다.")
    w("- 이 보고서는 기준 간 비교용이며, 실제 사업 적용 시 발주처 승인 절차(설계기준 보고서 승인)를 거쳐야 한다.")
    open(out_path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("written", out_path, len(L), "lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
