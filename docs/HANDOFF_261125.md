# 인수인계 2026-11-25 — 비공개 원문이 있는 PC 에서 이어 하기

다른 PC 에서 「마저 해줘」를 받으면 이 문서의 **처음 할 일**부터 한다. 코드·태그·DB 적재 방법은 모두 main 에 있다.
DB 는 옮기지 않는다 — 저장소에서 1분이면 다시 만들어진다.

## 오늘 main 에 들어간 것 (PR #1 ~ #6)

| PR | 내용 |
|---|---|
| #1 | 검토 모드 `engine/check.py`, 출처 문서 종류 `doc_type` (영국 DCG 등 그 사이 main 과 병합) |
| #2 | `tests/test_hydraulics.py`: 비공개 원문이 없으면 표별로 건너뜀 (전에는 파일 전체 수집 오류) |
| #3 | 처리장 기준값 336행 + 요코하마 1행 정규화 태깅 → **1153/1153**, 어휘 v1.4. 처리장 행 condition 은 CSV 원 키 그대로 복사(DB 적재는 정규화 condition 만 써서, 태깅 전에는 DB 쪽 처리장 조건이 비어 있었다) |
| #4 | GitHub Actions: CSV 모드 + 임시 PostGIS 에 적재하는 DB 모드, `requirements.txt` |
| #5 | 처리장 `basis.flow = unspecified` 29행 중 14행을 **같은 기준**의 설계유량 조항으로 해소(근거는 `basis.note`), 19행은 이유를 적고 유지 |
| #6 | 방류수질 법령값 166행 태깅(`db/tag_effluent.py`, 어휘 v1.5) → DB `criteria.effluent_limit` |

테스트(비공개 원문 없이): CSV 모드 86 passed · 36 skipped · 1 xfailed / DB 모드 118 passed · 4 skipped · 1 xfailed.

## 처음 할 일 (원본 PC)

1. 받기·설치
   ```bash
   git pull            # 또는 gh repo clone taylee9809/sewage_design
   pip install -r requirements.txt
   ```
2. 비공개 원문 폴더 지정 — 폴더 구조는 그 폴더의 `README.txt` (`clauses/`, `criteria_assets/`, `criteria_quotes/quotes.csv`·`fields.csv`)
   ```bash
   export SEWAGE_PRIVATE_DIR=<비공개 폴더 경로>     # PowerShell: $env:SEWAGE_PRIVATE_DIR = "<경로>"
   ```
   지정하지 않으면 저장소 옆 `../sewage_design_private` 를 찾는다.
3. DB 만들기 (공개·비공개 두 DB, PostGIS 필요)
   ```bash
   createdb sewage_design && createdb sewage_design_private
   python db/load_criteria.py <공개 DSN> <비공개 DSN>
   python db/make_synthetic_network.py <공개 DSN>
   python db/make_syn02.py <공개 DSN>
   ```
4. 테스트
   ```bash
   python -m pytest tests -q -rs                         # CSV 모드
   SEWAGE_DB_DSN=<공개 DSN> python -m pytest tests -q -rs  # DB 모드
   ```
   **확인할 것**: 비공개 원문이 있으면 `test_hydraulics.py` 의 건너뜀 4개(요코하마 표3.24 2개, Ten States 33.41 2개)가 돌아야 한다. 적재 출력의 `private bodies` / `private assets` 가 0 이 아니어야 한다.
5. `git status` 가 깨끗한지 — 적재가 `criteria/normalized/_rows_for_tagging.jsonl` 을 다시 쓰는데, 비공개 구절이 이 파일로 새어 나가지 않게 되어 있다(공개 CSV 행만 씀). 바뀌었다면 커밋 전에 diff 를 본다.

## 남은 일

1. 위 4번 — 비공개 원문 표 테스트 4개 통과 확인. 실패하면 원문 판독본과 `engine/hydraulics.py` 중 어느 쪽이 맞는지부터.
2. `engine/plant.py` 의 `_num` 은 한국 표기 `1,000`(총대장균군)을 1.0 으로 읽는다(콜롬비아식 소수점 쉼표로 봄). 지금 엔진은 방류수질에서 BOD·SS 만 써서 결과에는 영향 없음. 대장균 등 다른 항목을 판정에 넣을 때는 태그 값(`criteria/normalized/effluent/`, 나라별 해석)을 쓰게 바꿀 것.
3. 정해진 다음 기능은 없음. 후보: 처리장 비교를 `engine.report` 에 절로 넣기, 방류수질 나라 간 비교표.

## 함정

- Windows 콘솔에서 적재 출력이 cp949 오류로 멈추면 `PYTHONIOENCODING=utf-8`.
- 외장·네트워크 드라이브의 저장소는 git 이 소유자를 확인하지 못해 막힌다 → `git -c safe.directory=<경로> …` 또는 `git config --global --add safe.directory <경로>`.
- `db/tag_effluent.py` 는 태그를 통째로 다시 만든다(규칙이 결정적, 손 태그 없음). CSV 를 고치면 다시 돌리고 태그 파일도 커밋 — 안 하면 `tests/test_effluent.py` 가 잡는다.
- 처리장 태깅(`criteria/normalized/treatment.jsonl`)은 손 결정이 섞여 있다(#5 의 14행). 다시 생성하지 말고 고칠 행만 고친다.
- 실무값은 설계기준 행에 넣지 않는다 — 별도 standard_id + 검토 파일 `adopt`. 공개 저장소이므로 사업명·맨홀 번호를 넣지 않는다.
