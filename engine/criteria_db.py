"""sewage_design DB의 기준값(criteria.criterion)을 읽어 설계 조건에 맞는 행을 고른다.

DSN은 환경변수 SEWAGE_DB_DSN (예: postgresql://user:pw@localhost:5432/sewage_design).
"""
import os
from dataclasses import dataclass, field

# 조건에 이 키가 있으면 '예외·특수 사례' 행이다. 설계 조건(ctx)이 명시적으로 요구할 때만 쓴다.
SPECIAL_KEYS = {"exception", "other", "item", "facility", "lining", "location", "manhole_type", "joint_method",
                "pipe_role", "wastewater_type", "terrain", "depth_m", "slope", "road_width_m", "receives_house_connections",
                "sewer_type", "altitude_masl", "flow_lps"}


# 엔진 기본 판정에 쓰는 문서 종류. 나머지(지침·구 기준 해설·지자체 연구·논문)는 사업·검토 파일의 adopt로만 쓴다.
JUDGING_DOC_TYPES = ("law", "regulation", "design_standard")


def doc_type(standard_id):
    """criteria/standards.json의 문서 종류(doc_type)."""
    import json
    from pathlib import Path

    std = json.loads((Path(__file__).resolve().parent.parent / "criteria" / "standards.json").read_text(encoding="utf-8"))
    return std[standard_id]["doc_type"]


@dataclass
class Row:
    standard_id: str
    param_key: str
    condition: dict
    basis: dict
    value_min: float | None
    value_max: float | None
    binding: str
    clause_ref: str | None
    value_text: str | None = None
    raw: dict = field(default_factory=dict, repr=False)


def load(standard_id, dsn=None):
    import psycopg  # DB 없이 쓰는 경로(load_csv)에서는 필요 없음

    dsn = dsn or os.environ["SEWAGE_DB_DSN"]
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        cur.execute("""SELECT standard_id, param_key, coalesce(condition, '{}'::jsonb), coalesce(basis, '{}'::jsonb),
                              value_min, value_max, binding, clause_ref, value_text
                       FROM criteria.criterion WHERE standard_id = %s""", (standard_id,))
        return [Row(r[0], r[1], r[2], r[3], None if r[4] is None else float(r[4]), None if r[5] is None else float(r[5]),
                    r[6], r[7], r[8]) for r in cur.fetchall()]


def load_csv(standard_id):
    """load()와 같은 행을 DB 없이 criteria/*_sewer.csv + normalized/*.jsonl에서 읽는다 (적재 규칙은 db/load_criteria.py와 동일).
    조문 연결·비공개 원문은 빠진다 — 값·조건·basis·구속력·조항 표기만 필요할 때(검토 모드) 쓴다."""
    import csv
    import sys
    from pathlib import Path

    dbdir = Path(__file__).resolve().parent.parent / "db"
    if str(dbdir) not in sys.path:
        sys.path.insert(0, str(dbdir))
    import load_criteria as lc

    norm = lc.load_normalized()
    out = []
    for f in sorted((lc.ROOT / "criteria").glob("*_sewer.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["standard_id"] != standard_id:
                continue
            lo, hi, _ = lc.normalize(r)
            nz = norm.get(lc.row_key(r), {})
            out.append(Row(r["standard_id"], r["param_key"], nz.get("condition") or {}, nz.get("basis") or {}, lo, hi,
                           r["binding"], r["clause_no"] or None, r["value_text"] or None))
    if not out:
        raise LookupError("기준값 없음: %s" % standard_id)
    return out


def _range_ok(spec, x):
    if isinstance(spec, dict):
        return all({"eq": x == v, "ge": x >= v, "gt": x > v, "le": x <= v, "lt": x < v}[op]
                   for op, v in spec.items() if v is not None)
    return x == spec


def _value_ok(spec, x):
    if isinstance(spec, list):
        return x in spec or (isinstance(x, list) and set(x) & set(spec))
    return spec == x


def matches(row, ctx, allow=()):
    """row.condition의 모든 키가 ctx와 맞으면 True. ctx에 없는 일반 키는 통과, 특수 키는 allow에 있어야 통과."""
    for k, spec in row.condition.items():
        if k in ctx:
            v = ctx[k]
            if k in ("dia_mm", "population", "served_population", "depth_m", "slope", "road_width_m", "altitude_masl", "flow_lps"):
                if not _range_ok(spec, v):
                    return False
            elif not _value_ok(spec, v):
                return False
        elif k in SPECIAL_KEYS and k not in allow:
            return False
        elif k == "dia_basis":
            continue
    return True


def pick(rows, param_key, ctx, basis=None, allow=()):
    """param_key·조건·basis(부분 일치)에 맞는 행 목록."""
    out = []
    for r in rows:
        if r.param_key != param_key or r.binding == "none" or not matches(r, ctx, allow):
            continue
        if basis and any(r.basis.get(k) != v for k, v in basis.items()):
            continue
        out.append(r)
    return out


def one(rows, param_key, ctx, basis=None, allow=()):
    got = pick(rows, param_key, ctx, basis, allow)
    if len(got) != 1:
        raise LookupError("%s %s %s → %d행: %s" % (param_key, ctx, basis, len(got),
                                                     [(g.condition, g.basis, g.clause_ref) for g in got]))
    return got[0]
