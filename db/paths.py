"""공개 저장소(이 폴더)와 비공개 폴더(재배포 불가 원문)의 데이터 위치.

비공개 폴더는 환경변수 SEWAGE_PRIVATE_DIR, 없으면 이 저장소 옆의 sewage_design_private.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = Path(os.environ.get("SEWAGE_PRIVATE_DIR", ROOT.parent / "sewage_design_private"))

CLAUSE_DIRS = [ROOT / "criteria" / "clauses", PRIVATE / "clauses"]
ASSET_DIRS = [ROOT / "criteria" / "assets", PRIVATE / "criteria_assets"]
QUOTES = PRIVATE / "criteria_quotes" / "quotes.csv"  # 재배포 불가 기준의 원문 구절 (row_key → quote_short)


def jsonl_files(dirs):
    return [f for d in dirs if d.exists() for f in sorted(d.glob("*.jsonl"))]
