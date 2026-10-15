"""펌프장·압송관 (SYN02 저지대 관망). 로컬 DB 필요."""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")

from engine.pump import plan  # noqa: E402

SIDS = ["KDS_61_40_00_20251001", "TSS_WW_2026", "JP_YOKOHAMA_SEKKEI_202604", "CPHEEO_SEW_2013", "CO_RAS_0330_2017_COMP2021"]


@pytest.fixture(scope="module")
def plans():
    return {s: plan("SYN02", s) for s in SIDS}


def test_depth_limit_places_relay_station_only_where_text_gives_number(plans):
    # 인도만 매설 6 m 한도(의무) → 중계펌프장 자동, 나머지는 토구 직전 물리적 필요분만
    assert plans["CPHEEO_SEW_2013"]["lifts"] == ["U10", "U12"]
    for s in SIDS:
        if s != "CPHEEO_SEW_2013":
            assert plans[s]["lifts"] == ["U12"]


def test_review_kinds_flagged_not_decided(plans):
    for s in ("KDS_61_40_00_20251001", "JP_YOKOHAMA_SEKKEI_202604"):
        assert any(n.startswith("판정 보류") for n in plans[s]["notes"])


def test_force_main_velocity_in_text_range(plans):
    for s, p in plans.items():
        for st in p["stations"]:
            vmin, vmax = st["fm_v_range"]
            assert (vmax is None or st["fm_v"] <= vmax + 1e-9) and (vmin is None or st["fm_v"] >= vmin - 1e-9 or st["notes"]), s


def test_no_outfall_problem_left(plans):
    for p in plans.values():
        assert not any(n.startswith("남은 문제") for n in p["notes"])


def test_wet_well_level_only_where_text_gives_rule(plans):
    st = {s: p["stations"][-1] for s, p in plans.items()}
    # 한국: 흡입수위 = 유입관저 + 일평균 수심 (KDS 61 45 00 1.4(1)) → 유입관저보다 높다
    assert not st["KDS_61_40_00_20251001"]["lwl_held"] and "1.4 (1)" in st["KDS_61_40_00_20251001"]["lwl_note"]
    # 인도: 유입관저 − 1.0 m (4.1.4 0.5~1.0 m 중 상한 채택)
    assert not st["CPHEEO_SEW_2013"]["lwl_held"] and "1.0 m" in st["CPHEEO_SEW_2013"]["lwl_note"]
    for s in ("TSS_WW_2026", "JP_YOKOHAMA_SEKKEI_202604", "CO_RAS_0330_2017_COMP2021"):
        assert st[s]["lwl_held"] and st[s]["lwl_note"].startswith("판정 보류")


def test_minor_loss_by_text(plans):
    kr = plans["KDS_61_40_00_20251001"]["stations"][-1]
    assert kr["hm"] == pytest.approx(kr["fm_v"] ** 2 / (2 * 9.81))  # C=110에 굴곡 포함 → 토출 속도수두만
    assert plans["JP_YOKOHAMA_SEKKEI_202604"]["stations"][-1]["hm"] == 0
    ind = plans["CPHEEO_SEW_2013"]["stations"][-1]
    # 예시 부속: 입구 0.5 + 스윙체크 2.5 + 게이트 0.4×2 + 90° 1.0×3 + 티 1.5 = ΣK 8.3, + 속도수두
    assert ind["hm"] == pytest.approx(9.3 * ind["fm_v"] ** 2 / (2 * 9.81))
    for s in ("TSS_WW_2026", "CO_RAS_0330_2017_COMP2021"):
        st = plans[s]["stations"][-1]
        assert st["hm"] == 0 and st["hm_note"].startswith("판정 보류")
    for p in plans.values():
        for st in p["stations"]:
            assert st["tdh"] == pytest.approx(max(st["static_m"], 0) + st["hf"] + st["hm"])


def test_suction_and_submergence(plans):
    assert "흡입관경" in plans["KDS_61_40_00_20251001"]["stations"][-1]["suction"]
    assert "102 mm" in plans["TSS_WW_2026"]["stations"][-1]["suction"]
    assert "2.5 ×" in plans["CO_RAS_0330_2017_COMP2021"]["stations"][-1]["submergence"]
    assert "NPSH 판정 보류" in plans["CPHEEO_SEW_2013"]["stations"][-1]["submergence"]


def test_terminal_station_is_force_main_to_outfall(plans):
    # 토구 관저고 미달 → 토구 직전 펌프장 + 토구까지 압송관(자연유하 설계에서 제외)
    for p in plans.values():
        st = [s for s in p["stations"] if s["node"] == "U12"][0]
        assert st["mode"] == "remote" and st["to"] == "U13" and st["fm_links"] == ["U12-U13"]
        assert st["fm_len"] == pytest.approx(100.0)
        assert "U12-U13" not in {r["link"] for r in p["out"]}


def test_remote_force_main_from_project_input():
    from engine.design import load_project
    pj = load_project("SYN02")
    pj["pump_stations"] = {"value": [{"node": "U08", "to": "U13"}]}
    p = plan("SYN02", "CPHEEO_SEW_2013", project=pj)
    assert p["lifts"] == ["U08"]  # 원거리 압송으로 깊은 구간이 사라져 매설 한도 중계펌프장 불필요
    st = p["stations"][0]
    assert st["mode"] == "remote" and st["fm_len"] == pytest.approx(500.0)
    assert st["static_m"] == pytest.approx(22.0 - st["lwl"])  # 토구 지정 관저고까지
    gravity = {r["link"] for r in p["out"]}
    assert not gravity & {"U08-U09", "U09-U10", "U10-U11", "U11-U12", "U12-U13"}
    # 압송 구간 중간 맨홀 자체 유입은 설계자 검토로 표시
    assert sum("압송 구간 중간 맨홀" in n for n in p["notes"]) == 4
