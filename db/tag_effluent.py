"""방류수질 법령값(criteria/effluent_limits.csv) → 정규화 태그(criteria/normalized/effluent/effluent_limits.jsonl).

CSV 는 원문 표기 그대로 둔다(engine/plant.py 가 그대로 읽는다). 태그는 나라 간 비교·DB 적재용:
- param_key: 수질 항목 표준 키 (BOD 일수가 원문에 없으면 bod, 5일이면 bod5 — 바꿔 부르지 않는다)
- 값: 나라별 숫자 표기(콜롬비아 소수점 쉼표 '0,50', 한국 천 단위 쉼표 '1,000', '<50', '6.0-9.0')를 수치로
- limit_kind: max | min(제거율 하한) | range(pH), strict: 원문이 '<'(미만)
- unit: SI 표기 통일, averaging: avg_7d | avg_30d | unspecified
- condition: 원 키 유지, 처리용량·BOD 부하 구간은 범위 객체, 적용기간은 effective_from/effective_to
- legal_status: law | regulation | court_order, stayed: 법원이 시행을 정지한 규칙
기존 태그는 덮어쓴다(규칙이 결정적이라 손 태그 없음). 사용: py -3 db/tag_effluent.py [--check]
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "criteria" / "effluent_limits.csv"
OUT = ROOT / "criteria" / "normalized" / "effluent" / "effluent_limits.jsonl"

LAWS = [  # (원문 법령명 앞부분, law_id, legal_status, stayed)
    ("하수도법 시행규칙", "KR_SEWERAGE_ACT_RULE_ANNEX1", "law", False),
    ("40 CFR Part 133", "US_40CFR133", "regulation", False),
    ("Environment (Protection) Amendment Rules, 2017", "IN_EP_RULES_GSR1265E_2017", "law", True),
    ("NGT Principal Bench order, O.A. No. 1069/2018", "IN_NGT_OA1069_2018", "court_order", False),
    ("Resolución 0631 de 2015", "CO_RES_0631_2015", "regulation", False),
]

PARAMS = [  # (정규식, param_key) — 위에서부터 첫 일치
    (r"percent removal", None),  # 아래 REMOVAL 에서 처리
    (r"^CBOD5", "cbod5"), (r"^BOD5$|^DBO5", "bod5"), (r"^BOD", "bod"),
    (r"^COD$|^DQO", "cod"), (r"^TOC", "toc"),
    (r"^SS |^SS$|^TSS$|^SST ", "tss"), (r"^SSED", "settleable_solids"),
    (r"^T-N|^Nitrogen-Total", "tn"), (r"^T-P|^Phosphorus-Total", "tp"),
    (r"^총대장균군", "total_coliform"), (r"^Fecal Coliform", "fecal_coliform"),
    (r"^pH$", "ph"), (r"^생태독성", "ecotoxicity_daphnia"), (r"^Grasas y Aceites", "oil_grease"),
    (r"^Cianuro", "cyanide_total"), (r"^Cadmio", "cadmium"), (r"^Cinc", "zinc"), (r"^Cobre", "copper"),
    (r"^Cromo", "chromium"), (r"^Mercurio", "mercury"), (r"^Níquel", "nickel"), (r"^Plomo", "lead"),
    (r"^HAP", "pah"),
]
REMOVAL = [(r"^CBOD5", "cbod5_removal"), (r"^BOD5", "bod5_removal"), (r"^SS ", "tss_removal")]

UNITS = [(r"^mg/L", "mg/L"), (r"^개/mL$", "count/mL"), (r"^MPN/100 ?mL$", "MPN/100mL"), (r"^TU$", "TU"),
         (r"^mL/L$", "mL/L"), (r"pH", "pH"), (r"^% removal", "percent")]


def row_key(x):
    raw = "|".join([x["country"], x["law"], x["article"], x["parameter"], x["condition"].strip(), x["value_max"]])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def first(table, s, what):
    for pat, v in table:
        if re.search(pat, s):
            return v
    raise ValueError("%s 해석 불가: %s" % (what, s))


def num(t, country):
    t = t.strip()
    if country == "CO":  # 콜롬비아: 소수점 쉼표, 천 단위 없음
        t = t.replace(".", "").replace(",", ".")
    else:  # 한국·미국·인도: 쉼표는 천 단위
        t = t.replace(",", "")
    return float(t)


def value(x):
    s, c = x["value_max"].strip(), x["country"]
    m = re.fullmatch(r"([\d.,]+)\s*(?:-|a)\s*([\d.,]+)", s)
    if m:
        return num(m.group(1), c), num(m.group(2), c), "range", False
    m = re.fullmatch(r"(<)?\s*([\d.,]+)", s)
    if not m:
        raise ValueError("값 해석 불가: %r" % s)
    v = num(m.group(2), c)
    if x["unit"].startswith("% removal"):
        return v, None, "min", False
    return None, v, "max", bool(m.group(1))


def band(s):
    """'>=500', '50~<500', '<50', '<=625', '>625 y <=3000', '>3000' → 범위 객체."""
    out = {}
    for op, v in re.findall(r"(>=|<=|>|<|~<|~)?\s*(\d+)", s.replace(" y ", " ")):
        key = {">=": "ge", "<=": "le", ">": "gt", "<": "lt", "~<": "lt", "~": "le"}.get(op, "ge")
        out[key] = int(v)
    if not out:
        raise ValueError("구간 해석 불가: %s" % s)
    return out


def condition(c):
    c = dict(c)
    if "capacity_m3_per_day" in c:
        c["capacity_m3_d"] = band(c.pop("capacity_m3_per_day"))
    if "load_kg_d_DBO5" in c:
        c["load_bod5_kg_d"] = band(c.pop("load_kg_d_DBO5"))
    p = c.pop("period", None)
    if p:
        a, _, b = p.partition("~")
        if a:
            c["effective_from"] = a
        if b:
            c["effective_to"] = b
    if c.get("region") == "전 지역":
        c["region"] = "all"
    return c


def averaging(s):
    if re.search(r"30-day", s):
        return "avg_30d"
    if re.search(r"7-day", s):
        return "avg_7d"
    return "unspecified"


def tag(x):
    law_id, status, stayed = next((i, st, sy) for pre, i, st, sy in LAWS if x["law"].startswith(pre))
    p = x["parameter"]
    pk = first(REMOVAL, p, "제거율 항목") if "percent removal" in p else first(PARAMS, p, "항목")
    lo, hi, kind, strict = value(x)
    raw = json.loads(x["condition"]) if x["condition"].strip() else {}
    t = {"row_key": row_key(x), "law_id": law_id, "legal_status": status, "param_key": pk,
         "value_min": lo, "value_max": hi, "limit_kind": kind, "unit": first(UNITS, x["unit"], "단위"),
         "averaging": averaging(x["averaging"]), "condition": condition(raw)}
    if strict:
        t["strict"] = True
    if stayed:
        t["stayed"] = True
    return t


def build():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    tags = [tag(x) for x in rows]
    keys = [t["row_key"] for t in tags]
    assert len(set(keys)) == len(keys), "row_key 중복"
    return rows, tags


def load_tags():
    return {o["row_key"]: o for o in (json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip())}


def main():
    _, tags = build()
    text = "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tags)
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("일치" if same else "불일치: py -3 db/tag_effluent.py 로 다시 만들 것")
        sys.exit(0 if same else 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print("effluent tags", len(tags))


if __name__ == "__main__":
    main()
