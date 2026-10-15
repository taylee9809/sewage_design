"""가상 오수관망 SYN02 — 저지대(분지)를 지나 높은 처리장으로 가야 하는 관망 (펌프장 판정 검증용).

간선 U(14개 맨홀): 고지(32 m) → 분지 바닥(20 m, 약 0.9 km 지점) → 처리장(24 m)으로 오르막. 토구는 처리장 유입 관저고 22.0 m 지정.
지선 V: 분지 바닥으로 들어오는 평탄 주거지. 실제 장소와 무관.
사용: py -3 db/make_syn02.py <공개 DB DSN>
"""
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
PID, SRID = "SYN02", 5186
X0, Y0 = 210000.0, 452000.0
# (node_id, dx, dy, ground_el, pop_initial, pop_ultimate)
NODES = [("U%02d" % i, i * 100, 0, gl, p0, p1) for i, (gl, p0, p1) in enumerate([
    (32.0, 200, 300), (30.5, 250, 400), (28.8, 250, 400), (26.9, 300, 450), (24.8, 300, 500), (22.9, 300, 500),
    (21.4, 350, 550), (20.5, 350, 550), (20.1, 300, 500), (20.4, 250, 400), (21.3, 200, 300), (22.4, 150, 250),
    (23.3, 100, 200), (24.0, 0, 0)])]
NODES += [("V%02d" % i, 800, -100 * (5 - i), gl, 200, 350) for i, gl in enumerate([20.9, 20.8, 20.6, 20.5, 20.3])]
CHAINS = [["U%02d" % i for i in range(14)], ["V00", "V01", "V02", "V03", "V04", "U08"]]
OUTFALL, OUTFALL_INV = "U13", 22.0
# 배수설비 연결점 예시 (conn_id, 구간 상류, 하류, 상류에서 거리 m, 오수받이 깊이 m, 연결관 길이 m) — 평탄한 V 지선의 깊은 오수받이
CONNS = [("C01", "V01", "V02", 50, 1.6, 8.0), ("C02", "V02", "V03", 60, 1.6, 8.0), ("C03", "U01", "U02", 40, 1.2, 6.0)]


def main(dsn):
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        cur.execute((ROOT / "db" / "schema_network.sql").read_text(encoding="utf-8"))
        cur.execute("DELETE FROM network.design_link WHERE project_id = %s", (PID,))
        cur.execute("DELETE FROM network.project WHERE project_id = %s", (PID,))
        cur.execute("INSERT INTO network.project VALUES (%s,%s,%s,true,%s)",
                    (PID, "가상 오수관망 SYN02 (저지대)", SRID, "분지 바닥을 지나 높은 처리장으로. 토구 관저고 22.0 m 지정. 위치 무의미."))
        pos = {}
        for nid, dx, dy, z, p0, p1 in NODES:
            pos[nid] = (X0 + dx, Y0 + dy)
            cur.execute("""INSERT INTO network.node (project_id,node_id,kind,ground_el,pop_initial,pop_ultimate,min_invert_el,land_owner,geom)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),%s))""",
                        (PID, nid, "outfall" if nid == OUTFALL else "manhole", z, p0, p1, OUTFALL_INV if nid == OUTFALL else None,
                         "public" if nid in ("U06", "U08", "U10") else "private", *pos[nid], SRID))
        for ch in CHAINS:
            for a, b in zip(ch, ch[1:]):
                cur.execute("""INSERT INTO network.link (project_id,link_id,from_node,to_node,material,soil_class,gw_depth_m,geom)
                               VALUES (%s,%s,%s,%s,'pvc','clay',%s,ST_SetSRID(ST_MakeLine(ST_MakePoint(%s,%s),ST_MakePoint(%s,%s)),%s))""",
                            (PID, "%s-%s" % (a, b), a, b, 1.5 if a[0] == "V" or a in ("U07", "U08", "U09") else None, *pos[a], *pos[b], SRID))
        # 배수설비 연결점 예시: 오수받이 관저고 = 접속점 지반고 − 깊이, 연결관 길이
        gl = {nid: z for nid, _, _, z, _, _ in NODES}
        for cid, a, b, x, depth, lc in CONNS:
            z = gl[a] + (gl[b] - gl[a]) * x / 100.0 - depth
            px, py = pos[a][0] + (pos[b][0] - pos[a][0]) * x / 100.0, pos[a][1] + (pos[b][1] - pos[a][1]) * x / 100.0
            cur.execute("""INSERT INTO network.house_connection VALUES (%s,%s,%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),%s))""",
                        (PID, cid, "%s-%s" % (a, b), x, round(z, 3), lc, "예시 — 오수받이 지표 아래 %.1f m" % depth, px, py, SRID))
        cur.execute("SELECT count(*), round(sum(length_m)) FROM network.link WHERE project_id=%s", (PID,))
        print("links", cur.fetchone())


if __name__ == "__main__":
    main(sys.argv[1])
