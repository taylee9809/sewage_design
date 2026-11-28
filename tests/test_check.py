"""검토 모드(engine.check). DB 없이 criteria CSV로 돈다. 정답지: 실무 검토서 수기 계산(tests/fixtures/check_case01.json)."""
import copy
import json
from pathlib import Path

import pytest

from engine import check
from engine import criteria_db as db

CASE = json.loads((Path(__file__).parent / "fixtures" / "check_case01.json").read_text(encoding="utf-8"))
# 검토서 표 값: 만관유량(㎥/일), 사용률(%) 당초·변경
SHEET = {"A1": (1379, 0.5, 3.3), "A2": (1414, 1.5, 4.5), "A3": (1838, 2.7, 5.1), "A4": (3211, 1.6, 3.5), "B1": (2365, 1.8, 2.2)}
# 펌프장: 기동횟수(회/h) 당초·변경, 실양정, 마찰손실, 소요양정(m)
PUMPS = {"P1": (0.3, 1.7, 5.60, 1.99, 8.1), "P2": (0.4, 2.0, 2.48, 3.74, 7.5), "P3": (1.5, 1.7, 3.12, 0.03, 3.5)}


@pytest.fixture(scope="module")
def res():
    return check.run(CASE)


def sec(res, sid):
    return next(s for s in res["sections"] if s["id"] == sid)


def test_load_csv_matches_rules():
    rows = db.load_csv("KDS_61_40_00_20251001")
    assert db.one(rows, "manning_n", {"material": "pvc", "shape": "circular"}).value_min == 0.011
    assert db.one(rows, "max_depth_ratio", {"shape": "circular"}).value_max == 1.0


def test_full_flow_and_usage_match_sheet(res):
    for sid, (qf, u0, u1) in SHEET.items():
        g = sec(res, sid)["pipes"][0]
        assert g["qf_m3d"] == pytest.approx(qf, rel=0.006), sid  # 검토서 경사는 0.1‰ 반올림 표기
        assert g["by"]["당초"]["usage"] * 100 == pytest.approx(u0, abs=0.06), sid
        assert g["by"]["변경"]["usage"] * 100 == pytest.approx(u1, abs=0.06), sid


def test_adopted_margin_is_separate_from_standard(res):
    lim = sec(res, "A1")["pipes"][0]["limit"]
    assert lim["base_limit"] == pytest.approx(1.0)  # KDS: 만류(y/D=1.0) — 여유율 수치 없음
    assert lim["limit"] == pytest.approx(0.5)  # 채택: 소구경 여유율 100%
    assert "KR_MOE_SEWER_2011" in lim["note"] and "guide" in lim["note"]


def test_low_velocity_is_managed_not_failed(res):
    # 1.7·1.8‰ D200: 만관유속 0.51·0.52 m/s < 0.6 (KDS 1.3(1)① — 설계수심=만류로 판정)
    for sid in ("A1", "A2"):
        assert sec(res, sid)["judge"] == {"당초": "지속관리 구간", "변경": "지속관리 구간"}
    for sid in ("A3", "A4", "B1"):
        assert sec(res, sid)["judge"] == {"당초": "OK", "변경": "OK"}


def test_low_velocity_without_adoption_is_ng():
    case = copy.deepcopy(CASE)
    del case["adopt"]["low_velocity"]
    assert sec(check.run(case), "A1")["judge"]["변경"] == "집중유지관리"  # 등급표가 있으면 그 등급
    del case["adopt"]["maintenance_tiers"]
    assert sec(check.run(case), "A1")["judge"]["변경"] == "NG"  # 실무 채택이 없으면 기준 그대로


def test_margin_range_needs_explicit_pick_and_gaps_stay_empty():
    case = copy.deepcopy(CASE)
    cr = check.Criteria(case)
    assert cr.usage_limit(800)["limit"] == pytest.approx(0.5)  # 중구경 50~100% 중 max
    del case["adopt"]["capacity_margin"]["pick"]
    with pytest.raises(LookupError):
        check.Criteria(case).usage_limit(800)
    with pytest.raises(LookupError):  # 600~700 mm는 원문 표에 없음
        cr.usage_limit(650)


