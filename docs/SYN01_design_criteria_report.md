# 설계기준 보고서 — 가상 오수관망 SYN01

> 자동 생성 (engine/report.py). 가상 관망 — 사업 ID `SYN01`. 원문 값은 DB `criteria.criterion`, 해석 규칙은 `criteria/rules/`, 사업 채택값은 `criteria/projects/SYN01.json`에서 읽었다.

## 1. 적용 기준

| 기준 | 판본 | 최신 | 공개 조건 | 비고 |
|---|---|---|---|---|
| KDS 61 40 00 관로시설 설계기준<br>`KDS_61_40_00_20251001` | 2025-10-01 | 예 | unknown |  |
| Recommended Standards for Wastewater Facilities (Ten States Standards)<br>`TSS_WW_2026` | 2026 | 예 | values_only | 사용자 구매본(PDF, 2026-06-11 수정). 판매처 다운로드 약관(복사·공유 불가)과 문서 내 저작권 고지가 다름 |
| 横浜市下水道設計指針(管きょ編)・同解説<br>`JP_YOKOHAMA_SEKKEI_202604` | 令和8年度改訂版 + 2026-04-17 正誤 | 예 | values_only | 지자체 기준. 일부 값은 국가 지침(下水道施設計画・設計指針と解説, 유료) 근거 |
| Manual on Sewerage and Sewage Treatment Systems, Part A: Engineering<br>`CPHEEO_SEW_2013` | 2013 | 예 | full_text | 공식 사이트 업로드본(Wayback). 표지 없어 발행연도 문서 내 직접 확인 못 함 |
| Reglamento Técnico del Sector de Agua Potable y Saneamiento Básico (RAS) — Resolución 0330 de 2017, compilado con Res. 799 y 908 de 2021<br>`CO_RAS_0330_2017_COMP2021` | Anexo 2 compilatorio (2021) | 예 | full_text | 법령 원문. Res. 0548/2022(경과규정) 이후 개정은 RAS 페이지 기준 미확인 |

## 2. 기준별 설계 항목 (원문 그대로)

원문 구절은 재배포 가능한 기준(공개 조건 full_text)만 싣는다.

### KDS_61_40_00_20251001

| 항목 | 조건 | 값 | 정의 조건(basis) | 조항 | 구속력 | 원문 구절 |
|---|---|---|---|---|---|---|
| 1인1일 오수량 |  | (원문 비공개) | design_daily_max/ultimate/capita_day | 1.7.2 (1) | 기준 |  |
| 시간최대(첨두) 계수 |  | 1.3~1.8 ratio | design_peak_hourly/ultimate/ratio_to_daily_max | 1.7.2 (6) | 기준 |  |
| 지하수·침입수 |  | 0.2 ratio | design_daily_max/ultimate/ratio_to_per_capita | 1.7.2 (3) | 기준 |  |
| 최소유속 | system separate | 0.6 m/s | design_peak_hourly/ultimate/unspecified | 1.3 (1) ① | 기준 |  |
| 최소유속 | system ['combined', 'storm'] | 0.8 m/s | design_storm/unspecified/unspecified | 1.3 (2) ① | 기준 |  |
| 최대유속 | system separate | 3 m/s | design_peak_hourly/ultimate/unspecified | 1.3 (1) ① | 기준 |  |
| 최대유속 | system ['combined', 'storm'] | 3 m/s | design_storm/unspecified/unspecified | 1.3 (2) ① | 기준 |  |
| 최소경사 | system separate | (원문 비공개) | design_peak_hourly/ultimate/unspecified | 1.3 (1) ① | 기준 |  |
| 설계수심비 | shape circular | 1 ratio | design_flow/ultimate/full | 1.2 (2) ④ | 기준 |  |
| 설계수심비 | shape rectangular | 0.9 ratio | design_flow/ultimate/partial | 1.2 (2) ④ | 기준 |  |
| 설계수심비 | shape horseshoe | 0.8 ratio | design_flow/ultimate/partial | 1.2 (2) ④ | 기준 |  |
| 여유율 | system separate | (원문 비공개) | design_peak_hourly/ultimate/unspecified | 1.1 (5) | 참고 |  |
| 조도계수 n | material rc | 0.013 - | any | 1.2 (2) ② | 기준 |  |
| 조도계수 n | material vcp | 0.013 - | any | 1.2 (2) ② | 기준 |  |
| 조도계수 n | material pvc | 0.011 - | any | 1.2 (2) ② | 기준 |  |
| 조도계수 n | material frp | 0.011 - | any | 1.2 (2) ② | 기준 |  |
| 최소관경 | system separate | 200 mm | any | 2.3 (1) | 기준 |  |
| 최소관경 | system ['combined', 'storm'] | 250 mm | any | 2.3 (2) | 기준 |  |
| 최소토피 |  | 1 m | any | 3.2 | 기준 |  |
| 맨홀 최대간격 | dia_mm ≤600 | 75 m | any | 7.1 (1) ② | 기준 |  |
| 맨홀 최대간격 | dia_mm >600 ≤1000 | 100 m | any | 7.1 (1) ② | 기준 |  |
| 맨홀 최대간격 | dia_mm >1000 ≤1500 | 150 m | any | 7.1 (1) ② | 기준 |  |
| 맨홀 최대간격 | dia_mm ≥1650 | 200 m | any | 7.1 (1) ② | 기준 |  |
| 부관(낙차맨홀) 기준 낙차 | system ['separate', 'combined'], joint_method step | 0.6 m | any | 5.1 (2) | 기준 |  |
| 관 접합 |  | (원문 비공개) | any | 5.1 (1); 5.1 (2) | 기준 |  |
| 하류 관경 감소 |  | (원문 비공개) | any | 1.3 본문 | 기준 |  |

