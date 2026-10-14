"""일반 엔진(규칙 데이터 구동)이 나라별 코드 버전과 같은 결과를 내는지 — SYN01 기준선 대조."""
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")

BASE = json.loads((Path(__file__).parent / "fixtures" / "syn01_baseline.json").read_text(encoding="utf-8"))
CC = {"KR": "KDS_61_40_00_20251001", "US": "TSS_WW_2026", "JP": "JP_YOKOHAMA_SEKKEI_202604", "IN": "CPHEEO_SEW_2013",
      "CO": "CO_RAS_0330_2017_COMP2021"}


@pytest.fixture(scope="module")
def results():
    from engine.design import run
    return run("SYN01")


@pytest.mark.parametrize("cc", list(CC))
def test_same_as_baseline(results, cc):
    out = {r["link"]: r for r in results[CC[cc]]}
    for link, b in BASE[cc]["links"].items():
        r = out[link]
        assert r["dia"] == b["dia"], link
        assert r["S"] == pytest.approx(b["S"], abs=1e-6), link
        assert r["inv_up"] == pytest.approx(b["inv_up"], abs=1e-3), link
        assert r["inv_dn"] == pytest.approx(b["inv_dn"], abs=1e-3), link
        assert r["extra_mh"] == b["extra_mh"], link
        assert r["drop"] == pytest.approx(b["drop"], abs=1e-3), link
        assert ("플러싱" in r["governing"]) == b["flush"], link
        assert ("경고" in r["governing"]) == b["warn"], link


def test_no_country_branches_in_generic_engine():
    """일반 엔진 코드에 나라·기준 이름 분기가 없어야 한다 (기본 실행 목록 한 줄만 예외)."""
    eng = Path(__file__).parent.parent / "engine"
    src = "\n".join(l for f in ("generic.py", "design.py") for l in (eng / f).read_text(encoding="utf-8").splitlines()
                    if not l.startswith("DEFAULT_STANDARDS"))
    for token in ('"KR"', '"US"', '"JP"', '"IN"', "KDS_", "TSS_", "YOKOHAMA", "CPHEEO"):
        assert token not in src, token
