"""규칙·사업 파일의 짧은 수식을 eval 없이 계산한다.

허용: 숫자, 이름(호출자가 넘긴 변수), + - * / ** %, 단항 + -, 비교(연쇄 포함), and/or/not, 괄호,
허용 함수 호출(sqrt 등). 속성 접근·첨자·문자열·람다·컴프리헨션 등은 모두 거부한다.
예: "1 + 14 / (4 + sqrt(P/1000))", "average > 3785.41"
"""
import ast
import math
import operator
from functools import lru_cache

FUNCS = {"sqrt": math.sqrt, "log": math.log, "log10": math.log10, "exp": math.exp,
         "min": min, "max": max, "abs": abs}

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
_CMP = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
        ast.Eq: operator.eq, ast.NotEq: operator.ne}
MAX_LEN = 300


class ExprError(ValueError):
    pass


@lru_cache(maxsize=256)
def _parse(src):
    if not isinstance(src, str) or len(src) > MAX_LEN:
        raise ExprError("수식은 %d자 이하 문자열: %r" % (MAX_LEN, src))
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ExprError("수식 문법 오류: %r (%s)" % (src, e.msg)) from None
    _check(tree.body, src)
    return tree.body


def _check(node, src):
    """허용 노드만 있는지 파싱 시점에 검사 (계산 전에 거부)."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ExprError("숫자 상수만 허용: %r" % src)
    elif isinstance(node, ast.Name):
        pass
    elif isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        _check(node.left, src), _check(node.right, src)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        _check(node.operand, src)
    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            _check(v, src)
    elif isinstance(node, ast.Compare) and all(type(o) in _CMP for o in node.ops):
        for v in (node.left, *node.comparators):
            _check(v, src)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS or node.keywords:
            raise ExprError("허용되지 않은 함수 호출: %r (허용: %s)" % (src, ", ".join(sorted(FUNCS))))
        for a in node.args:
            _check(a, src)
    else:
        raise ExprError("허용되지 않은 구문 %s: %r" % (type(node).__name__, src))


def _eval(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ExprError("알 수 없는 변수 %r (사용 가능: %s)" % (node.id, ", ".join(sorted(env))))
        return env[node.id]
    if isinstance(node, ast.BinOp):
        left, right = _eval(node.left, env), _eval(node.right, env)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ExprError("거듭제곱 지수가 너무 큼: %r" % right)
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        return _UNARY[type(node.op)](_eval(node.operand, env))
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval(v, env) for v in node.values)
        return any(_eval(v, env) for v in node.values)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, env)
            if not _CMP[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        return FUNCS[node.func.id](*(_eval(a, env) for a in node.args))
    raise ExprError("허용되지 않은 구문 %s" % type(node).__name__)  # _check 를 통과했으면 오지 않음


def evaluate(src, env):
    """수식 src 를 변수 env(이름 → 숫자)로 계산한다. 허용되지 않은 구문이면 ExprError."""
    return _eval(_parse(src), {k: v for k, v in env.items() if isinstance(v, (int, float)) and not isinstance(v, bool)})


def validate(src):
    """계산하지 않고 문법·허용 구문만 확인한다 (규칙·사업 파일 검사용)."""
    _parse(src)
