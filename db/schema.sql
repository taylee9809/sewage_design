-- sewage_design: 설계기준 DB (다국가 확장형, 공개 배포용)
-- 목적 1: 설계기준 조문 DB화(원문 그대로)  목적 2: 설계 논리 하네스·각국 기준 동일 조건 비교
-- 새 나라 추가 = standard 1행 + clause/criterion INSERT. 엔진 코드는 parameter만 안다.
-- 재배포 불가 원문 본문은 별도 DB(sewage_design_private)에만 두고, 여기선 clause.body_text를 비운다.

CREATE EXTENSION IF NOT EXISTS postgis;
DROP SCHEMA IF EXISTS criteria CASCADE;
CREATE SCHEMA criteria;
SET search_path = criteria, public;

-- 1. 기준서
CREATE TABLE standard (
  standard_id     text PRIMARY KEY,       -- KDS_61_40_00_20251001, TSS_WW_2026
  country         text NOT NULL,          -- ISO 3166 alpha-2, 국제기구는 INT
  issuer          text,
  title           text,
  edition         text,
  effective_date  date,
  is_latest       boolean,                -- 수집 시점 기준 최신판 여부
  access          text CHECK (access IN ('free','paid','project_only')),
  redistributable text CHECK (redistributable IN ('full_text','values_only','unknown')),
  license_note    text,                   -- 근거(저작권 고지 문구·출처)
  source_url      text,
  note            text
);

-- 2. 항목 사전 (기준 독립)
CREATE TABLE parameter (
  param_key   text PRIMARY KEY,
  domain      text NOT NULL DEFAULT 'sewer_gravity',
  name_ko     text,
  name_en     text,
  unit_si     text,                       -- 항목별 계산 단위 고정
  value_kind  text,                       -- min | max | range | value | table | formula | rule
  description text
);

-- 2-1. 나라별 용어 → 사전 매핑
CREATE TABLE parameter_alias (
  alias     text,
  lang      text,
  param_key text REFERENCES parameter,
  PRIMARY KEY (alias, lang)
);

-- 3. 조문 (원문 그대로)
CREATE TABLE clause (
  clause_id    serial PRIMARY KEY,
  standard_id  text NOT NULL REFERENCES standard,
  clause_no    text NOT NULL,             -- 문서 자체 번호 체계 그대로 ('1.3 (1) ①', '33.41', '3.5.4 解説', '第5条の9')
  clause_title text,
  parent_no    text,
  seq          int,                       -- 문서 내 순서
  page         text,                      -- 인쇄 쪽 표기
  lang         text,
  body_text    text,                      -- 원문 본문. redistributable<>'full_text'면 NULL (비공개 DB에 있음)
  source_url   text,
  UNIQUE (standard_id, clause_no)
);

-- 3-1. 조문 속 이미지(수식·표·그림) 판독본. 이미지 파일은 재배포 가능 기준만 공개, 나머지는 비공개 폴더
CREATE TABLE asset (
  asset_id    text PRIMARY KEY,           -- 본문의 [이미지 #id] / [그림 #id] 와 같은 값
  standard_id text NOT NULL REFERENCES standard,
  clause_id   int REFERENCES clause,
  kind        text,                       -- formula | table | figure | graph | drawing | flowchart | symbol
  label       text,                       -- 원문 캡션·식 번호
  text        text,                       -- 판독 텍스트 (수식은 평문, 표는 ' | ' 행)
  latex       text,
  data        jsonb,                      -- 그래프 디지타이즈 점·표 구조화 값
  confidence  text CHECK (confidence IN ('high','medium','low')),
  note        text
);

-- 4. 기준값
CREATE TABLE criterion (
  criterion_id  serial PRIMARY KEY,
  row_key       text UNIQUE,              -- 수집 CSV 행의 안정 키 (정규화 파일 연결용)
  standard_id   text NOT NULL REFERENCES standard,
  param_key     text NOT NULL REFERENCES parameter,
  condition_raw jsonb,                    -- 원문 표기 그대로 ({"dia_in":8})
  condition     jsonb,                    -- 표준 키·SI 정규화 (엔진·비교용)
  basis         jsonb,                    -- 값이 정의된 조건 ({"flow":"full_pipe"} 등)
  value_min     numeric,                  -- SI
  value_max     numeric,
  unit_si       text,                     -- 행 단위. 단일 항목은 parameter.unit_si와 같음
  value_text    text,                     -- 수치로 못 넣는 규정, '규정 없음'
  formula       text,
  orig_value    text,                     -- 원문 단위 그대로 '2.0 ft/s'
  unit_orig     text,
  binding       text NOT NULL CHECK (binding IN ('mandatory','standard','guide','none')),
  binding_raw   text,                     -- 원문 문형
  clause_id     int REFERENCES clause,    -- 대표 조문 (clause_ref의 첫 조항)
  clause_ref    text,                     -- 수집 시 기록한 조항 표기 그대로 ('3.15.1 Table 3.9')
  quote_short   text,
  source_url    text,
  verified      text NOT NULL DEFAULT 'unverified',
  retrieved_at  date,
  note          text
);
CREATE INDEX criterion_param_idx ON criterion (param_key, standard_id);

-- 5. 사업별 채택값 (= 설계기준 보고서)
CREATE TABLE project_criteria (
  project_id   text NOT NULL,
  param_key    text NOT NULL REFERENCES parameter,
  condition    jsonb,
  criterion_id int REFERENCES criterion,
  override_min numeric,
  override_max numeric,
  rationale    text,                      -- standard 단계 이탈 근거 (보고서 문장)
  approved_by  text,
  approved_at  date
);

-- 6. 관 규격 목록 (조달·표준·제조사 자료). 수리 계산은 inner_mm 사용
CREATE TABLE pipe_catalog (
  country            text NOT NULL,
  material           text NOT NULL,
  product_type       text,
  standard_ref       text,
  nominal_mm         numeric,
  inner_mm           numeric,
  outer_mm           numeric,
  wall_mm            numeric,
  class_or_stiffness text,
  source_url         text,
  source_type        text,
  retrieved_at       date,
  note               text
);
