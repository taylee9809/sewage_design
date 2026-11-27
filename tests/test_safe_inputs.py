"""규칙·사업 파일 입력이 코드로 실행되지 않는지: 수식은 safe_expr, 관 제품 선택은 매개변수 SQL (DB 불필요)."""
import json
import math
from pathlib import Path

import pytest

from engine import safe_expr
from engine.generic import pipe_product_filter

ROOT = Path(__file__).resolve().parent.parent


def _exprs():
    """저장소의 규칙·사업 파일에 있는 수식 전부."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("expr", "when") and isinstance(v, str):
                    out.append(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for f in sorted((ROOT / "criteria" / "rules").glob("*.json")):
        walk(json.loads(f.read_text(encoding="utf-8")))
    for f in sorted((ROOT / "criteria" / "projects").glob("*.json")):
        for ch in json.loads(f.read_text(encoding="utf-8"))["standards"].values():
            for v in ch.values():
                if isinstance(v["value"], str) and "sqrt(" in v["value"]:
                    out.append(v["value"])
    return sorted(set(out))


def test_repo_expressions_parse():
    ex = _exprs()
    assert ex, "수식을 하나도 못 찾음"
    for e in ex:
        safe_expr.validate(e)


@pytest.mark.parametrize("P", [500, 1000, 10000, 100000])
def test_peak_factor_formulas(P):
    assert safe_expr.evaluate("1 + 14 / (4 + sqrt(P/1000))", {"P": P}) == pytest.approx(1 + 14 / (4 + math.sqrt(P / 1000)))
    assert safe_expr.evaluate("(18 + sqrt(P/1000)) / (4 + sqrt(P/1000))", {"P": P}) == \
        pytest.approx((18 + math.sqrt(P / 1000)) / (4 + math.sqrt(P / 1000)))


def test_conditions():
    assert safe_expr.evaluate("average > 3785.41", {"average": 4000}) is True
    assert safe_expr.evaluate("average <= 3785.41", {"average": 4000}) is False
    assert safe_expr.evaluate("100 <= average_lps < 250", {"average_lps": 120}) is True
    assert safe_expr.evaluate("not (a > 1) or b == 2", {"a": 5, "b": 2}) is True


@pytest.mark.parametrize("src", [
    "().__class__.__base__.__subclasses__()",
    "__import__('os').system('echo x')",
    "sqrt.__globals__",
    "[x for x in (1, 2)]",
    "(lambda: 1)()",
    "P[0]",
    "'abc'",
    "open('x')",
    "sqrt(x=1)",
    "9 ** 9 ** 9",
])
def test_rejects_code(src):
    with pytest.raises(safe_expr.ExprError):
        safe_expr.evaluate(src, {"P": 1})


def test_unknown_variable():
    with pytest.raises(safe_expr.ExprError, match="알 수 없는 변수"):
        safe_expr.evaluate("Q + 1", {"P": 1})


def test_pipe_filter_is_parameterized():
    where, args = pipe_product_filter([
        {"standard_ref": {"prefix": "ASTM D3034"}, "class_or_stiffness": {"prefix": "SDR 35"}},
        {"standard_ref": {"prefix": "ASTM F679"}, "product_type": "solid_wall_gravity_sewer_PSM", "class_or_stiffness": "PS 46"},
    ])
    assert where == ("(standard_ref LIKE %s AND class_or_stiffness LIKE %s) OR "
                     "(standard_ref LIKE %s AND product_type = %s AND class_or_stiffness = %s)")
    assert args == ["ASTM D3034%", "SDR 35%", "ASTM F679%", "solid_wall_gravity_sewer_PSM", "PS 46"]


def test_pipe_filter_escapes_like_wildcards():
    _, args = pipe_product_filter({"product_type": {"prefix": "a_b%c"}})
    assert args == ["a\\_b\\%c%"]


@pytest.mark.parametrize("spec", [
    "product_type LIKE 'x%'",                          # 옛 SQL 조각
    {"product_type) OR (1=1": "x"},                    # 허용 안 된 필드명
    {"note": "x"},
    {"product_type": {"regex": "x"}},
    {"product_type": {"eq": 1}},
    {"product_type": {"eq": "a", "prefix": "b"}},
    [],
    {},
])
def test_pipe_filter_rejects(spec):
    with pytest.raises(ValueError):
        pipe_product_filter(spec)


def test_repo_projects_pipe_product():
    n = 0
    for f in sorted((ROOT / "criteria" / "projects").glob("*.json")):
        for ch in json.loads(f.read_text(encoding="utf-8"))["standards"].values():
            if "pipe_product" in ch:
                pipe_product_filter(ch["pipe_product"]["value"])
                n += 1
    assert n > 0
