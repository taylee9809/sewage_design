-- 관망 입력·설계 결과 (3단계 하네스용). QGIS에서 PostGIS 레이어로 바로 열 수 있다.
-- criteria 스키마(기준)와 분리: 기준은 공용, 관망은 사업별.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS network;
SET search_path = network, public;

CREATE TABLE IF NOT EXISTS project (
  project_id text PRIMARY KEY,
  name       text,
  srid       int NOT NULL,
  synthetic  boolean NOT NULL DEFAULT false,   -- 가상 관망 여부
  note       text
);

-- 맨홀(절점). 유입 인구는 그 맨홀로 들어오는 배수구역 인구(초기·목표연도)
CREATE TABLE IF NOT EXISTS node (
  project_id    text NOT NULL REFERENCES project ON DELETE CASCADE,
  node_id       text NOT NULL,
  kind          text NOT NULL DEFAULT 'manhole' CHECK (kind IN ('manhole','outfall')),
  ground_el     numeric NOT NULL,                -- 지반고 m
  pop_initial   int NOT NULL DEFAULT 0,
  pop_ultimate  int NOT NULL DEFAULT 0,
  min_invert_el numeric,                         -- 하류단 지정 관저고 등 고정 조건(선택)
  note          text,
  geom          geometry(Point) NOT NULL,
  PRIMARY KEY (project_id, node_id)
);

-- 관로(구간). 흐름 방향 = from → to
CREATE TABLE IF NOT EXISTS link (
  project_id text NOT NULL REFERENCES project ON DELETE CASCADE,
  link_id    text NOT NULL,
  from_node  text NOT NULL,
  to_node    text NOT NULL,
  material   text NOT NULL DEFAULT 'pvc',
  note       text,
  geom       geometry(LineString) NOT NULL,
  length_m   numeric GENERATED ALWAYS AS (ST_Length(geom)) STORED,
  PRIMARY KEY (project_id, link_id),
  FOREIGN KEY (project_id, from_node) REFERENCES node (project_id, node_id),
  FOREIGN KEY (project_id, to_node) REFERENCES node (project_id, node_id)
);

-- 기준별 설계 결과 (하네스가 채운다)
CREATE TABLE IF NOT EXISTS design_link (
  project_id   text NOT NULL,
  standard_id  text NOT NULL,
  run_id       text NOT NULL,
  link_id      text NOT NULL,
  dia_mm       int,
  slope        numeric,
  q_design     numeric,                          -- m3/s
  q_initial    numeric,
  inv_up       numeric,                          -- 상류 관저고
  inv_dn       numeric,
  cover_up     numeric,
  cover_dn     numeric,
  v_check      numeric,                          -- 기준이 정한 판정 유속
  extra_manholes int,                            -- 맨홀 최대간격 때문에 추가로 필요한 중간 맨홀 수
  governing    text,                             -- 경사·관경을 결정한 조항
  note         text,
  PRIMARY KEY (project_id, standard_id, run_id, link_id)
);

-- 실무 판정(가시설·펌프장)용 입력 (2026-10-14)
ALTER TABLE link ADD COLUMN IF NOT EXISTS soil_class text;          -- 토질조사 결과 요약 (예: sand, clay, gravel)
ALTER TABLE link ADD COLUMN IF NOT EXISTS gw_depth_m numeric;        -- 지하수위 심도 (지표 아래 m), NULL = 지하수 없음/미확인
ALTER TABLE node ADD COLUMN IF NOT EXISTS land_owner text;           -- 지적 소유 구분 (public = 국공유지)

-- 배수설비 연결점 (2026-10-16): 필지 오수받이에서 본관으로 들어오는 연결관. 본관은 이 높이보다 깊어야 한다.
CREATE TABLE IF NOT EXISTS house_connection (
  project_id    text NOT NULL REFERENCES project ON DELETE CASCADE,
  conn_id       text NOT NULL,
  link_id       text NOT NULL,                   -- 접속하는 본관 구간
  chainage_m    numeric NOT NULL,                -- 구간 상류 맨홀에서 접속점까지 거리
  box_invert_el numeric NOT NULL,                -- 오수받이 유출 관저고 m
  conn_len_m    numeric NOT NULL,                -- 오수받이~본관 연결관 길이
  note          text,
  geom          geometry(Point),
  PRIMARY KEY (project_id, conn_id),
  FOREIGN KEY (project_id, link_id) REFERENCES link (project_id, link_id) ON DELETE CASCADE
);
