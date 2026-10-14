"""재배포 불가 기준의 원문 문장을 공개 CSV·태그 파일에서 비공개 폴더로 옮긴다 (여러 번 돌려도 같은 결과).

대상: criteria/standards.json에서 redistributable == "values_only"인 기준.
- 공개 CSV: value_text → "[비공개 원문 ref:<원래 row_key>]"(값 칸 숫자는 그대로), note·clause_title·quote_short → 빈칸
- 비공개: <PRIVATE>/criteria_quotes/fields.csv (row_key, standard_id, column, value) — 적재 때 DB에만 채운다
- row_key가 바뀌므로 normalized/*.jsonl과 quotes.csv의 키도 새 키로 바꾸고, 태그 메모(tag_note)도 비공개로 옮긴다
사용: py -3 db/scrub_private_text.py
"""
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_criteria import row_key  # noqa: E402
from paths import PRIVATE, QUOTES, ROOT  # noqa: E402

FIELDS = PRIVATE / "criteria_quotes" / "fields.csv"
COLS = ("value_text", "note", "clause_title")
MARK = "[비공개 원문 ref:"


def write_csv(p, rows, cols):
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)


def main():
    std = json.loads((ROOT / "criteria" / "standards.json").read_text(encoding="utf-8"))
    target = {k for k, v in std.items() if v["redistributable"] == "values_only"}
    fields = list(csv.DictReader(open(FIELDS, encoding="utf-8"))) if FIELDS.exists() else []
    have = {(f["row_key"], f["column"]) for f in fields}
    quotes = list(csv.DictReader(open(QUOTES, encoding="utf-8")))
    qcols = list(quotes[0].keys())
    remap, moved = {}, 0
    for p in sorted((ROOT / "criteria").glob("*_sewer.csv")):
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        cols = list(rows[0].keys())
        changed = False
        for r in rows:
            if r["standard_id"] not in target or ((r["value_text"] or "").startswith(MARK) or not r["value_text"])                     and not (r["note"] or r["clause_title"] or r["quote_short"] or len((r["unit_orig"] or "").split()) >= 3):
                continue
            old = row_key(r)
            saved = {c: r[c] for c in COLS if r[c] and not (c == "value_text" and r[c].startswith(MARK))}
            if r["value_text"] and not r["value_text"].startswith(MARK):
                r["value_text"] = "%s%s]" % (MARK, old)
            new = row_key(r)
            for c, v in saved.items():
                if (new, c) not in have:
                    fields.append({"row_key": new, "standard_id": r["standard_id"], "column": c, "value": v})
                    have.add((new, c))
            if r["quote_short"]:
                quotes.append({**{c: "" for c in qcols}, "row_key": new, "standard_id": r["standard_id"],
                               "clause_no": r["clause_no"], "quote_short": r["quote_short"]})
            uo = r["unit_orig"] or ""
            if len(uo.split()) >= 3:  # 단위 뒤에 붙은 원문 설명 구절
                if (new, "unit_orig") not in have:
                    fields.append({"row_key": new, "standard_id": r["standard_id"], "column": "unit_orig", "value": uo})
                    have.add((new, "unit_orig"))
                r["unit_orig"] = uo.split()[0]
            r["note"] = r["clause_title"] = r["quote_short"] = ""
            if old != new:
                remap[old] = new
            moved += 1
            changed = True
        if changed:
            write_csv(p, rows, cols)
    for q in quotes:
        q["row_key"] = remap.get(q["row_key"], q["row_key"])
    write_csv(QUOTES, quotes, qcols)
    # 대상 기준 행의 (새) 키 목록
    target_keys = set()
    for p in sorted((ROOT / "criteria").glob("*_sewer.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if r["standard_id"] in target:
                target_keys.add(row_key(r))
    # 태그 파일: 키 교체 + 대상 기준의 tag_note는 비공개로
    tagged = 0
    for p in sorted((ROOT / "criteria" / "normalized").glob("[!_]*.jsonl")):
        out, changed = [], False
        for l in open(p, encoding="utf-8"):
            if not l.strip():
                continue
            o = json.loads(l)
            k = remap.get(o["row_key"], o["row_key"])
            bn = (o.get("basis") or {}).get("note")
            if bn and k in target_keys:
                if (k, "basis_note") not in have:
                    fields.append({"row_key": k, "standard_id": "", "column": "basis_note", "value": bn})
                    have.add((k, "basis_note"))
                o["basis"].pop("note")
                changed = True
            if k != o["row_key"] or (k in {f["row_key"] for f in fields} and o.get("tag_note")):
                if o.get("tag_note") and (k, "tag_note") not in have:
                    fields.append({"row_key": k, "standard_id": "", "column": "tag_note", "value": o["tag_note"]})
                    have.add((k, "tag_note"))
                o["row_key"], o["tag_note"] = k, ""
                changed = True
                tagged += 1
            out.append(o)
        if changed:
            tmp = str(p) + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                for o in out:
                    f.write(json.dumps(o, ensure_ascii=False) + "\n")
            os.replace(tmp, p)
    FIELDS.parent.mkdir(parents=True, exist_ok=True)
    write_csv(FIELDS, fields, ["row_key", "standard_id", "column", "value"])
    print("rows moved", moved, "keys remapped", len(remap), "tags", tagged, "private fields", len(fields))


if __name__ == "__main__":
    main()