### TSS_WW_2026

| 항목 | 조건 | 값 | 정의 조건(basis) | 조항 | 구속력 | 원문 구절 |
|---|---|---|---|---|---|---|
| 1인1일 오수량 | other collection_systemnew, system separate | 379 L/c/d | design_daily_avg/ultimate/capita_day | 11.243(a) | 의무 |  |
| 시간최대(첨두) 계수 | other collection_systemnew, system separate | 2~4.24 ratio | design_peak_hourly/ultimate/ratio_to_avg | 11.243(b); Figure 1 | 의무 |  |
| 지하수·침입수 | other collection_systemnew, system separate | (원문 비공개) | design_peak_hourly/ultimate/capita_day | 11.243(b) | 기준 |  |
| 최소유속 | dia_mm ≤1050, system separate, dia_basis nominal_in | 0.61 m/s | full_pipe/unspecified/full | 33.41 | 의무 |  |
| 최소유속 | dia_mm ≥1200, system separate, dia_basis nominal_in | 0.914 m/s | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최대유속 |  | 3.05 m/s | unspecified/unspecified/unspecified | 33.45 | 의무 |  |
| 최소경사 | dia_mm =200, system separate, dia_basis nominal_in | 0.004 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =250, system separate, dia_basis nominal_in | 0.0028 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =300, system separate, dia_basis nominal_in | 0.0022 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =375, system separate, dia_basis nominal_in | 0.0015 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =450, system separate, dia_basis nominal_in | 0.0012 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =525, system separate, dia_basis nominal_in | 0.001 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =600, system separate, dia_basis nominal_in | 0.0008 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =675, system separate, dia_basis nominal_in | 0.00067 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =750, system separate, dia_basis nominal_in | 0.00058 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =825, system separate, dia_basis nominal_in | 0.00052 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =900, system separate, dia_basis nominal_in | 0.00046 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =975, system separate, dia_basis nominal_in | 0.00041 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 최소경사 | dia_mm =1050, system separate, dia_basis nominal_in | 0.00037 m/m | full_pipe/unspecified/full | 33.41 | 기준 |  |
| 설계수심비 |  | (원문 비공개) | none |  | 규정 없음 |  |
| 여유율 |  | (원문 비공개) | none |  | 규정 없음 |  |
| 조도계수 n |  | 0.013 - | any | 33.41 | 의무 |  |
| 최소관경 | other sewer원수 이송 공공 자연유하 하수관, system separate | 203 mm | any | 33.1 | 의무 |  |
| 최소토피 |  | (원문 비공개) | any | 33.2 | 기준 |  |
| 맨홀 최대간격 | dia_mm ≤375, dia_basis nominal_in | 122 m | any | 34.1 | 의무 |  |
| 맨홀 최대간격 | dia_mm ≥450 ≤750, dia_basis nominal_in | 152 m | any | 34.1 | 의무 |  |
| 부관(낙차맨홀) 기준 낙차 |  | 0.61 m | any | 34.2 | 의무 |  |
| 하류 관경 감소 |  | (원문 비공개) | none | 33.6 | 규정 없음 |  |

### JP_YOKOHAMA_SEKKEI_202604

