# 조건(condition)·정의조건(basis) 표준 어휘 v1 (2026-10-13)

`condition_raw` = 수집 시 원문 표기 그대로. `condition` = 아래 표준 키로 정규화한 것(엔진 조회용).
`basis` = 그 값이 **어떤 유량·수리 상태에서 정의됐는지**(국가 간 비교용). 같은 param_key라도 basis가 다르면 직접 비교하지 않는다.

## 1. condition 표준 키

수치 범위는 연산자 객체로 쓴다: `{"ge":200,"le":600}`, `{"gt":600,"le":1000}`, `{"eq":250}`. 원문에 경계 포함 여부가 없으면 `ge`/`le`.

| 키 | 값 | 예 |
|---|---|---|
| `system` | `separate` \| `combined` \| `storm` (배열 가능) | 분류식 오수관 → `"separate"` |
| `pipe_role` | `branch`(지선) \| `sub_main`(준간선) \| `trunk`(간선) \| `interceptor`(차집관) \| `house_connection`(연결관·취부관·가정연결) \| `building_drain`(택지 내 배수설비) \| `force_main` \| `inverted_siphon` | |
| `dia_mm` | 범위 객체, 공칭/내경 mm | Ten States 8 in → `{"eq":200}` + `dia_basis:"nominal_in"` |
| `dia_basis` | `nominal_in`(인치 공칭) \| `nominal_mm` \| `inner` | 인치 규격은 반드시 표기 |
| `material` | `rc` \| `concrete` \| `vcp` \| `pvc` \| `hdpe` \| `frp` \| `grp` \| `ci_di` \| `steel` \| `ac` \| `masonry` \| `pe` \| `resin_concrete` \| `rigid` \| `flexible` | |
| `shape` | `circular` \| `rectangular` \| `horseshoe` \| `egg` | |
| `wastewater_type` | `domestic` \| `commercial` \| `industrial` \| `groundwater` \| `institutional` | |
| `population` | 범위 객체 (명) | |
| `served_population` | 범위 객체 (명, 해당 관로 배수 인구) | |
| `depth_m` | 범위 객체 (관 매설심도·맨홀 깊이) | |
| `slope` | 범위 객체 (m/m) | 급경사 앵커 조건 |
| `location` | `roadway` \| `sidewalk` \| `planned_road` \| `crossing_water_main` \| `stream_crossing` \| 자유 텍스트 | |
| `road_width_m` | 범위 객체 | |
| `receives_house_connections` | bool | |
| `manhole_type` | 자유 텍스트(원문 규격명) | |
| `joint_method` | `crown` \| `water_surface` \| `invert` \| `step` \| `center` | |
| `exception` | 자유 텍스트 — 예외·완화 조건 (원문 요약) | "초기관로, 장래 유량 증가 없음" |
| `other` | 자유 객체 — 위에 안 맞는 조건 | |

## 2. basis 표준 키

| 키 | 값 | 뜻 |
|---|---|---|
| `flow` | `design_peak_hourly`(계획시간최대) \| `design_daily_max` \| `design_daily_avg` \| `peak`(총괄 첨두) \| `min_flow` \| `full_pipe`(만관) \| `design_depth`(설계수심) \| `any` | 값이 판정되는 유량 상태 |
| `horizon` | `initial`(초기, 기준연도) \| `ultimate`(목표연도) \| `unspecified` | |
| `hydraulic_state` | `full` \| `partial` \| `unspecified` | 만관/부분류 |
| `per` | `capita_day` \| `area_day` \| `length_day` \| `manhole_day` \| `ratio_to_avg` \| `ratio_to_daily_max` \| `ratio_to_per_capita` | 유량·계수의 분모 |
| `ref_param` | param_key | 비율 값이 무엇에 대한 비율인지 (예: 지하수량 → per_capita_wastewater) |
| `note` | 자유 텍스트 | 원문 근거 한 줄 |

basis가 의미 없는 항목(최소관경, 맨홀 간격, 토피 등 기하 규정)은 `{"flow":"any"}`로 둔다.

## v1.1 추가 (2026-10-13, 1차 태깅에서 나온 공백)

| 키 | 추가 값 | 뜻 |
|---|---|---|
| `flow` | `design_flow` | 그 기준이 말하는 "계획하수량" 일반 (관 종류별 정의는 기준 내 다른 행이 정함) |
| `flow` | `design_storm` | 계획우수량 |
| `flow` | `combined_design` | 합류관 계획하수량 (계획우수량 + 계획시간최대오수량) |
| `flow` | `wet_weather` | 우천시 계획오수량 (차집관로) |
| `flow` | `design_max_week` | 설계 최대 주간 유량 (Ten States 11.241(b)) |
| `flow` | `unspecified` | 원문이 유량 조건을 정하지 않음 |
| `flow` | `none` | 해당 기준에 규정 자체가 없음 (binding none 행) |
| `hydraulic_state` | `actual` | 설계유량 시 실수심 유속 (만관 아님) |
| `per` | `capita`, `area`, `length`, `manhole` | 분모만 표시. 시간 단위는 unit_si를 따른다 (기존 `*_day`는 일 단위일 때만) |
| `per` | `ratio_to_peak_hourly`, `ratio_to_design_flow` | 비율 값의 기준 |
| `wastewater_type` | `channel_drainage` | 수로 등 배수 |
| `joint_method` | `stepped` | 계단접합 (`step`=단차접합과 구분) |
| `material` | `plastic` | 관종 미특정 플라스틱. material은 배열 허용 |
| `terrain` (신규 키) | `flat` \| `hilly` | |
| `facility` (신규 키) | 자유 텍스트 | 법령의 시설 구분 (排水施設, 公共下水道 등) |
| `item` (신규 키) | 자유 텍스트 | 복합 항목(연결관 등)의 하위 항목 (최대연장, 접속각…) |
| `lining` (신규 키) | 자유 텍스트 | 관 내면 상태 (unlined, mortar lining…) |

## v1.2 추가 (2026-10-14, 콜롬비아 RAS)

| 키 | 값 | 뜻 |
|---|---|---|
| `horizon` | `both` | 계획기간 초기·말기 두 조건 모두에서 판정 |
| `altitude_masl` (신규 조건 키, 범위) | 범위 객체 m | 표고 조건 (원단위 상한 등) |
| `sewer_type` (신규 조건 키, 특수) | `conventional` 외 원문 표기 (simplificado, condominial, ASAS…) | 재래식이 아닌 하수도 형식 — 기본 설계에서는 제외 |
| `flow_lps` (신규 조건 키, 범위) | 범위 객체 L/s | 유량 조건 (최대유속 예외 등) |
| `hydraulic_state` | `actual` (전단응력 판정에도 사용) | τ = ρgRS를 실수심 R로 계산 |
| 공백 메모 | 면적 종류(도로 면적/배수 면적), 토피 측정 기준(외면 관정), OR 조건 | 아직 키 없음 — note에 기록, 필요 시 v1.3 |

## 3. 비교 그룹

`param_key` + `basis`(`flow`,`horizon`,`hydraulic_state`,`per`)가 같은 행끼리만 직접 비교한다. 다르면 2단계(공통 지표 환산) 또는 3단계(동일 입력 설계 결과 비교)로 넘긴다.
