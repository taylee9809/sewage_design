"""실무 판정 층: 가시설 선정·펌프장 비교 로직."""
import os

import pytest

from engine.practice import pump_pv, shoring_method

TABLE = [{"method": "무지보(개착)", "max_depth": 1.5, "gw": False}, {"method": "조절식 간이흙막이 싱글", "max_depth": 2.5, "gw": False},
         {"method": "조절식 간이흙막이 더블", "max_depth": 4.0, "gw": False}, {"method": "H-pile+토류판", "max_depth": 10.0, "gw": False},
         {"method": "시트파일", "max_depth": 10.0, "gw": True}]


def test_shoring_by_depth_and_groundwater():
    assert shoring_method(1.2, None, TABLE) == "무지보(개착)"
    assert shoring_method(2.0, None, TABLE) == "조절식 간이흙막이 싱글"
    assert shoring_method(3.5, None, TABLE) == "조절식 간이흙막이 더블"
    assert shoring_method(5.0, None, TABLE) == "H-pile+토류판"
    assert shoring_method(2.0, 1.2, TABLE) == "시트파일"        # 굴착 바닥이 지하수위보다 깊음
    assert shoring_method(1.0, 1.2, TABLE) == "무지보(개착)"    # 지하수위보다 얕음
    assert shoring_method(12.0, None, TABLE).startswith("개별 검토")


def test_pump_present_value():
    pr = {"unit_costs": {"pump_station_capex": 100, "pump_om_per_year": 10, "om_years": 2, "discount_rate": 0.0}}
    assert pump_pv(pr) == 120
    pr["unit_costs"]["discount_rate"] = 0.1
    assert pump_pv(pr) == pytest.approx(100 + 10 / 1.1 + 10 / 1.21)


@pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")
def test_lift_station_reduces_downstream_depth():
    from engine.practice import evaluate
    e = evaluate("SYN01", "CPHEEO_SEW_2013")
    assert e["trials"] and max(t["saving"] for t in e["trials"]) > 0
