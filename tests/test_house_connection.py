"""배수설비 연결점 (SYN02 예시 연결점 C01~C03). 로컬 DB 필요."""
import math
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")

from engine.design import load_project  # noqa: E402
from engine.generic import Standard  # noqa: E402
from engine.pump import plan  # noqa: E402


@pytest.fixture(scope="module")
def project():
    return load_project("SYN02")


def test_limit_formulas_follow_text(project):
    z_box, Lc, D = 19.0, 8.0, 0.2
    kr = Standard("KDS_61_40_00_20251001", project).house_connection(z_box, Lc, D)[0]
    assert kr == pytest.approx(z_box - 0.01 * Lc - D / 2)  # 14.5(1)③ 경사 1%·중심선 위
    jp = Standard("JP_YOKOHAMA_SEKKEI_202604", project).house_connection(z_box, Lc, D)[0]
    assert jp == pytest.approx(z_box - 0.015 * Lc - D / 2 * (1 + math.sin(math.radians(45))))  # 6.2 150 mm 1.5%·45°
    co = Standard("CO_RAS_0330_2017_COMP2021", project).house_connection(z_box, Lc, D)[0]
    assert co == pytest.approx(z_box - 0.02 * Lc + 0.14 - D)  # Art.144 140 mm·2%·관정 이상
    for sid in ("TSS_WW_2026", "CPHEEO_SEW_2013"):
        lim, why = Standard(sid, project).house_connection(z_box, Lc, D)
        assert lim is None and why.startswith("판정 보류")


def test_design_lowers_main_to_receive_connection(project):
    from engine.network import load_network
    import psycopg
    with psycopg.connect(os.environ["SEWAGE_DB_DSN"]) as con, con.cursor() as cur:
        _, links = load_network(cur, "SYN02")
    conns = {c["id"]: (l["id"], c) for l in links for c in l["conns"]}
    for sid in ("KDS_61_40_00_20251001", "JP_YOKOHAMA_SEKKEI_202604", "CO_RAS_0330_2017_COMP2021"):
        st = Standard(sid, project)
        res = {r["link"]: r for r in plan("SYN02", sid)["out"]}
        for lid, c in conns.values():
            r = res[lid]
            lim = st.house_connection(c["z"], c["Lc"], r["D"])[0]
            assert r["inv_up"] - r["S"] * c["x"] <= lim + 1e-6, (sid, c["id"])
    kr = {r["link"]: r for r in plan("SYN02", "KDS_61_40_00_20251001")["out"]}
    assert "배수설비 연결 위해" in kr["V01-V02"]["governing"]
