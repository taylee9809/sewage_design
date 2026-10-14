"""일반 엔진: 기준별 규칙(criteria/rules/<standard_id>.json) + 기준값(DB criterion) + 사업 채택값(criteria/projects/<id>.json)만으로 동작.

나라 이름으로 분기하는 코드가 없어야 한다. 새 기준 = rules JSON 1개 + criterion 행 INSERT.
규칙 유형(rule type)은 db/rule_types.md / 노션 '규칙 유형 사전' 참고. 모르는 유형이 나오면 오류로 알린다(새 유형 추가 필요).
"""
import json
import math
from dataclasses import dataclass
from pathlib import Path

from engine import criteria_db as db
from engine import hydraulics as h

ROOT = Path(__file__).resolve().parent.parent
KNOWN_TYPES = {"VELOCITY_MIN", "VELOCITY_MAX", "SLOPE_TABLE", "CAPACITY", "MIN_DIAMETER", "MIN_COVER", "JUNCTION",
               "MANHOLE_SPACING", "NO_DECREASE", "LOW_FLOW_FALLBACK", "DESIGN_FLOW",
               "WALL_SHEAR_MIN",       # v2 (2026-10-14, 콜롬비아 RAS Art.141)
               "MONOTONIC_DOWNSTREAM",
               # v3 (2026-10-15) 펌프장·압송관
               "PUMP_TRIGGER", "FORCE_MAIN_VELOCITY", "FORCE_MAIN_FRICTION", "FORCE_MAIN_MIN_DIAMETER", "PUMP_COUNT",
               "WET_WELL_VOLUME", "PUMP_HEAD_POWER"}  # v2 (2026-10-14, KDS 1.3 본문·요코하마 3.5.4: 하류로 경사 점감·유속 점증)
REQUIRED = ("mandatory", "standard")


@dataclass
class Req:
    """요구 최소경사 후보."""
    slope: float
    kind: str        # velocity | capacity | table
    reason: str
    clause: str
    binding: str


def _cap_slope(D, n, Q, yr):
    return (Q * n / (h.area(D, yr) * h.hydraulic_radius(D, yr) ** (2 / 3))) ** 2


def _range_ok(spec, x):
    return all({"eq": x == v, "ge": x >= v, "gt": x > v, "le": x <= v, "lt": x < v}[op] for op, v in spec.items() if v is not None)


