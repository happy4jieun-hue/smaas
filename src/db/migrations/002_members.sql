-- =============================================================
-- 002_members.sql
-- members 테이블 추가
-- MatcherAgent가 실제 가용 인원을 조회하기 위한 스키마
--
-- 실행: psql -h <host> -U <user> -d <db> -f 002_members.sql
-- =============================================================

-- ── members ──────────────────────────────────────────────────
-- 업무에 배정 가능한 팀원 프로필.
-- skills: 보유 스킬 배열 (예: ['TypeScript', 'React', 'AWS'])
-- capacity: 현재 가용 용량 0~100 (0이면 업무 불가)
CREATE TABLE members (
  id         UUID         NOT NULL DEFAULT uuid_generate_v4(),
  name       VARCHAR(100) NOT NULL,
  email      VARCHAR(255),
  team       VARCHAR(100),
  skills     TEXT[]       NOT NULL DEFAULT '{}',
  capacity   SMALLINT     NOT NULL DEFAULT 100,
  timezone   VARCHAR(50)  NOT NULL DEFAULT 'Asia/Seoul',
  created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT members_pkey           PRIMARY KEY (id),
  CONSTRAINT members_capacity_range CHECK (capacity BETWEEN 0 AND 100)
);

CREATE INDEX idx_members_skills    ON members USING GIN (skills);
CREATE INDEX idx_members_capacity  ON members (capacity);

CREATE TRIGGER trg_members_updated_at
  BEFORE UPDATE ON members
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE  members           IS '업무 배정 가능한 팀원 프로필';
COMMENT ON COLUMN members.skills    IS '보유 스킬 목록 (TEXT[])';
COMMENT ON COLUMN members.capacity  IS '가용 용량 0~100 (0이면 배정 불가)';

-- assignments.member_id → members.id FK 추가
-- (001_init.sql에서 VARCHAR로 선언된 컬럼을 UUID FK로 변경)
ALTER TABLE assignments
  ALTER COLUMN member_id TYPE UUID USING member_id::UUID,
  ADD CONSTRAINT assignments_member_fk
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL;

-- =============================================================
-- DOWN
-- =============================================================
-- ALTER TABLE assignments DROP CONSTRAINT IF EXISTS assignments_member_fk;
-- ALTER TABLE assignments ALTER COLUMN member_id TYPE VARCHAR(255);
-- DROP TABLE IF EXISTS members;
