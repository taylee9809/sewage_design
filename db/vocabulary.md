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

## v1.3 추가 (2026-11-02, 영국 DCG)

| 키 | 값 | 뜻 |
|---|---|---|
| `flow` | `one_third_design` | 설계유량의 1/3 (DCG B6.9 최소유속) |
| `flow` | `pump_rate` | 펌프 운전 유량 (DCG D6.3.1) |
| `per` | `dwelling` | 세대당 |
| `location` | `garden_path` \| `driveway_restricted` \| `driveway_limited` \| `agricultural_open_space` \| `highway_unrestricted` | DCG B5.1.7 토피 구분 |
| `manhole_type` | `manhole-manhole` 등 | 인접 구조물 쌍 (DCG B5.2.6 간격) |
| `dwellings`, `properties` (신규 조건 키, 범위) | 범위 객체 | 세대 수·가구(건물) 수 조건 |
| `wc_connected` (신규 조건 키) | `at_least_one` \| `none` | 연결 WC 유무 |
| `velocity_ms` (신규 조건 키, 범위) | 범위 객체 m/s | 유속 구간별 값 (압송관 ks) |

## 3. 비교 그룹

`param_key` + `basis`(`flow`,`horizon`,`hydraulic_state`,`per`)가 같은 행끼리만 직접 비교한다. 다르면 2단계(공통 지표 환산) 또는 3단계(동일 입력 설계 결과 비교)로 넘긴다.

## v1.2 추가 (2026-10-21, 유지관리 기준·문서 종류)

| 키 | 추가 값 | 뜻 |
|---|---|---|
| `flow` | `dry_weather` | 청천시 실유량 (합류관 퇴적 판정 등) |
| condition `flood_risk_area` | `true` | 침수우려지역(하수도정비중점관리지역·자연재해위험개선지구 중 하수 침수위험 지역 등)에서만 적용 |

### 문서 종류 (`criteria/standards.json`의 `doc_type`)

| 값 | 뜻 | 엔진 기본 판정 |
|---|---|---|
| `law` | 법률·시행령·시행규칙 | 사용 |
| `regulation` | 고시·훈령·장관 결의(Resolución) 등 구속력 있는 행정규칙 | 사용 |
| `design_standard` | 설계기준(KDS, Ten States, CPHEEO Manual 등) | 사용 |
| `guideline` | 정부 지침·매뉴얼 | 채택(adopt) 시만 |
| `legacy_commentary` | 대체된 구 기준과 해설 | 채택(adopt) 시만 |
| `local_study` | 지자체 기본계획·연구 | 채택(adopt) 시만 |
| `paper` | 학술 논문 | 채택(adopt) 시만 |


## v1.4 추가 (2026-11-25, 하수처리장 기준값)

처리장 행(`criteria/*_treatment_sewer.csv`)의 **condition 은 CSV 원 키 그대로** 둔다(`treatment_stage`·`process`·`unit`·`flow_basis`·`settling_type` 등). 처리장 엔진(`engine/plant.py`)과 규칙 파일이 이 키로 행을 찾기 때문이다. 정규화 파일에는 condition 을 복사해 두어 DB 적재(정규화 condition 만 씀)에서도 조건이 살아 있게 한다. basis 만 아래처럼 붙인다.

| 키 | 추가 값 | 뜻 |
|---|---|---|
| `flow` | `dry_weather_avg` | 건기(청천시) 일평균 유량 (RAS 처리장 설계유량) |
| `flow` | `design_monthly_max` | 설계 월최대 유량 |
| `flow` | `design_daily_max_plus_return` | 설계 일최대 유량 + 최대 반송유량 (Ten States 이차침전지 고형물부하) |
| `flow` | `design_peak_instantaneous` | 설계 순간최대 유량 (Ten States 정의 (e)) |
| `flow` | 배열 | 원문이 두 유량 모두에서 판정하라고 할 때 (예: 평균·첨두 둘 다 수면부하 검토). 비교 그룹은 배열이 같은 행끼리만 |

condition 의 `flow_basis` 원문 표기 → basis.flow: `average`·`average_daily`·`design_average` → `design_daily_avg`, `max_daily`·`design_maximum_day` → `design_daily_max`, `peak_hourly`·`design_peak_hourly` → `design_peak_hourly`, `peak` → `peak`, `wet_weather` → `wet_weather`.

flow 를 정하지 않은 원칙: 유량과 무관한 값(치수·경사·여유고·지수·공정 상수·원단위 부하)은 `any`. 유량으로 정의되는 값(수면·월류·고형물 부하, 체류시간, HRT, F/M, 용적부하, 수로 유속, 반송비)인데 **그 조항이** 유량을 말하지 않으면 `unspecified`. 단, **같은 기준**의 다른 조항이 그 시설의 설계유량을 명시하면(예: KDS 61 50 00 표 1.1.1 「2차처리 처리시설 = 계획1일최대오수량」, RAS Art.189 3호 「일차침전지 = 시간최대」) 그 유량으로 채우고 basis.note 에 근거 조항을 적는다(2026-11-25, 14행). 시스템(분류/합류)에 따라 유량이 갈리는데 행에 그 조건이 없거나, 실측 범위·각주처럼 판정 기준이 아닌 행은 `unspecified` 로 두고 note 에 이유를 적는다. 다른 기준의 조항으로는 채우지 않는다.

## v1.5 추가 (2026-11-25, 방류수질 법령값)

`criteria/effluent_limits.csv`(법령 원문 표기) → `criteria/normalized/effluent/effluent_limits.jsonl`(`db/tag_effluent.py` 가 규칙으로 생성, 손 태그 없음) → DB `criteria.effluent_limit`. 설계기준 행(`criterion`)과 섞지 않는다.

| 필드 | 값 | 뜻 |
|---|---|---|
| `param_key` | `bod` \| `bod5` \| `cbod5` \| `cod` \| `toc` \| `tss` \| `settleable_solids` \| `tn` \| `tp` \| `total_coliform` \| `fecal_coliform` \| `ph` \| `ecotoxicity_daphnia` \| `oil_grease` \| 중금속(`cadmium` …) \| `pah` \| `*_removal` | BOD 일수가 원문에 없으면 `bod`(한국·인도), 5일 명시면 `bod5` — 같은 이름으로 합치지 않는다 |
| `limit_kind` | `max` \| `min` \| `range` | 상한 / 제거율 하한 / pH 범위 |
| `strict` | `true` | 원문이 '<'(미만) |
| `unit` | `mg/L` \| `count/mL` \| `MPN/100mL` \| `TU` \| `mL/L` \| `pH` \| `percent` | `mg/L O2` 는 `mg/L` |
| `averaging` | `avg_7d` \| `avg_30d` \| `unspecified` | 원문 평균 산정기간 |
| `legal_status` | `law` \| `regulation` \| `court_order` (+ `stayed`) | 시행규칙·법률 / 고시·CFR·Resolución / 법원 명령, 법원이 시행 정지한 규칙 |
| condition `capacity_m3_d`, `load_bod5_kg_d` | 범위 객체 | 처리용량·BOD 부하 구간 |
| condition `effective_from`, `effective_to` | 날짜 | 적용기간 (한국 별표 1 2029-11-30/2029-12-01 전환) |

숫자 표기: 콜롬비아는 쉼표가 소수점('0,50' = 0.5), 한국·미국·인도는 쉼표가 천 단위('1,000' = 1000).