class Standard:
    def __init__(self, standard_id, project, dsn=None):
        spec = json.loads((ROOT / "criteria" / "rules" / ("%s.json" % standard_id)).read_text(encoding="utf-8"))
        unknown = {r["type"] for r in spec["rules"]} - KNOWN_TYPES
        if unknown:
            raise NotImplementedError("새 규칙 유형 필요: %s" % unknown)
        self.sid, self.spec, self.dsn = standard_id, spec, dsn
        self.rows = db.load(standard_id, dsn)
        fsid = spec.get("flow_standard_id")
        self.flow_rows = db.load(fsid, dsn) if fsid else self.rows
        psid = spec.get("pump_standard_id")  # 펌프장 기준이 별도 코드인 경우(KDS 61 45 00)
        self.pump_rows = db.load(psid, dsn) if psid else self.rows
        self.choice = {k: v["value"] for k, v in project["standards"].get(standard_id, {}).items()}
        self.material = project.get("material", "pvc")
        self.by_type = {}
        for r in spec["rules"]:
            self.by_type.setdefault(r["type"], []).append(r)
        got = db.pick(self.rows, "manning_n", {"material": self.material, "shape": "circular"})
        if got:
            self.n, self.n_clause = got[0].value_min, got[0].clause_ref
        else:  # 원문에 조도계수 수치가 없으면 사업 채택값
            self.n, self.n_clause = self.choice["manning_n"], "사업 채택값(원문 수치 없음)"

    # ── 공통 도우미 ──
    def rule(self, t):
        got = self.by_type.get(t, [])
        return got[0] if got else None

    def _pick(self, r, ctx, rows=None, basis=None):
        return [x for x in db.pick(rows or self.rows, r["param"], {**r.get("cond", {}), **ctx}, basis=basis or r.get("basis"),
                                   allow=tuple(r.get("allow", ()))) if x.binding in REQUIRED]

    def _choice(self, key, row=None):
        v = self.choice[key]
        if v == "max":
            return row.value_max
        if v == "min":
            return row.value_min
        return v

    def design_depth(self):
        r = self.rule("CAPACITY")
        if r and r["kind"] == "depth_ratio":
            row = db.one(self.rows, r["param"], r["cond"])
            return row.value_max or row.value_min, row.clause_ref
        return 1.0, None

    # ── 관 규격 ──
    def pipe_sizes(self, cur):
        cur.execute("SELECT nominal_mm::float, min(inner_mm)::float FROM criteria.pipe_catalog WHERE country=%%s AND material=%%s "
                    "AND inner_mm IS NOT NULL AND (%s) GROUP BY 1 ORDER BY 1" % self.choice["pipe_product"].replace("%", "%%"),
                    (self.country(cur), self.material))
        rows = cur.fetchall()
        if self.spec["pipe"]["nominal"] == "inch25":  # 인치 규격 → 기준 표의 mm 표기(1 in = 25 mm 관례)
            return [(round(a / 25.4 * 25), b) for a, b in rows]
        return [(round(a), b) for a, b in rows]

    def country(self, cur):
        cur.execute("SELECT country FROM criteria.standard WHERE standard_id=%s", (self.sid,))
        return cur.fetchone()[0]

    def dia_compare(self, nom, inner):
        m = self.spec["pipe"]["min_dia_compare"]
        return inner if m == "inner" else (nom / 25 * 25.4 if m == "inch_mm" else nom)

    def table_label(self, nom, inner):
        if self.spec["pipe"]["table_lookup"] != "nearest_inner":
            return nom
        sizes = set()
        for r in self.by_type.get("SLOPE_TABLE", []):
            for x in db.pick(self.rows, r["param"], r.get("cond", {})):
                d = x.condition.get("dia_mm", {})
                sizes.update(v for k, v in d.items() if k in ("eq", "ge", "gt") and v)
        return min(sizes, key=lambda x: abs(x - inner))

    def min_diameter(self):
        r = self.rule("MIN_DIAMETER")
        return max(x.value_min for x in self._pick(r, {}))

    # ── 설계유량 ──
    def avg_flow(self, P):
        """첨두계수를 빼고 침입수·하한 없이 본 평균 유량 (습정 충수·체류 판정용)."""
        return self.peak_flow(P, peak=False)

    def peak_flow(self, P, peak=True):
        if P <= 0:
            return 0.0
        r = self.rule("DESIGN_FLOW")
        pc = r["per_capita"]
        if pc.get("source") == "project":
            q = self.choice[pc["key"]]
        elif pc.get("kind") == "product":  # 예: 순급수원단위(표고별) × 회귀계수
            q = 1.0
            for f in pc["factors"]:
                ctx = {**f.get("cond", {}), **{k: self.choice[v] for k, v in f.get("ctx_from_project", {}).items()}}
                row = db.one(self.flow_rows, f["param"], ctx, allow=tuple(f.get("allow", ())))
                q *= row.value_max if row.value_max is not None else row.value_min
        else:
            q = db.one(self.flow_rows, pc["param"], pc["cond"], basis=pc.get("basis"), allow=tuple(pc.get("allow", ()))).value_min
        inf = r["infiltration"]
        f_inf = 1.0
        if inf["kind"] == "ratio_project":
            f_inf += self._choice(inf["key"], db.one(self.flow_rows, inf["param"], inf.get("cond", {})))
        pk = r["peak"]
        if not peak:
            return P * q / 1000 / 86400 * f_inf
        if pk["kind"] == "range_project":
            pf = self._choice(pk["key"], db.one(self.flow_rows, pk["param"], pk.get("cond", {})))
        elif pk["kind"] == "formula":
            pf = eval(pk["expr"], {"__builtins__": {}}, {"sqrt": math.sqrt, "P": P})
        elif pk["kind"] == "range_clamp_project":  # 원문은 범위만, 산정식은 사업 채택 → 범위로 자름
            row = db.one(self.flow_rows, pk["param"], pk.get("cond", {}))
            pf = min(max(eval(self.choice[pk["key"]], {"__builtins__": {}}, {"sqrt": math.sqrt, "P": P}), row.value_min), row.value_max)
        elif pk["kind"] == "table_by_population":
            pf = db.pick(self.flow_rows, pk["param"], {**pk.get("cond", {}), "served_population": P})[0].value_min
        else:
            pf = 1.0
        Q = P * q / 1000 / 86400 * f_inf * pf
        fl = r.get("floor")
        if fl:  # 구간 최소 설계유량 (L/s)
            Q = max(Q, db.one(self.flow_rows, fl["param"], fl.get("cond", {})).value_min / 1000)
        return Q

    # ── 요구 최소경사 ──
    def requirements(self, label, inner, Q, Qi):
        D = inner / 1000
        ctx = {"dia_mm": label, "material": self.material, "shape": "circular"}
        out = []
        for r in self.by_type.get("VELOCITY_MIN", []):
            for row in self._pick(r, ctx):
                v, flow = row.value_min, (Qi if r["flow"] == "initial" else Q)
                if r["state"] == "actual":
                    s = h.slope_for_velocity_at_flow(D, self.n, v, max(flow, 1e-6))
                else:
                    yr = self.design_depth()[0] if r["state"] == "design_depth" else 1.0
                    s = h.slope_for_velocity(D, self.n, v, yr)
                out.append(Req(s, "velocity", "유속 %.2f m/s 이상 (%s, %s 유량) — %s, n=%.3f(%s)"
                               % (v, r["state"], r["flow"], r.get("resolution", ""), self.n, self.n_clause), row.clause_ref, row.binding))
        for r in self.by_type.get("WALL_SHEAR_MIN", []):
            for row in self._pick(r, ctx):
                for fname in r["flows"]:
                    flow = Qi if fname == "initial" else Q
                    s = h.slope_for_shear_at_flow(D, self.n, row.value_min, max(flow, 1e-6))
                    out.append(Req(s, "velocity", "벽면 전단응력 %.1f Pa 이상 (실수심, %s 유량) — n=%.3f(%s)"
                                   % (row.value_min, fname, self.n, self.n_clause), row.clause_ref, row.binding))
        for r in self.by_type.get("SLOPE_TABLE", []):
            for row in self._pick(r, ctx):
                out.append(Req(row.value_min, "table", "최소경사표", row.clause_ref, row.binding))
        r = self.rule("CAPACITY")
        if r:
            if r["kind"] == "depth_ratio":
                yr, cl = self.design_depth()
                out.append(Req(_cap_slope(D, self.n, max(Q, 1e-6), yr), "capacity", "설계수심 y/D≤%.1f로 통수" % yr, cl, "standard"))
            elif r["kind"] == "margin":
                m = db.one(self.rows, r["param"], r["cond"])
                out.append(Req(_cap_slope(D, self.n, max(Q, 1e-6) * (1 + m.value_min), 1.0), "capacity",
                               "계획하수량×(1+여유 %.0f%%) 만관 통수" % (m.value_min * 100), m.clause_ref, m.binding))
            else:
                out.append(Req(_cap_slope(D, self.n, max(Q, 1e-6), 1.0), "capacity", "만관 이내 통수", r.get("clause", ""), "standard"))
        return out

    def fallback(self):
        r = self.rule("LOW_FLOW_FALLBACK")
        return r

    # ── 유속 판정·상한 ──
    def vmax(self):
        r = self.rule("VELOCITY_MAX")
        row = db.pick(self.rows, r["param"], r.get("cond", {}))[0]
        return row.value_max, r["state"], r["enforce"]

    def velocity(self, D, S, Q, state):
        if state == "actual":
            yr = h.depth_ratio_for_flow(D, S, self.n, Q) if Q > 0 else None
            return h.velocity(D, S, self.n, yr) if yr else h.velocity(D, S, self.n)
        return h.velocity(D, S, self.n, self.design_depth()[0] if state == "design_depth" else 1.0)

    def v_check(self, D, S, Q):
        """기준이 정한 판정 유속(VELOCITY_MIN의 상태)."""
        st = (self.by_type.get("VELOCITY_MIN") or self.by_type["VELOCITY_MAX"])[0]["state"]
        return self.velocity(D, S, Q, st)

    # ── 토피·접합·맨홀·관경 감소 ──
    def cover(self, dia):
        r = self.rule("MIN_COVER")
        if r["kind"] == "value":
            ctx = {**r["cond"], **{k: self.choice[v] for k, v in r.get("cond_from_project", {}).items()}}
            return db.one(self.rows, r["param"], ctx, allow=tuple(r.get("allow", ()))).value_min
        if r["kind"] == "project":
            return self.choice[r["key"]]
        role = next(x["role"] for x in r["roles"] if _range_ok({k: v for k, v in x.items() if k != "role"}, dia))
        return max(x.value_min for x in self._pick(r, {"pipe_role": role, "dia_mm": dia}) if x.value_min is not None)

    def junction(self, u_inv_dn, u_D, D):
        r = self.rule("JUNCTION")
        kind = self.choice["junction"] if r["kind"] == "project_choice" else r["kind"]
        if kind == "crown":
            drop = 0.0
            if "min_drop_param" in r:  # 관정 간 최소 낙차 (원문 조건부 규정을 항상 적용 — resolution 참고)
                drop = db.one(self.rows, r["min_drop_param"], {"joint_method": "crown"}, allow=("joint_method", "exception")).value_min
            return u_inv_dn + u_D - D - drop
        if kind == "depth_ratio":
            k = r["ratio"]
            return u_inv_dn + k * u_D - k * D
        raise NotImplementedError("접합 방식 %s" % kind)

    def spacing(self, dia):
        r = self.rule("MANHOLE_SPACING")
        rh = r.get("receives_house_connections")
        ctx = {"dia_mm": dia}
        allow = ()
        if rh is not None:
            ctx["receives_house_connections"] = rh
            allow = ("receives_house_connections", "pipe_role", "exception")
        got = [x for x in db.pick(self.rows, r["param"], ctx, allow=allow) if x.binding in REQUIRED
               and (rh is None or x.condition.get("receives_house_connections") == rh)]
        return min(x.value_max for x in got) if got else None

    def monotonic(self):
        """하류 경사 점감·유속 점증 규칙과 구속력(원문 행에서). 기준 단계는 사업 예외(allow_slope_increase)가 없으면 적용."""
        r = self.rule("MONOTONIC_DOWNSTREAM")
        if not r:
            return None
        rows = [x for x in self.rows if x.param_key == r["param"]]
        binding = rows[0].binding if rows else "standard"
        if binding not in ("mandatory", "standard") or (binding == "standard" and "allow_slope_increase" in self.choice):
            return None
        return {**r, "binding": binding}

    def no_decrease(self):
        r = self.rule("NO_DECREASE")
        return r["enforce"] if r else None