| 항목 | 조건 | 값 | 정의 조건(basis) | 조항 | 구속력 | 원문 구절 |
|---|---|---|---|---|---|---|
| 1인1일 오수량 | wastewater_type domestic | 220 L/c/d | design_daily_avg/capita_day | 3.3.1 表3.8 | 기준 |  |
| 1인1일 오수량 | wastewater_type domestic | 290 L/c/d | design_daily_max/capita_day | 3.3.1 表3.8 | 기준 |  |
| 1인1일 오수량 | other use管きょ設計(Qs), wastewater_type domestic | 430.3 L/c/d | design_peak_hourly/capita_day | 3.3.1 表3.8 | 기준 |  |
| 시간최대(첨두) 계수 | wastewater_type domestic | 1.95 ratio | design_peak_hourly/ratio_to_avg | 3.3.5 表3.21 | 기준 |  |
| 시간최대(첨두) 계수 | wastewater_type commercial | 1.95 ratio | design_peak_hourly/ratio_to_avg | 3.3.5 表3.21 | 기준 |  |
| 시간최대(첨두) 계수 | wastewater_type industrial | 2 ratio | design_peak_hourly/ratio_to_avg | 3.3.5 表3.21 | 기준 |  |
| 시간최대(첨두) 계수 | wastewater_type groundwater | 1 ratio | design_peak_hourly/ratio_to_avg | 3.3.5 表3.21; 3.3.4解説 | 기준 |  |
| 시간최대(첨두) 계수 | system combined, wastewater_type channel_drainage | 1.5 ratio | design_peak_hourly/ratio_to_avg | 3.3.5 表3.21; 3.3.4解説 | 기준 |  |
| 지하수·침입수 | other area事業計画区域(緑の10大拠点の市街化調整区域除く), system ['separate', 'combined'], wastewater_type groundwater | 5.787e-05 m3/s/ha | design_daily_avg/area_day | 3.3.4 表3.19 | 기준 |  |
| 지하수·침입수 | other area事業計画区域(緑の10大拠点の市街化調整区域除く), system ['separate', 'combined'], wastewater_type groundwater | 5.79e-05 m3/s/ha | design_peak_hourly/area | 3.3.4(1) 表3.17 | 기준 |  |
| 최소유속 | system separate | 0.6 m/s | design_peak_hourly/ultimate/full | 3.5.4(1) | 기준 |  |
| 최소유속 | system ['combined', 'storm'] | 0.8 m/s | design_flow/ultimate/actual | 3.5.4(2) | 기준 |  |
| 최대유속 | system separate | 3 m/s | design_peak_hourly/ultimate/full | 3.5.4(1) | 기준 |  |
| 최대유속 | system ['combined', 'storm'] | 3 m/s | design_flow/ultimate/actual | 3.5.4(2) | 기준 |  |
| 최소경사 | dia_mm =250, system separate | 0.0025 m/m | full_pipe/unspecified/full | 3.5.4 解説(p.3-37) | 참고 |  |
| 설계수심비 | shape circular | 1 ratio | design_flow/ultimate/full | 3.5.2(1) | 기준 |  |
| 설계수심비 | shape rectangular | 0.9 ratio | design_flow/ultimate/partial | 3.5.2(1) | 기준 |  |
| 설계수심비 | shape horseshoe | 0.8 ratio | design_flow/ultimate/partial | 3.5.2(1) | 기준 |  |
| 여유율 | system separate | 1 ratio | design_peak_hourly/ultimate/unspecified | 3.5.1(1) 表3.22 | 기준 |  |
| 여유율 | other component汚水量分のみ(雨水量分は余裕なし), system combined | 0.2 ratio | design_peak_hourly/ultimate/unspecified | 3.5.1(3) 表3.22 | 기준 |  |
| 조도계수 n | material rc | 0.013 - | any | 3.5.2(3) 表3.23 | 기준 |  |
| 조도계수 n | material vcp | 0.013 - | any | 3.5.2(3) 表3.23 | 기준 |  |
| 조도계수 n | shape rectangular, material rc | 0.013 - | any | 3.5.2(3) 表3.23 | 기준 |  |
| 조도계수 n | material pvc | 0.01 - | any | 3.5.2(3) 表3.23 | 기준 |  |
| 조도계수 n | material frp | 0.01 - | any | 3.5.2(3) 表3.23 | 기준 |  |
| 최소관경 | shape circular | 250 mm | any | 3.5.6 | 기준 |  |
| 최소토피 | other note歩道, 또는 交通量少(表3.26 L・A)이고 幅員6.50m以下の車道, location ['sidewalk', 'roadway'], road_width_m ≤6.5 | 1.2 m | any | 3.5.8 | 기준 |  |
| 최소토피 | location ['planned_road', 'roadway'], road_width_m >6.5 | 1.5 m | any | 3.5.8(1) 解説 | 기준 |  |
| 최소토피 | pipe_role trunk | 3.5 m | any | 3.5.8(1) 表3.25 | 기준 |  |
| 최소토피 | other includes圧送管, dia_mm <1000, pipe_role sub_main | 1.8 m | any | 3.5.8(1) 表3.25 | 기준 |  |
| 최소토피 | other dia_def汚水管・雨水管 口径300mm以下 / 合流管 450mm以下, pipe_role branch | 1.2 m | any | 3.5.8(1) 表3.25 | 기준 |  |
| 최소토피 | other source道路法施行令第11条第4号(引用) | 1 m | any | 3.5.8 解説 | 참고 |  |
| 맨홀 최대간격 | dia_mm ≤300 | 50 m | any | 4.1.2 表4.1 | 기준 |  |
| 맨홀 최대간격 | dia_mm ≥350 ≤600 | 75 m | any | 4.1.2 表4.1 | 기준 |  |
| 맨홀 최대간격 | dia_mm ≥700 ≤1000 | 100 m | any | 4.1.2 表4.1 | 기준 |  |
| 맨홀 최대간격 | dia_mm ≥1100 ≤1500 | 150 m | any | 4.1.2 表4.1 | 기준 |  |
| 맨홀 최대간격 | dia_mm ≥1650 | 200 m | any | 4.1.2 表4.1 | 기준 |  |
| 관 접합 | joint_method water_surface | 0.7 ratio | any | 3.5.9(1) | 참고 |  |
| 관 접합 | joint_method crown | (원문 비공개) | any | 3.5.9(2) | 기준 |  |
| 하류 관경 감소 |  | (원문 비공개) | any | 3.5.4; 3.5.9 | 규정 없음 |  |

### CPHEEO_SEW_2013

