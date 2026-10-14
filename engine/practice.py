"""실무 판정 층 (기준서 아님): 가시설 공법 선정, 공사비(터파기+가시설), 중계펌프장 전환 비교.

규칙과 수치는 사업 파일(criteria/projects/<id>.json)의 "practice"에서 읽는다 — 사용자 실무 방식을 틀로, 수치는 예시/업체표/내역단가.
- 가시설: 적용표(공법별 적용 최대 깊이·지하수 조건)에서 조건을 만족하는 첫 공법
- 비용: 구간 평균 굴착깊이 × 굴착폭 × 연장 × 토공 단가 + 양측 흙막이 면적 × 가시설 단가
- 펌프장: 국공유지 맨홀 후보마다 '그 맨홀에서 다시 최소토피로 시작'하는 설계를 다시 돌려
  (터파기+가시설) 절감액이 (펌프장 공사비 + 유지관리 현재가치)보다 크면 펌프장 채택
사용: py -3 -m engine.practice SYN01
"""
import os
import sys

import psycopg

from engine.design import design, load_project
from engine.generic import Standard
from engine.network import load_network


def shoring_method(depth, gw_depth, table):
    has_gw = gw_depth is not None and gw_depth < depth  # 굴착 바닥이 지하수위보다 깊으면 지하수 있음
    for t in table:
        if depth <= t["max_depth"] and t["gw"] == has_gw:
            return t["method"]
    return "개별 검토(적용표 범위 밖)"


def link_cost(r, link, pr):
    uc, tb = pr["unit_costs"], pr["shoring"]["table"]
    depth = (r["cover_up"] + r["cover_dn"]) / 2 + r["D"] + 0.1  # 관저 아래 기초 0.1 m
    width = max(uc["trench_min_width_m"], r["D"] + uc["trench_extra_width_m"])
    method = shoring_method(max(r["cover_up"], r["cover_dn"]) + r["D"] + 0.1, link.get("gw"), tb)
    earth = depth * width * r["L"] * uc["earthwork_per_m3"]
    shore = 2 * depth * r["L"] * uc["shoring_per_m2"].get(method, 0)
    return {"depth": depth, "method": method, "earth": earth, "shoring": shore, "total": earth + shore}


def network_cost(out, links, pr):
    L = {l["id"]: l for l in links}
    rows = [dict(link=r["link"], **link_cost(r, L[r["link"]], pr)) for r in out]
    return sum(x["total"] for x in rows), rows


def pump_pv(pr):
    uc = pr["unit_costs"]
    r, n = uc["discount_rate"], uc["om_years"]
    annuity = n if r == 0 else (1 - (1 + r) ** -n) / r
    return uc["pump_station_capex"] + uc["pump_om_per_year"] * annuity


def evaluate(pid, standard_id, dsn=None):
    dsn = dsn or os.environ["SEWAGE_DB_DSN"]
    project = load_project(pid)
    pr = project["practice"]
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        nodes, links = load_network(cur, pid)
        st = Standard(standard_id, project, dsn)
        sizes = st.pipe_sizes(cur)
    base = design(st, nodes, links, sizes)
    base_cost, base_rows = network_cost(base, links, pr)
    pump = pump_pv(pr)
    cands = [n for n, v in nodes.items() if v["kind"] == "manhole"
             and all(v.get({"land_owner": "owner"}.get(k, k)) == val for k, val in pr["pump"]["site_filter"].items())]
    trials = []
    for n in cands:
        out = design(st, nodes, links, sizes, lifts={n})
        c, _ = network_cost(out, links, pr)
        trials.append({"node": n, "gravity_cost": c, "saving": base_cost - c, "pump_cost": pump, "net": base_cost - c - pump})
    best = max(trials, key=lambda t: t["net"]) if trials else None
    return {"standard_id": standard_id, "base_cost": base_cost, "base_rows": base_rows, "pump_pv": pump, "trials": trials,
            "decision": ("중계펌프장 %s 채택 (절감 %.0f백만원 > 펌프장 %.0f백만원)" % (best["node"], best["saving"] / 1e6, pump / 1e6))
            if best and best["net"] > 0 else "자연유하 유지 (어느 후보도 절감액 < 펌프장 비용)"}


def main(pid):
    project = load_project(pid)
    for sid in project["standards"]:
        e = evaluate(pid, sid)
        methods = {}
        for r in e["base_rows"]:
            methods[r["method"]] = methods.get(r["method"], 0) + 1
        bt = max(e["trials"], key=lambda t: t["saving"]) if e["trials"] else None
        print("%-28s 공사비(터파기+가시설) %6.0f백만원 | 가시설 %s | 최대 절감 후보 %s %.0f백만원 vs 펌프장 %.0f백만원 → %s"
              % (sid, e["base_cost"] / 1e6, methods, bt["node"] if bt else "-", (bt["saving"] if bt else 0) / 1e6, e["pump_pv"] / 1e6,
                 e["decision"]))


if __name__ == "__main__":
    main(sys.argv[1])
