"""기준값을 DB 대신 공개 CSV(criteria/*_sewer.csv)에서 읽는다. load_criteria와 같은 조건(정규화본 우선)·단위 환산.
DB 적재 전 확인용·테스트용. 비공개 기준의 원문 구절은 없지만 수치·조건·조항은 같다."""
import csv
import json
import sys

from engine import criteria_db as db
from engine.generic import ROOT

sys.path.insert(0, str(ROOT / "db"))  # db/는 스크립트 폴더
from load_criteria import load_normalized, normalize, row_key  # noqa: E402

_cache = {}


def rows_from_csv(standard_id):
    if not _cache:
        norm = load_normalized()
        for f in sorted((ROOT / "criteria").glob("*_sewer.csv")):
            for r in csv.DictReader(f.open(encoding="utf-8")):
                lo, hi, _ = normalize(r)
                n = norm.get(row_key(r), {})
                cond = n["condition"] if n.get("condition") is not None else (json.loads(r["condition"]) if r["condition"].strip() else {})
                _cache.setdefault(r["standard_id"], []).append(
                    db.Row(r["standard_id"], r["param_key"], cond, n.get("basis") or {}, lo, hi, r["binding"], r["clause_no"],
                           r["value_text"] or None))
    return list(_cache.get(standard_id, []))


def use_csv():
    """이후 criteria_db.load가 CSV를 읽게 한다."""
    db.load = lambda standard_id, dsn=None: rows_from_csv(standard_id)