| 항목 | 조건 | 값 | 정의 조건(basis) | 조항 | 구속력 | 원문 구절 |
|---|---|---|---|---|---|---|
| 1인1일 오수량 | system separate, facility conventional sewers | 100 L/c/d | design_daily_avg/unspecified/capita_day | 3.5 | 의무 | conventional sewers shall be designed for a minimum sewage flow of 100 litres pe |
| 시간최대(첨두) 계수 | system separate, served_population ≤20000 | 3 ratio | peak/unspecified/ratio_to_avg | 3.5 Table 3.2 | 참고 | The peak factor or the ratio of maximum to average flows depends upon contributo |
| 시간최대(첨두) 계수 | system separate, served_population ≥20001 ≤50000 | 2.5 ratio | peak/unspecified/ratio_to_avg | 3.5 Table 3.2 | 참고 | The peak factor or the ratio of maximum to average flows depends upon contributo |
| 시간최대(첨두) 계수 | system separate, served_population ≥50001 ≤750000 | 2.25 ratio | peak/unspecified/ratio_to_avg | 3.5 Table 3.2 | 참고 | The peak factor or the ratio of maximum to average flows depends upon contributo |
| 시간최대(첨두) 계수 | system separate, served_population ≥750001 | 2 ratio | peak/unspecified/ratio_to_avg | 3.5 Table 3.2 | 참고 | The peak factor or the ratio of maximum to average flows depends upon contributo |
| 지하수·침입수 |  | 5~50 m3/(ha·d) | peak/unspecified/area_day | 3.6 Table 3.3 | 기준 | allowances for groundwater infiltration for the worst condition in the area shou |
| 지하수·침입수 |  | 0.0005~0.005 m3/(m·d) | peak/unspecified/length_day | 3.6 Table 3.3 | 기준 | allowances for groundwater infiltration for the worst condition in the area shou |
| 지하수·침입수 |  | 0.25~0.5 m3/(manhole·d) | peak/unspecified/manhole_day | 3.6 Table 3.3 | 기준 | allowances for groundwater infiltration for the worst condition in the area shou |
| 최소유속 | system separate | 0.6 m/s | peak/initial/actual | 3.15.1 Table 3.9 | 의무 | Gravity sewers shall be designed for the velocities as in Table 3.9. |
| 최소유속 | system separate | 0.8 m/s | peak/ultimate/actual | 3.15.1 Table 3.9 | 의무 | Gravity sewers shall be designed for the velocities as in Table 3.9. |
| 최대유속 | system separate | 3 m/s | unspecified/unspecified/unspecified | 3.15.3; Table 3.9 | 의무 | the maximum velocity shall be limited to 3 m/s |
| 최소경사 | dia_mm =150, system separate | 0.006 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 최소경사 | dia_mm =200, system separate | 0.004 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 최소경사 | dia_mm =250, system separate | 0.0028 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 최소경사 | dia_mm =300, system separate | 0.0022 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 최소경사 | dia_mm =375, system separate | 0.0015 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 최소경사 | dia_mm =450, system separate | 0.0012 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 최소경사 | dia_mm ≥525, system separate | 0.001 m/m | unspecified/unspecified/unspecified | 3.15.6 Table 3.13 | 의무 | The minimum slopes in Table 3.13 shall be applicable |
| 설계수심비 | shape circular | 0.8 ratio | peak/ultimate/partial | 3.15.5 | 의무 | the maximum depth of flow in design shall be limited to 0.8 of the diameter at u |
| 여유율 | shape circular | 0.8 ratio | peak/ultimate/partial | 3.15.5 | 의무 | the maximum depth of flow in design shall be limited to 0.8 of the diameter at u |
| 조도계수 n | other surfacegood, material vcp | 0.012 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other surfacefair, material vcp | 0.015 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other jointcollar surfacegood, material concrete | 0.013 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other jointcollar surfacefair, material concrete | 0.015 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other pipespun RCC/PSC, S/S joints, material rc | 0.011 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other pipebrick surfacegood, material masonry | 0.015 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other surfacewelded, material steel | 0.013 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | lining spun cement mortar, material steel | 0.011 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | lining unlined, material ci_di | 0.013 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | lining spun cement mortar, material ci_di | 0.011 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | material ac | 0.011 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | other surfacesmooth, material plastic | 0.011 - | any | 3.15.4 Table 3.11 | 참고 | Values of n may be taken as 0.015 for unlined metallic pipes and 0.011 for plast |
| 조도계수 n | material frp | 0.01 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 조도계수 n | material ['hdpe', 'pvc'] | 0.01 - | any | 3.15.4 Table 3.11 | 참고 | n : Manning's coefficient of roughness as in Table 3-11 |
| 최소관경 | other population_basispresent/base year, population <100000 | 150 mm | any | 3.14 | 의무 | population of less than 1 lakh, the minimum diameter of 150 mm shall be adopted |
| 최소관경 | terrain hilly | 150 mm | any | 3.14 | 의무 | In the case of hilly locations, the minimum diameter of 150 mm shall be adopted. |
| 최소토피 | system separate, location 하수관망 시점부(start of network) | 1 m | any | 3.20.3 | 참고 | It is the standard design practice to provide a minimum cover of 1 m at the star |
| 최소토피 | pipe_role house_connection | 0.9 m | any | 3.70 | 의무 | The minimum earth cover above the crown of the sewer shall be mandatorily 90 cm |
| 맨홀 최대간격 | dia_mm ≤600, pipe_role trunk, receives_house_connections False | 60 m | any | 3.71.2 Table 3.31 | 기준 | the following in Table 3.31 is now recommended |
| 맨홀 최대간격 | dia_mm ≥600 ≤900, pipe_role trunk, receives_house_connections False | 90 m | any | 3.71.2 Table 3.31 | 기준 | the following in Table 3.31 is now recommended |
| 맨홀 최대간격 | dia_mm ≥900 ≤1200, pipe_role trunk, receives_house_connections False | 120 m | any | 3.71.2 Table 3.31 | 기준 | the following in Table 3.31 is now recommended |
| 맨홀 최대간격 | dia_mm ≥1200 ≤1500, pipe_role trunk, receives_house_connections False | 150 m | any | 3.71.2 Table 3.31 | 기준 | the following in Table 3.31 is now recommended |
| 부관(낙차맨홀) 기준 낙차 |  | 0.6 m | any | 3.25; 3.17.1 | 의무 | a drop of more than 600 mm is required ... a drop connection shall be provided |
| 관 접합 | joint_method crown | 관정(crown) 접합: 관경 변경 시 유입·유출관 관정 동일 표고; 유출관 관정은 유입관 관정보다 높지 않게; 소관 관정(soffit)은 대관 관정보다 낮지 않게 | any | 3.17.1; 3.20.3; 3.26; 3.30 | 의무 | To avoid backing up, the crown of the outgoing sewer shall not be higher than th |
| 하류 관경 감소 |  | 하류로 관경 축소 금지 | any | 3.17.1 | 의무 | Transition from larger to smaller diameters shall not be made. |

