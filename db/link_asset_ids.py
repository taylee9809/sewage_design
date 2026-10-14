"""이미지 판독 파일(criteria/assets/*.jsonl)의 asset_id를 조문 본문 표시에 붙인다.

'[図: 캡션]' → '[図 #<asset_id>: 캡션]', '[Figure: 캡션]' → '[Figure #<asset_id>: 캡션]'.
판독 행의 placeholder(원래 표시 문자열)와 occurrence_in_clause(조문 안 순번)로 위치를 찾는다. 이미 id가 붙은 표시는 건너뛴다.
사용: py -3 db/link_asset_ids.py
"""
import json
import os
from pathlib import Path

from paths import ASSET_DIRS, CLAUSE_DIRS, jsonl_files



def tagged(placeholder, aid):
    head, sep, rest = placeholder[1:].partition(":")
    if not sep:  # '[이미지]' 처럼 캡션 없는 표시
        return "[%s #%s]" % (placeholder[1:-1], aid)
    return "[%s #%s:%s" % (head, aid, rest)


def main():
    assets = {}
    for f in jsonl_files(ASSET_DIRS):
        for l in open(f, encoding="utf-8"):
            if l.strip():
                a = json.loads(l)
                if a.get("placeholder"):
                    assets.setdefault((a["standard_id"], a["clause_no"]), []).append(a)
    for f in jsonl_files(CLAUSE_DIRS):
        recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        n = 0
        for r in recs:
            todo = assets.get((r["standard_id"], r["clause_no"]), [])
            # 같은 placeholder가 여러 번이면 뒤에서부터 바꿔야 앞 위치가 안 밀린다
            for a in sorted(todo, key=lambda a: -a.get("occurrence_in_clause", 1)):
                body, ph = r["body_text"], a["placeholder"]
                if tagged(ph, a["asset_id"]) in body:  # 이미 연결됨
                    continue
                # 같은 문자열 표시 중 몇 번째인지 (occurrence_in_clause는 모든 표시 기준 순번)
                nth = 1 + sum(1 for b in todo if b["placeholder"] == ph
                              and b.get("occurrence_in_clause", 1) < a.get("occurrence_in_clause", 1))
                pos, k = -1, 0
                while k < nth:
                    pos = body.find(ph, pos + 1)
                    if pos < 0:
                        break
                    k += 1
                if pos < 0:
                    print("not found", f.name, r["clause_no"], ph[:40])
                    continue
                r["body_text"] = body[:pos] + tagged(ph, a["asset_id"]) + body[pos + len(ph):]
                n += 1
        tmp = str(f) + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as w:
            for r in recs:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, f)
        print(f.name, "linked", n)


if __name__ == "__main__":
    main()
