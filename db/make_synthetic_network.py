"""가상 오수관망 SYN01 생성 → network 스키마.

실제 장소와 무관한 시험용 관망. 좌표는 EPSG:5186 수치를 빌렸을 뿐 위치에 의미 없음.
기준 간 차이가 드러나도록 일부러 넣은 조건:
- 간선 T(13개 맨홀, 동쪽 토구) + 지선 A(급경사), B(평탄), C(소유량)
- 맨홀 간격 45~140 m (한국 75 m·일본 50 m·인도 30 m 규정이 갈리도록)
- 지선 C 상류는 인구가 아주 적음 (실수심 유속 판정 차이)
- 지선 A는 지반 경사 약 3% (최대유속), 지선 B는 약 0.1% (최소경사)
사용: py -3 db/make_synthetic_network.py <공개 DB DSN>
"""
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
PID, SRID = "SYN01", 5186
X0, Y0 = 200000.0, 450000.0

# (node_id, dx, dy, ground_el, pop_initial, pop_ultimate)
NODES = [
    # 간선 T: 서→동, 완만한 하향 + 중간 평탄 구간
    ("T00", 0, 0, 42.0, 150, 250), ("T01", 60, 0, 41.7, 200, 300), ("T02", 140, 5, 41.2, 250, 400),
    ("T03", 230, 10, 40.6, 300, 450), ("T04", 330, 10, 40.2, 250, 400), ("T05", 420, 0, 40.05, 300, 500),
    ("T06", 540, -5, 39.95, 350, 550), ("T07", 640, -5, 39.9, 300, 450), ("T08", 760, 0, 39.6, 250, 400),
    ("T09", 860, 0, 39.1, 300, 450), ("T10", 980, 5, 38.5, 350, 550), ("T11", 1060, 5, 38.0, 300, 500),
    ("T12", 1200, 0, 37.2, 0, 0),
    # 지선 A: 북쪽 언덕에서 T03으로 (급경사)
    ("A00", 230, 420, 55.0, 80, 120), ("A01", 230, 330, 52.2, 120, 180), ("A02", 230, 240, 49.4, 150, 220),
    ("A03", 230, 150, 46.5, 150, 250), ("A04", 230, 70, 43.0, 120, 200),
    # 지선 B: 남쪽 평지에서 T06으로 (평탄)
    ("B00", 540, -560, 40.75, 120, 200), ("B01", 540, -450, 40.65, 150, 250), ("B02", 540, -340, 40.5, 200, 300),
    ("B03", 540, -230, 40.4, 200, 300), ("B04", 540, -140, 40.3, 150, 250), ("B05", 540, -60, 40.15, 150, 250),
    # 지선 C: 북동쪽 소규모 단지에서 T09로 (소유량)
    ("C00", 860, 300, 41.8, 15, 25), ("C01", 860, 210, 41.0, 20, 30), ("C02", 860, 120, 40.2, 25, 40),
    ("C03", 860, 45, 39.6, 20, 30),
]
CHAINS = [["T%02d" % i for i in range(13)], ["A00", "A01", "A02", "A03", "A04", "T03"],
          ["B00", "B01", "B02", "B03", "B04", "B05", "T06"], ["C00", "C01", "C02", "C03", "T09"]]


def main(dsn):
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        cur.execute((ROOT / "db" / "schema_network.sql").read_text(encoding="utf-8"))
        cur.execute("DELETE FROM network.design_link WHERE project_id = %s", (PID,))
        cur.execute("DELETE FROM network.project WHERE project_id = %s", (PID,))
        cur.execute("INSERT INTO network.project VALUES (%s,%s,%s,true,%s)",
                    (PID, "가상 오수관망 SYN01", SRID, "간선 T + 지선 A(급경사)·B(평탄)·C(소유량). 위치 무의미."))
        pos = {}
        for nid, dx, dy, z, p0, p1 in NODES:
            x, y = X0 + dx, Y0 + dy
            pos[nid] = (x, y)
            cur.execute("""INSERT INTO network.node (project_id,node_id,kind,ground_el,pop_initial,pop_ultimate,geom)
                           VALUES (%s,%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),%s))""",
                        (PID, nid, "outfall" if nid == "T12" else "manhole", z, p0, p1, x, y, SRID))
        n = 0
        for ch in CHAINS:
            for a, b in zip(ch, ch[1:]):
                cur.execute("""INSERT INTO network.link (project_id,link_id,from_node,to_node,material,geom)
                               VALUES (%s,%s,%s,%s,'pvc',ST_SetSRID(ST_MakeLine(ST_MakePoint(%s,%s),ST_MakePoint(%s,%s)),%s))""",
                            (PID, "%s-%s" % (a, b), a, b, *pos[a], *pos[b], SRID))
                n += 1
        # 가상 토질·지하수: 지선 B(평지)와 간선 중간 평탄부는 지하수 얕음, 지선 A(언덕)는 풍화토·지하수 없음
        cur.execute("""UPDATE network.link SET soil_class = CASE WHEN link_id LIKE 'A%%' THEN 'weathered_soil'
                         WHEN link_id LIKE 'B%%' OR link_id IN ('T05-T06','T06-T07','T07-T08','T08-T09') THEN 'sand' ELSE 'clay' END,
                       gw_depth_m = CASE WHEN link_id LIKE 'B%%' THEN 1.2
                         WHEN link_id IN ('T05-T06','T06-T07','T07-T08','T08-T09') THEN 1.8 ELSE NULL END
                       WHERE project_id=%s""", (PID,))
        # 가상 국공유지(펌프장 후보): 간선 중간·하류 맨홀 일부
        cur.execute("UPDATE network.node SET land_owner = CASE WHEN node_id IN ('T05','T07','T09','T11','B03') THEN 'public' ELSE 'private' END "
                    "WHERE project_id=%s", (PID,))
        cur.execute("""SELECT count(*), round(min(length_m)), round(max(length_m)), round(sum(length_m))
                       FROM network.link WHERE project_id=%s""", (PID,))
        print("links", cur.fetchone())
        cur.execute("SELECT sum(pop_initial), sum(pop_ultimate) FROM network.node WHERE project_id=%s", (PID,))
        print("population initial/ultimate", cur.fetchone())


if __name__ == "__main__":
    main(sys.argv[1])