### CO_RAS_0330_2017_COMP2021

| 항목 | 조건 | 값 | 정의 조건(basis) | 조항 | 구속력 | 원문 구절 |
|---|---|---|---|---|---|---|
| 1인1일 오수량 | wastewater_type domestic | QD = CR × P × DNETA / 86400 (L/s); 수요 단위면적·가입자 기반 식도 병기 | design_daily_avg/ultimate/capita_day | Artículo 134 numeral 1 | 의무 | Cuando se utilice proyección de población, se debe calcular con la siguiente ecu |
| 1인1일 순급수량 | altitude_masl >2000 | 120 L/c/d | design_daily_avg/ultimate/capita_day | Artículo 43 Tabla 1 | 의무 | se deberá utilizar un valor de dotación que no supere los máximos establecidos e |
| 1인1일 순급수량 | altitude_masl ≥1000 ≤2000 | 130 L/c/d | design_daily_avg/ultimate/capita_day | Artículo 43 Tabla 1 | 의무 | se deberá utilizar un valor de dotación que no supere los máximos establecidos e |
| 1인1일 순급수량 | altitude_masl <1000 | 140 L/c/d | design_daily_avg/ultimate/capita_day | Artículo 43 Tabla 1 | 의무 | se deberá utilizar un valor de dotación que no supere los máximos establecidos e |
| 시간최대(첨두) 계수 |  | 1.4~3.8 ratio | design_peak_hourly/ultimate/ratio_to_avg | Artículo 134 numeral 4 | 의무 | Este valor deberá estar entre 1,4 y 3,8 |
| 구간 최소 설계유량 | system separate | 1.5 L/s | design_flow/unspecified | Artículo 134 numeral 7 | 의무 | Cuando el caudal de diseño calculado en el tramo sea menor que 1,5 L/s, debe ado |
| 최소유속 | system separate | 고정값 없음: τ ≥ 1.0 Pa를 만드는 실유속이 최소유속 | design_flow/unspecified/actual | Artículo 141 | 의무 | La velocidad mínima real permitida en el colector de alcantarillado sanitario es |
| 최소 벽면 전단응력 | system separate | 1 Pa | design_flow/both/actual | Artículo 141 | 의무 | La velocidad mínima real permitida en el colector de alcantarillado sanitario es |
| 최대유속 | system separate | 5 m/s | design_flow/unspecified/actual | Artículo 142 | 의무 | La velocidad máxima real en un colector por gravedad no debe sobrepasar 5,0 m/s, |
| 최소경사 | system separate | 규정 없음 | none | Artículo 141 | 규정 없음 |  |
| 설계수심비 | system separate, dia_basis inner | 0.85 ratio | design_flow/unspecified/partial | Artículo 143 | 의무 | el valor máximo permisible de la profundidad del flujo para el caudal de diseño  |
| 최소관경 | system separate, dia_basis inner, population ≥2500 | 170 mm | any | Artículo 140 | 의무 | El diámetro interno real mínimo permitido en redes de alcantarillado sanitario e |
| 최소관경 | system separate, dia_basis inner, population <2500 | 140 mm | any | Artículo 140 | 의무 | Para poblaciones menores de 2.500 habitantes el diámetro interno real permitido  |
| 최소토피 | other location_rawVías peatonales o zonas verdes, system separate, location sidewalk | 0.75 m | any | Artículo 139 Tabla 18 | 의무 | Los valores mínimos permisibles de recubrimiento de los colectores que no requie |
| 최소토피 | other location_rawVías vehiculares, system separate, location roadway | 1.2 m | any | Artículo 139 Tabla 18 | 의무 | Los valores mínimos permisibles de recubrimiento de los colectores que no requie |
| 맨홀 최대간격 | receives_house_connections True | 120 m | any | Artículo 154 numeral 1 | 의무 | a distancia máxima de 120 m para tramos con aportes de caudal |
| 맨홀 최대간격 | other pipe_role_rawinterceptores y emisarios finales, pipe_role interceptor, receives_house_connections False | 300 m | any | Artículo 154 numeral 1 | 의무 | 300 m en interceptores y emisarios finales sin aportes de caudal |
| 부관(낙차맨홀) 기준 낙차 | joint_method invert | 0.75 m | any | Artículo 155 numeral 1 | 의무 | con una diferencia de nivel entre las cotas bateas mayor a 0,75 m, respecto del  |
| 관 접합 |  | 맨홀 유입·유출관 관저고 차이 = 수리해석(흐름 상태·구조물 형상 손실)으로 결정; 손실 ≤ 0이면 관정 간 2 cm 이상 | design_flow | Artículo 154 numeral 7; Artículo 137 | 의무 | una diferencia entre las cotas bateas de los colectores de entrada y salida, def |
| 하류 관경 감소 |  | 규정 없음 | none | Artículo 154 | 규정 없음 |  |

