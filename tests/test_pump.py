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
