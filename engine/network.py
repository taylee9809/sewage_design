"""관망 입력 읽기·정렬·요약·저장 (기준과 무관한 공용 부분)."""


def load_network(cur, pid):
    cur.execute("SELECT node_id, kind, ground_el::float, pop_initial, pop_ultimate, land_owner FROM network.node WHERE project_id=%s", (pid,))
    nodes = {r[0]: {"kind": r[1], "gl": r[2], "p0": r[3], "p1": r[4], "owner": r[5]} for r in cur.fetchall()}
    cur.execute("SELECT link_id, from_node, to_node, length_m::float, material, soil_class, gw_depth_m::float "
                "FROM network.link WHERE project_id=%s", (pid,))
    links = [dict(zip(("id", "up", "dn", "L", "mat", "soil", "gw"), r)) for r in cur.fetchall()]
    return nodes, links


def topo(links):
    """상류→하류 순서. 유입 링크가 모두 끝난 링크부터."""
    into = {}
    for l in links:
        into.setdefault(l["dn"], []).append(l)
    done, order = set(), []
    while len(order) < len(links):
        for l in links:
            if l["id"] not in done and all(i["id"] in done for i in into.get(l["up"], [])):
                order.append(l)
                done.add(l["id"])
    return order, into


def tributary_pop(order, into, nodes):
    p0, p1 = {}, {}
    for l in order:
        ins = into.get(l["up"], [])
        p0[l["id"]] = nodes[l["up"]]["p0"] + sum(p0[i["id"]] for i in ins)
        p1[l["id"]] = nodes[l["up"]]["p1"] + sum(p1[i["id"]] for i in ins)
    return p0, p1


def summarize(out):
    L = sum(r["L"] for r in out)
    exc = sum(r["L"] * ((r["cover_up"] + r["cover_dn"]) / 2 + r["D"]) for r in out)  # 연장×평균 관저 깊이 (굴착 지표)
    return {"total_len_m": round(L), "max_dia": max(r["dia"] for r in out),
            "outfall_depth_m": round(out[-1]["cover_dn"] + out[-1]["D"], 2),
            "max_depth_m": round(max(max(r["cover_up"], r["cover_dn"]) + r["D"] for r in out), 2),
            "depth_x_len_m2": round(exc), "extra_manholes": sum(r["extra_mh"] or 0 for r in out),
            "drops": sum(1 for r in out if r["drop"] > 0),
            "flushing_devices": sum(1 for r in out if "플러싱" in r["governing"]),
            "warnings": sum(1 for r in out if "경고" in r["governing"])}


def save(cur, pid, standard_id, run_id, out, note=""):
    cur.execute("DELETE FROM network.design_link WHERE project_id=%s AND standard_id=%s AND run_id=%s", (pid, standard_id, run_id))
    for r in out:
        cur.execute("INSERT INTO network.design_link VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (pid, standard_id, run_id, r["link"], r["dia"], r["S"], r["Q"], r["Qi"], r["inv_up"], r["inv_dn"],
                     r["cover_up"], r["cover_dn"], r["v"], r["extra_mh"], r["governing"], note))