def test_pumps_match_sheet(res):
    for st in res["stations"]:
        n0, n1, ha, hl, H = PUMPS[st["id"]]
        assert st["by"]["당초"]["N"] == pytest.approx(n0, abs=0.06)
        assert st["by"]["변경"]["N"] == pytest.approx(n1, abs=0.06)
        assert st["ha"] == pytest.approx(ha, abs=0.005)
        assert st["hl"] == pytest.approx(hl, rel=0.03, abs=0.01)  # 검토서는 10.666·Q^1.85 형, 엔진은 10.67·Q^1.852 형
        assert st["H"] == pytest.approx(H, abs=0.1)
        assert st["head_judge"] == "OK"
        assert all(b["cap_judge"] == "OK" and b["starts_judge"] == "OK" for b in st["by"].values())


def test_pump_defaults_follow_standard_when_not_adopted():
    case = copy.deepcopy(CASE)
    for k in ("hazen_c", "pump_starts_per_hour"):
        del case["adopt"][k]
    del case["stations"][0]["force_main"]["sum_k"]
    st = check.run(case)["stations"][0]
    assert st["C"] == 110 and "1.2 (2) ③" in st["C_note"]
    assert st["hm"] == pytest.approx(st["fm_v"] ** 2 / (2 * 9.81))  # C에 굴곡 포함 → 토출 속도수두만
    assert st["by"]["변경"]["starts_judge"] == "판정 보류"


def test_new_design_single_scenario():
    case = copy.deepcopy(CASE)
    case["scenarios"] = ["신설"]
    for s in case["sections"]:
        for p in s["pipes"]:
            p["flow"] = {"신설": p["flow"]["변경"]}
    for st in case["stations"]:
        st["inflow"] = {"신설": st["inflow"]["변경"]}
    r = check.run(case)
    assert sec(r, "A3")["judge"] == {"신설": "OK"}
    md = check.report(r)
    assert "신설 사용률" in md and "지속관리 구간" in md

def test_doc_types_match_schema_and_judging_set():
    import re
    root = Path(__file__).parent.parent
    allowed = set(re.findall(r"'(\w+)'", re.search(r"doc_type\s+text NOT NULL CHECK \(doc_type IN \(([^)]*)\)", (root / "db" / "schema.sql").read_text(encoding="utf-8")).group(1)))
    std = json.loads((root / "criteria" / "standards.json").read_text(encoding="utf-8"))
    assert all(v["doc_type"] in allowed for v in std.values())
    assert set(db.JUDGING_DOC_TYPES) <= allowed
    assert std["KR_MOE_SEWER_2011"]["doc_type"] == "legacy_commentary"


def test_non_judging_document_cannot_be_the_standard():
    case = copy.deepcopy(CASE)
    case["standard_id"] = "KR_MOE_SEWER_2011"  # 구 기준 해설 → adopt로만
    with pytest.raises(ValueError):
        check.Criteria(case)


def test_maintenance_tiers_by_actual_velocity(res):
    # 실수심 유속(변경): A1 0.23, A2 0.27, A3 0.35, A4 0.56, B1 0.35 m/s / 당초 A3 0.30 미만
    want = {"A1": "집중유지관리", "A2": "집중유지관리", "A3": "중점유지관리", "A4": "중점유지관리", "B1": "중점유지관리"}
    for sid, label in want.items():
        assert sec(res, sid)["pipes"][0]["by"]["변경"]["tier"]["label"] == label, sid
    assert sec(res, "A3")["pipes"][0]["by"]["당초"]["tier"]["label"] == "집중유지관리"
    assert sec(res, "A1")["judge"]["변경"] == "지속관리 구간"  # 최소유속 판정(설계수심=만류)은 별도


def test_regulation_applies_only_inside_scope():
    def judges(flag):
        case = copy.deepcopy(CASE)
        case["area"] = {"flood_risk_area": flag}
        return [x["judge"] for x in check.run(case)["regulations"] if "준설" in x["text"] and "회/년" in x["text"]]
    assert judges(None) == ["확인 필요"]  # 정상관로 0.2회/년 < 고시 제6조② 연 1회 — 제3조 적용범위 미확인
    assert judges(True) == ["NG"]
    assert judges(False) == ["해당 없음"]
