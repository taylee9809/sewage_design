"""재배포 불가 기준 행의 조건·basis에 남은 원문 설명 구절을 한국어 표기로 바꾼다 (row_key 재매핑 포함, 반복 실행 안전).
binding_raw는 핵심 문형어(shall/should/may/must)만 남긴다.
사용: py -3 db/translate_private_phrases.py
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_criteria import row_key  # noqa: E402
from paths import PRIVATE, QUOTES, ROOT  # noqa: E402

KO_FILE = PRIVATE / "criteria_quotes" / "phrase_map.json"  # 원문 구절 → 한국어 (원문 구절이라 비공개 보관)
KO = json.loads(KO_FILE.read_text(encoding="utf-8")) if KO_FILE.exists() else {}
MODAL = re.compile(r"\b(shall not|shall|should|must|may)\b", re.I)


def tr(x):
    if isinstance(x, dict):
        return {k: tr(v) for k, v in x.items()}
    if isinstance(x, list):
        return [tr(v) for v in x]
    return KO.get(x, x) if isinstance(x, str) else x


def main():
    std = json.loads((ROOT / "criteria" / "standards.json").read_text(encoding="utf-8"))
    target = {k for k, v in std.items() if v["redistributable"] == "values_only"}
    remap, changed_rows = {}, 0
    for p in sorted((ROOT / "criteria").glob("*_sewer.csv")):
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        cols = list(rows[0].keys())
        dirty = False
        for r in rows:
            if r["standard_id"] not in target:
                continue
            old = row_key(r)
            if r["condition"]:
                c = json.dumps(tr(json.loads(r["condition"])), ensure_ascii=False)
                if c != r["condition"]:
                    r["condition"] = c
            m = MODAL.search(r["binding_raw"] or "")
            if m and r["binding_raw"] != m.group(1):
                r["binding_raw"] = m.group(1)
            new = row_key(r)
            if new != old:
                remap[old] = new
            changed_rows += 1
            dirty = True
        if dirty:
            tmp = str(p) + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, p)
    # 태그·비공개 보관 파일 키 재매핑, 태그의 조건·basis도 번역
    for p in sorted((ROOT / "criteria" / "normalized").glob("[!_]*.jsonl")):
        out = []
        for l in open(p, encoding="utf-8"):
            if l.strip():
                o = json.loads(l)
                o["row_key"] = remap.get(o["row_key"], o["row_key"])
                o["condition"], o["basis"] = tr(o.get("condition")), tr(o.get("basis"))
                out.append(o)
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            for o in out:
                f.write(json.dumps(o, ensure_ascii=False) + "\n")
        os.replace(tmp, p)
    for p in (QUOTES, PRIVATE / "criteria_quotes" / "fields.csv"):
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        for r in rows:
            r["row_key"] = remap.get(r["row_key"], r["row_key"])
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, p)
    print("rows", changed_rows, "keys remapped", len(remap))


if __name__ == "__main__":
    main()
