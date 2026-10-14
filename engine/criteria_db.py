"""sewage_design DB의 기준값(criteria.criterion)을 읽어 설계 조건에 맞는 행을 고른다.

DSN은 환경변수 SEWAGE_DB_DSN (예: postgresql://user:pw@localhost:5432/sewage_design).
"""
import os
from dataclasses import dataclass, field

import psycopg

# 조건에 이 키가 있으면 '예외·특수 사례' 행이다. 설계 조건(ctx)이 명시적으로 요구할 때만 쓴다.
SPECIAL_KEYS = {"exception", "other", "item", "facility", "lining", "location", "manhole_type", "joint_method",
                "pipe_role", "wastewater_type", "terrain", "depth_m", "slope", "road_width_m", "receives_house_connections",
                "sewer_type", "altitude_masl", "flow_lps"}


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
    dsn = dsn or os.environ["SEWAGE_DB_DSN"]
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        cur.execute("""SELECT standard_id, param_key, coalesce(condition, '{}'::jsonb), coalesce(basis, '{}'::jsonb),
                              value_min, value_max, binding, clause_ref, value_text
                       FROM criteria.criterion WHERE standard_id = %s""", (standard_id,))
        return [Row(r[0], r[1], r[2], r[3], None if r[4] is None else float(r[4]), None if r[5] is None else float(r[5]),
                    r[6], r[7], r[8]) for r in cur.fetchall()]


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
