-- sewage_design_private: 재배포 불가 원문 본문 보관 (배포 금지, 로컬 전용)
-- 공개 DB와 standard_id·clause_no로 연결된다.
DROP SCHEMA IF EXISTS source CASCADE;
CREATE SCHEMA source;

CREATE TABLE source.clause_body (
  standard_id  text NOT NULL,
  clause_no    text NOT NULL,
  clause_title text,
  parent_no    text,
  seq          int,
  page         text,
  lang         text,
  body_text    text,
  source_url   text,
  PRIMARY KEY (standard_id, clause_no)
);