## 3. 사업 채택값 (원문에 수치가 없거나 선택지를 주는 값)

| 기준 | 항목 | 채택값 | 근거 |
|---|---|---|---|
| KDS_61_40_00_20251001 | qpc | `300` | KDS 1.7.2 (1) 수치 없음, 예시값 300 L/인·일 (사용자 결정 2026-10-14) |
| KDS_61_40_00_20251001 | pf_hourly | `max` | 1.7.2 (6) 1.3~1.8 범위 상한 |
| KDS_61_40_00_20251001 | gw_ratio | `max` | 1.7.2 (3) 20% 이하 — 상한 |
| KDS_61_40_00_20251001 | junction | `crown` | 5.1 (1) 수면접합 또는 관정접합 중 관정접합 |
| KDS_61_40_00_20251001 | pump_efficiency | `0.7` | 펌프+전동기 효율 가정(원문 표 없음 또는 구간 미정리) — 비교용 |
| TSS_WW_2026 | cover | `1.0` | 33.2 수치 없음, 비교용 1.0 m |
| TSS_WW_2026 | pump_efficiency | `0.7` | 펌프+전동기 효율 가정(원문 표 없음 또는 구간 미정리) — 비교용 |
| JP_YOKOHAMA_SEKKEI_202604 | pump_efficiency | `0.7` | 펌프+전동기 효율 가정(원문 표 없음 또는 구간 미정리) — 비교용 |
| CPHEEO_SEW_2013 | cover | `1.0` | 3.20.3 시점부 1 m(참고값) 사용 |
| CPHEEO_SEW_2013 | pump_efficiency | `0.7` | 펌프+전동기 효율 가정(원문 표 없음 또는 구간 미정리) — 비교용 |
| CO_RAS_0330_2017_COMP2021 | altitude_masl | `1500` | 가상 관망 표고 가정 1,500 m → Art.43 순급수 130 L/인·일 |
| CO_RAS_0330_2017_COMP2021 | peak_formula | `1 + 14 / (4 + sqrt(P/1000))` | Art.134 num.4 '근사식'(식 미지정) — Harmon식 채택, 1.4~3.8로 자름 |
| CO_RAS_0330_2017_COMP2021 | manning_n | `0.01` | RAS에 조도계수 수치 없음 — PVC 0.010 가정(일본·인도 PVC와 동일) |
| CO_RAS_0330_2017_COMP2021 | street_location | `roadway` | Art.139 Tabla 18 차도 1.20 m 적용(가상 관망은 도로 매설 가정) |
| CO_RAS_0330_2017_COMP2021 | pump_efficiency | `0.7` | 펌프+전동기 효율 가정(원문 표 없음 또는 구간 미정리) — 비교용 |
| CO_RAS_0330_2017_COMP2021 | hazen_c | `140` | RAS 하수 조항에 C 없음 — PVC 140 가정(CPHEEO PVC 값과 동일) |

## 4. 기준 비교 — 같은 정의 조건끼리만

값 옆 괄호는 정의 조건(유량/시점/수리 상태/분모). 정의 조건이 다르면 숫자가 같아도 같은 기준이 아니다. 실제 영향은 5절의 같은 관망 설계 결과로 비교한다.

