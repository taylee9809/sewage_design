"""criteria/*.csv → sewage_design DB (criteria 스키마). 재실행 시 해당 standard_id 행을 지우고 다시 넣는다.

사용: py -3 db/load_criteria.py <공개 DB DSN> [<비공개 DB DSN>]
공개 DB(sewage_design)는 스키마를 새로 만들고 전부 다시 넣는다. 비공개 DB(sewage_design_private)에는 재배포 불가 본문만.
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import psycopg

from paths import ASSET_DIRS, CLAUSE_DIRS, PRIVATE, QUOTES, jsonl_files

ROOT = Path(__file__).resolve().parent.parent

STANDARDS = json.loads((ROOT / "criteria" / "standards.json").read_text(encoding="utf-8"))  # 기준서 메타데이터 (새 기준 = 항목 추가)

# 항목별 계산 단위 (단일 단위 항목만). 행 단위가 다르면 아래 변환표로 맞춘다.
CANON_UNIT = {
    "min_pipe_diameter": "mm", "drop_manhole_threshold": "m", "per_capita_wastewater": "L/c/d",
    "manning_n": "-", "min_velocity": "m/s", "max_velocity": "m/s", "min_slope": "m/m",
    "min_cover": "m", "manhole_max_spacing": "m",
}
CONVERT = {("m", "mm"): 1000.0, ("mm", "m"): 0.001, ("m3/(cap·d)", "L/c/d"): 1000.0,
           ("dimensionless", "-"): 1.0, ("s/m^(1/3)", "-"): 1.0}


def num(s):
    s = (s or "").strip()
    try:
        return float(s) if s else None
    except ValueError:
        return None


def orig_text(r):
    """원문 단위 값. value_min/max가 SI로 들어온 파일(일본·인도)은 단위가 원문과 같을 때만 기록."""
    a, b = (r["value_min"] or "").strip(), (r["value_max"] or "").strip()
    si, base = num(r["value_si"]), num(a) if a else num(b)
    in_orig = si is not None and base not in (None, 0) and abs(si - base) > 1e-9 * max(1.0, abs(si))
    if not in_orig and (r["unit_orig"] or "").strip() not in ("", (r["unit_si"] or "").strip()):
        return None
    v = f"{a}~{b}" if a and b else (a or (f"≤{b}" if b else ""))
    return f"{v} {r['unit_orig']}".strip() if v else None


def normalize(r):
    """CSV마다 value_min/max가 원문 단위(KDS·Ten States)거나 SI(일본·인도)다.
    value_si가 value_min/max와 다르면 원문 단위로 보고 value_si/원문값 비율로 SI 환산."""
    key, unit = r["param_key"], (r["unit_si"] or "").strip()
    lo, hi = num(r["value_min"]), num(r["value_max"])
    si = num(r["value_si"])
    base = lo if lo is not None else hi
    if si is not None and base not in (None, 0) and abs(si - base) > 1e-9 * max(1.0, abs(si)):
        f = si / base
        lo = lo * f if lo is not None else None
        hi = hi * f if hi is not None else None
    canon = CANON_UNIT.get(key)
    if canon and unit and unit != canon:
        f = CONVERT.get((unit, canon))
        if f is None:
            raise ValueError(f"단위 변환 불가: {key} {unit}→{canon}")
        lo = lo * f if lo is not None else None
        hi = hi * f if hi is not None else None
        unit = canon
    return lo, hi, unit or canon


REF_SPLIT = re.compile(r"\s*(?:;|・|～|~)\s*")
REF_TAIL = re.compile(r"\s*(?:Table\s*\S+|表\s*\S+|<표[^>]*>|본문|\(p\.[^)]*\)|解説\(p\.[^)]*\))\s*$")


def load_clause_files():
    out = []
    for f in jsonl_files(CLAUSE_DIRS):
        out += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    return out


def link_clause(ref, nos):
    """수집 시 조항 표기(clause_ref) → 조문 레코드 clause_no. 조각마다 가장 긴 접두 일치를 고른다."""
    for piece in REF_SPLIT.split(ref or ""):
        piece = piece.strip()
        while piece:
            if piece in nos:
                return piece
            best = max((c for c in nos if piece.startswith(c) and piece[len(c):len(c) + 1] in (" ", "(", "（", "第")), key=len, default=None)
            if best:
                return best
            cut = REF_TAIL.sub("", piece)
            if cut == piece:
                break
            piece = cut
    return None


def row_key(r):
    """CSV 행의 안정 키 (재적재해도 같음). 정규화 파일(criteria/normalized/*.jsonl)과 연결하는 데 쓴다."""
    raw = "|".join([r["standard_id"], r["param_key"], (r["condition"] or "").strip(), r["clause_no"] or "",
                    r["value_min"] or "", r["value_max"] or "", r["value_text"] or ""])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def load_normalized():
    out = {}
    d = ROOT / "criteria" / "normalized"
    for f in sorted(d.glob("[!_]*.jsonl")) if d.exists() else []:
        for l in open(f, encoding="utf-8"):
            if l.strip():
                o = json.loads(l)
                out[o["row_key"]] = o
    return out


def main(dsn, dsn_private=None):
    rows = []
    for f in sorted((ROOT / "criteria").glob("*_sewer.csv")):  # 기준값 CSV (새 기준 = 파일 추가)
        rows += list(csv.DictReader(open(f, encoding="utf-8")))
    clauses = load_clause_files()
    norm = load_normalized()
    keys = [row_key(r) for r in rows]
    assert len(set(keys)) == len(keys), "row_key 중복"
    # 공개 CSV에서 뺀 원문 구절은 비공개 폴더에서 DB에만 채운다 (rows를 바꾸면 _rows_for_tagging.jsonl로 새어 나감)
    private_quotes = ({o["row_key"]: o["quote_short"] for o in csv.DictReader(open(QUOTES, encoding="utf-8"))}
                      if QUOTES.exists() else {})
    # 공개 CSV에서 뺀 원문 문장(값 설명·메모)도 DB에만 채운다 (db/scrub_private_text.py)
    pf = PRIVATE / "criteria_quotes" / "fields.csv"
    private_fields = ({(o["row_key"], o["column"]): o["value"] for o in csv.DictReader(open(pf, encoding="utf-8"))}
                      if pf.exists() else {})
    with psycopg.connect(dsn) as con, con.cursor() as cur:
        cur.execute((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
        cur.execute("SET search_path = criteria, public")
        for sid, m in STANDARDS.items():
            cur.execute("""INSERT INTO standard (standard_id,country,issuer,title,edition,effective_date,is_latest,access,
                             redistributable,license_note,source_url,note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (sid, m["country"], m["issuer"], m["title"], m["edition"], m["effective_date"], m["is_latest"],
                         m["access"], m["redistributable"], m["license_note"], m["source_url"], m.get("note")))
        for key in sorted({r["param_key"] for r in rows}):
            cur.execute("INSERT INTO parameter (param_key, unit_si) VALUES (%s,%s)", (key, CANON_UNIT.get(key)))

        # 조문: 재배포 가능한 기준만 본문 포함
        ids = {}
        for c in clauses:
            public_body = STANDARDS[c["standard_id"]]["redistributable"] == "full_text"
            cur.execute("""INSERT INTO clause (standard_id,clause_no,clause_title,parent_no,seq,page,lang,body_text,source_url)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING clause_id""",
                        (c["standard_id"], c["clause_no"], c.get("clause_title"), c.get("parent_no"), c.get("seq"),
                         None if c.get("page") is None else str(c["page"]), c.get("lang"),
                         c.get("body_text") if public_body else None, c.get("source_url")))
            ids[(c["standard_id"], c["clause_no"])] = cur.fetchone()[0]
        nos_by_std = {}
        for sid, no in ids:
            nos_by_std.setdefault(sid, set()).add(no)

        n_asset = 0
        private_assets = []
        for f in jsonl_files(ASSET_DIRS):
            for l in open(f, encoding="utf-8"):
                if not l.strip():
                    continue
                a = json.loads(l)
                if STANDARDS[a["standard_id"]]["redistributable"] != "full_text":  # 판독본도 원문 복제라 비공개 DB로
                    private_assets.append(a)
                    a = {k: (None if k in ("text", "latex", "data") else v) for k, v in a.items()}
                cur.execute("""INSERT INTO asset (asset_id,standard_id,clause_id,kind,label,text,latex,data,confidence,note)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (a["asset_id"], a["standard_id"], ids.get((a["standard_id"], a.get("clause_no"))), a.get("kind"),
                             a.get("label"), a.get("text"), a.get("latex"),
                             json.dumps(a["data"], ensure_ascii=False) if a.get("data") is not None else None,
                             a.get("confidence"), a.get("note")))
                n_asset += 1
        print("assets", n_asset)

        n_pipe = 0
        for f in sorted((ROOT / "criteria" / "pipe_catalog").glob("*.csv")):
            for r in csv.DictReader(open(f, encoding="utf-8")):
                cur.execute("""INSERT INTO pipe_catalog VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (r["country"], r["material"], r["product_type"], r["standard_ref"], num(r["nominal_mm"]),
                             num(r["inner_mm"]), num(r["outer_mm"]), num(r["wall_mm"]), r["class_or_stiffness"] or None,
                             r["source_url"] or None, r["source_type"] or None, r["retrieved_at"] or None, r["note"] or None))
                n_pipe += 1
        print("pipe_catalog", n_pipe)

        unlinked = []
        for r in rows:
            lo, hi, unit = normalize(r)
            cond = json.loads(r["condition"]) if (r["condition"] or "").strip() else None
            cj = json.dumps(cond, ensure_ascii=False) if cond is not None else None
            nz = norm.get(row_key(r), {})
            ncond = json.dumps(nz["condition"], ensure_ascii=False) if nz.get("condition") is not None else None
            b = dict(nz["basis"]) if nz.get("basis") is not None else None
            if b is not None and private_fields.get((row_key(r), "basis_note")):
                b["note"] = private_fields[(row_key(r), "basis_note")]
            nbasis = json.dumps(b, ensure_ascii=False) if b is not None else None
            no = link_clause(r["clause_no"], nos_by_std.get(r["standard_id"], set()))
            if no is None:
                unlinked.append((r["standard_id"], r["clause_no"]))
            cur.execute("""INSERT INTO criterion (row_key,standard_id,param_key,condition_raw,condition,basis,value_min,value_max,unit_si,value_text,
                             orig_value,unit_orig,binding,binding_raw,clause_id,clause_ref,quote_short,source_url,retrieved_at,note)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (row_key(r), r["standard_id"], r["param_key"], cj, ncond, nbasis, lo, hi, unit or None,
                         private_fields.get((row_key(r), "value_text")) or r["value_text"] or None,
                         orig_text(r), private_fields.get((row_key(r), "unit_orig")) or r["unit_orig"] or None, r["binding"],
                         r.get("binding_raw") or None,
                         ids.get((r["standard_id"], no)), r["clause_no"] or None,
                         r["quote_short"] or private_quotes.get(row_key(r)) or None,
                         r["source_url"] or None, r["retrieved_at"] or None,
                         private_fields.get((row_key(r), "note")) or r["note"] or None))
        cur.execute("""SELECT s.standard_id, s.redistributable,
                              (SELECT count(*) FROM clause c WHERE c.standard_id=s.standard_id),
                              (SELECT count(*) FROM clause c WHERE c.standard_id=s.standard_id AND c.body_text IS NOT NULL),
                              (SELECT count(*) FROM criterion k WHERE k.standard_id=s.standard_id),
                              (SELECT count(*) FROM criterion k WHERE k.standard_id=s.standard_id AND k.clause_id IS NOT NULL)
                       FROM standard s ORDER BY 1""")
        print("standard | redistributable | clauses | public_body | criteria | linked")
        for row in cur.fetchall():
            print(" | ".join(map(str, row)))
        print("unlinked", len(unlinked), unlinked[:20])
        print("normalized", sum(1 for r in rows if row_key(r) in norm), "/", len(rows))
        nd = ROOT / "criteria" / "normalized"
        nd.mkdir(exist_ok=True)
        with open(nd / "_rows_for_tagging.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"row_key": row_key(r), **{k: r[k] for k in ("standard_id", "param_key", "condition", "value_min",
                        "value_max", "unit_orig", "value_si", "unit_si", "value_text", "clause_no", "clause_title", "quote_short", "note")}},
                        ensure_ascii=False) + "\n")

    if dsn_private:  # 재배포 불가 본문 보관
        with psycopg.connect(dsn_private) as con, con.cursor() as cur:
            cur.execute((ROOT / "db" / "schema_private.sql").read_text(encoding="utf-8"))
            n = 0
            for c in clauses:
                if STANDARDS[c["standard_id"]]["redistributable"] != "full_text":
                    cur.execute("""INSERT INTO source.clause_body (standard_id,clause_no,clause_title,parent_no,seq,page,lang,body_text,source_url)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (c["standard_id"], c["clause_no"], c.get("clause_title"), c.get("parent_no"), c.get("seq"),
                                 None if c.get("page") is None else str(c["page"]), c.get("lang"), c.get("body_text"), c.get("source_url")))
                    n += 1
            print("private bodies", n)
            cur.execute("""CREATE TABLE source.asset (asset_id text PRIMARY KEY, standard_id text, clause_no text, kind text,
                             label text, text text, latex text, data jsonb, confidence text, note text, file text, page text)""")
            for a in private_assets:
                cur.execute("INSERT INTO source.asset VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (a["asset_id"], a["standard_id"], a.get("clause_no"), a.get("kind"), a.get("label"), a.get("text"),
                             a.get("latex"), json.dumps(a["data"], ensure_ascii=False) if a.get("data") is not None else None,
                             a.get("confidence"), a.get("note"), a.get("file"), None if a.get("page") is None else str(a["page"])))
            print("private assets", len(private_assets))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
