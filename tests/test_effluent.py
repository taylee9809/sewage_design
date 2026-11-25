"""방류수질 법령값 태그(db/tag_effluent.py): CSV 와 태그 파일 동기, 나라별 숫자 표기 해석, DB 적재."""
import csv
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "db"))
import tag_effluent as te  # noqa: E402

needs_db = pytest.mark.skipif(not os.environ.get("SEWAGE_DB_DSN"), reason="SEWAGE_DB_DSN 없음")


def test_tag_file_matches_csv():
    _, tags = te.build()
    assert te.load_tags() == {t["row_key"]: t for t in tags}, "CSV 가 바뀜 → py -3 db/tag_effluent.py"


@pytest.mark.parametrize("country,raw,unit,expect", [
    ("KR", "1,000", "개/mL", (None, 1000.0, "max", False)),   # 한국: 쉼표 = 천 단위
    ("CO", "0,50", "mg/L", (None, 0.5, "max", False)),        # 콜롬비아: 쉼표 = 소수점
    ("CO", "6,00 a 9,00", "Unidades de pH", (6.0, 9.0, "range", False)),
    ("US", "6.0-9.0", "pH units (range)", (6.0, 9.0, "range", False)),
    ("IN", "<50", "mg/L", (None, 50.0, "max", True)),         # 미만
    ("US", "85", "% removal (minimum)", (85.0, None, "min", False)),
])
def test_value_parsing(country, raw, unit, expect):
    assert te.value({"country": country, "value_max": raw, "unit": unit}) == expect


def test_bands_and_period():
    c = te.condition({"capacity_m3_per_day": "50~<500", "period": "2029-12-01~", "region": "전 지역"})
    assert c == {"capacity_m3_d": {"ge": 50, "lt": 500}, "effective_from": "2029-12-01", "region": "all"}
    assert te.band(">625 y <=3000") == {"gt": 625, "le": 3000}


def test_bod_days_not_renamed():
    # 원문이 일수를 적지 않은 BOD(한국·인도)는 bod, 5일 명시만 bod5
    keys = {(t["law_id"][:2], t["param_key"]) for t in te.build()[1] if t["param_key"].startswith("bod")}
    assert ("KR", "bod") in keys and ("US", "bod5") in keys and ("CO", "bod5") in keys and ("KR", "bod5") not in keys


@needs_db
def test_db_loaded():
    import psycopg
    n_csv = sum(1 for _ in csv.DictReader(open(te.SRC, encoding="utf-8-sig")))
    with psycopg.connect(os.environ["SEWAGE_DB_DSN"]) as con:
        n, n_null = con.execute("SELECT count(*), count(*) FILTER (WHERE value_min IS NULL AND value_max IS NULL) "
                                "FROM criteria.effluent_limit").fetchone()
    assert n == n_csv and n_null == 0