| 항목 | KDS_61_40_00_20251001 | TSS_WW_2026 | JP_YOKOHAMA_SEKKEI_202604 | CPHEEO_SEW_2013 | CO_RAS_0330_2017_COMP2021 |
|---|---|---|---|---|---|
| 1인1일 오수량 | (원문 비공개) (design_daily_max/ultimate/capita_day) | — | 220 L/c/d (design_daily_avg/capita_day)<br>290 L/c/d (design_daily_max/capita_day) | 100 L/c/d (design_daily_avg/unspecified/capita_day) | QD = CR × P × DNETA / 86400 (L/s); 수요 단위면적·가입자 기반 식도 병기 (design_daily_avg/ultimate/capita_day) |
| 1인1일 순급수량 | — | — | — | — | 120 L/c/d (design_daily_avg/ultimate/capita_day)<br>130 L/c/d (design_daily_avg/ultimate/capita_day)<br>140 L/c/d (design_daily_avg/ultimate/capita_day) |
| 회귀계수 | — | — | — | — | — |
| 시간최대(첨두) 계수 | 1.3~1.8 ratio (design_peak_hourly/ultimate/ratio_to_daily_max) | — | 1.95 ratio (design_peak_hourly/ratio_to_avg)<br>1.95 ratio (design_peak_hourly/ratio_to_avg)<br>2 ratio (design_peak_hourly/ratio_to_avg) | 3 ratio (peak/unspecified/ratio_to_avg)<br>2.5 ratio (peak/unspecified/ratio_to_avg)<br>2.25 ratio (peak/unspecified/ratio_to_avg) | 1.4~3.8 ratio (design_peak_hourly/ultimate/ratio_to_avg) |
| 지하수·침입수 | 0.2 ratio (design_daily_max/ultimate/ratio_to_per_capita) | — | — | 5~50 m3/(ha·d) (peak/unspecified/area_day)<br>0.0005~0.005 m3/(m·d) (peak/unspecified/length_day)<br>0.25~0.5 m3/(manhole·d) (peak/unspecified/manhole_day) | — |
| 구간 최소 설계유량 | — | — | — | — | 1.5 L/s (design_flow/unspecified) |
| 최소유속 | 0.6 m/s (design_peak_hourly/ultimate/unspecified) | 0.61 m/s (full_pipe/unspecified/full)<br>0.914 m/s (full_pipe/unspecified/full) | 0.6 m/s (design_peak_hourly/ultimate/full) | 0.6 m/s (peak/initial/actual)<br>0.8 m/s (peak/ultimate/actual) | 고정값 없음: τ ≥ 1.0 Pa를 만드는 실유속이 최소유속 (design_flow/unspecified/actual) |
| 최소 벽면 전단응력 | — | — | — | — | 1 Pa (design_flow/both/actual) |
| 최대유속 | 3 m/s (design_peak_hourly/ultimate/unspecified) | 3.05 m/s (unspecified/unspecified/unspecified) | 3 m/s (design_peak_hourly/ultimate/full) | 3 m/s (unspecified/unspecified/unspecified) | 5 m/s (design_flow/unspecified/actual) |
| 최소경사 | (원문 비공개) (design_peak_hourly/ultimate/unspecified) | 0.004 m/m (full_pipe/unspecified/full)<br>0.0028 m/m (full_pipe/unspecified/full)<br>0.0022 m/m (full_pipe/unspecified/full) | 0.0025 m/m (full_pipe/unspecified/full) | 0.006 m/m (unspecified/unspecified/unspecified)<br>0.004 m/m (unspecified/unspecified/unspecified)<br>0.0028 m/m (unspecified/unspecified/unspecified) | 규정 없음 |
| 설계수심비 | 1 ratio (design_flow/ultimate/full)<br>0.9 ratio (design_flow/ultimate/partial)<br>0.8 ratio (design_flow/ultimate/partial) | 규정 없음 | 1 ratio (design_flow/ultimate/full)<br>0.9 ratio (design_flow/ultimate/partial)<br>0.8 ratio (design_flow/ultimate/partial) | 0.8 ratio (peak/ultimate/partial) | 0.85 ratio (design_flow/unspecified/partial) |
| 여유율 | (원문 비공개) (design_peak_hourly/ultimate/unspecified) | 규정 없음 | 1 ratio (design_peak_hourly/ultimate/unspecified) | 0.8 ratio (peak/ultimate/partial) | — |
| 조도계수 n | 0.013 - (any)<br>0.013 - (any)<br>0.011 - (any) | 0.013 - (any) | 0.013 - (any)<br>0.013 - (any)<br>0.013 - (any) | 0.011 - (any)<br>0.013 - (any)<br>0.011 - (any) | — |
| 최소관경 | 200 mm (any) | — | 250 mm (any) | 150 mm (any) | 170 mm (any)<br>140 mm (any) |
| 최소토피 | 1 m (any) | (원문 비공개) (any) | — | — | — |
| 맨홀 최대간격 | 75 m (any)<br>100 m (any)<br>150 m (any) | 122 m (any)<br>152 m (any) | 50 m (any)<br>75 m (any)<br>100 m (any) | — | 120 m (any) |
| 부관(낙차맨홀) 기준 낙차 | 0.6 m (any) | 0.61 m (any) | — | 0.6 m (any) | 0.75 m (any) |
| 관 접합 | (원문 비공개) (any) | — | 0.7 ratio (any)<br>(원문 비공개) (any) | 관정(crown) 접합: 관경 변경 시 유입·유출관 관정 동일 표고; 유출관 관정은 유입관 관정보다 높지 않게; 소관 관정(soffit)은 대관 관정보다 낮지 않게 (any) | 맨홀 유입·유출관 관저고 차이 = 수리해석(흐름 상태·구조물 형상 손실)으로 결정; 손실 ≤ 0이면 관정 간 2 cm 이상 (design_flow) |
| 하류 관경 감소 | (원문 비공개) (any) | 규정 없음 | 규정 없음 | 하류로 관경 축소 금지 (any) | 규정 없음 |

## 5. 같은 관망 설계 결과 (SYN01)

| 기준 | 굴착 지표(m²) | 최대 관경 | 최대 매설깊이(m) | 추가 맨홀 | 부관 | 플러싱 장치 | 경고 |
|---|---|---|---|---|---|---|---|
| KDS_61_40_00_20251001 | 3556 | 400 | 2.22 | 22 | 10 | 0 | 0 |
| TSS_WW_2026 | 4033 | 450 | 2.73 | 1 | 0 | 0 | 0 |
| JP_YOKOHAMA_SEKKEI_202604 | 4322 | 400 | 2.86 | 30 | 12 | 0 | 0 |
| CPHEEO_SEW_2013 | 5578 | 250 | 4.25 | 66 | 0 | 14 | 0 |
| CO_RAS_0330_2017_COMP2021 | 4921 | 315 | 3.28 | 4 | 0 | 0 | 0 |

### 경사·관경을 결정한 조항 (구간 수)

- **KDS_61_40_00_20251001**: 1.3 (1) ① 유속 0.60 m/s 이상 (design_depth, design 유량) ×10; 지반 따라 최소토피 유지(요구 경사 2.22‰보다 급함) ×6; 하류 경사 점감(1.3 본문 기준)로 경사 제한, 상류 맨홀 낙차 0.10 m ×2; 하류 경사 점감(1.3 본문 기준)로 경사 제한, 상류 맨홀 낙차 0.00 m ×1
- **TSS_WW_2026**: 지반 따라 최소토피 유지(요구 경사 4.00‰보다 급함) ×12; 33.41 최소경사표 ×11; 지반 따라 최소토피 유지(요구 경사 3.68‰보다 급함) ×1; 33.41 유속 0.61 m/s 이상 (full, design 유량) ×1
- **JP_YOKOHAMA_SEKKEI_202604**: 3.5.4(1) 유속 0.60 m/s 이상 (full, design 유량) ×8; 지반 따라 최소토피 유지(요구 경사 1.45‰보다 급함) ×7; 하류 경사 점감(3.5.4 의무)로 경사 제한, 상류 맨홀 낙차 0.10 m ×2; 하류 경사 점감(3.5.4 의무)로 경사 제한, 상류 맨홀 낙차 0.14 m ×2
- **CPHEEO_SEW_2013**: 3.15.6 Table 3.13 최소경사표 ×17; 지반 따라 최소토피 유지(요구 경사 6.00‰보다 급함) ×6; 지반 따라 최소토피 유지(요구 경사 23.62‰보다 급함) ×1; 지반 따라 최소토피 유지(요구 경사 14.82‰보다 급함) ×1
- **CO_RAS_0330_2017_COMP2021**: Artículo 141 벽면 전단응력 1.0 Pa 이상 (실수심, initial 유량) ×15; 지반 따라 최소토피 유지(요구 경사 5.44‰보다 급함) ×6; 지반 따라 최소토피 유지(요구 경사 5.06‰보다 급함) ×2; 지반 따라 최소토피 유지(요구 경사 4.14‰보다 급함) ×1

## 5-2. 펌프장·압송관

전환 조건에 원문 수치가 있으면 자동 배치, 없으면 판정 보류(설계자 검토)로 표시한다. 토구 지정 관저고에 자연유하로 닿지 못하면 기준과 무관한 물리적 필요로 토구 직전에 펌프장을 둔다. 원문에 없는 항목(흡입수위·부속손실·잠김 등)은 판정 보류이며, 부속 구성은 펌프장마다 사업 입력(`station_fittings`)이다.

| 기준 | 펌프장 | 판정 메모 |
|---|---|---|
| KDS_61_40_00_20251001 | 없음 | 판정 보류(설계자 검토): 원문 수치 없음 — 최대 매설 2.22 m (A03-A04) |
| TSS_WW_2026 | 없음 | — |
| JP_YOKOHAMA_SEKKEI_202604 | 없음 | 판정 보류(설계자 검토): 원문 수치 없음 — 최대 매설 2.86 m (T11-T12) |
| CPHEEO_SEW_2013 | 없음 | — |
| CO_RAS_0330_2017_COMP2021 | 없음 | — |

## 6. 원문 한계·주의

- 각 기준의 판정 규칙 해석(원문 미지정 해소)은 `criteria/rules/<기준>.json`의 `resolution`에 근거 조항과 함께 적혀 있다.
- 이미지·수식 판독 신뢰도가 낮은 항목은 DB `criteria.asset.confidence='low'`로 표시된다.
- 이 보고서는 기준 간 비교용이며, 실제 사업 적용 시 발주처 승인 절차(설계기준 보고서 승인)를 거쳐야 한다.
