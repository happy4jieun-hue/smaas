-- =============================================================
-- 001_init.sql
-- Smaas 초기 스키마
--
-- 실행: psql -h <host> -U <user> -d <db> -f 001_init.sql
-- 롤백: 파일 하단 "-- DOWN" 섹션 참고
-- =============================================================

-- ── 확장 ────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── updated_at 자동 갱신 트리거 함수 ────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================
-- 1. tasks
--    사용자가 등록한 원본 업무 요청
-- =============================================================
CREATE TYPE task_status AS ENUM (
  'pending',    -- 생성됨, 워크플로우 시작 전
  'running',    -- 워크플로우 진행 중
  'completed',  -- 정상 완료
  'failed'      -- 처리 중 오류 발생
);

CREATE TABLE tasks (
  id            UUID         NOT NULL DEFAULT uuid_generate_v4(),
  title         VARCHAR(255) NOT NULL,
  description   TEXT         NOT NULL,
  requester_id  VARCHAR(255) NOT NULL,
  deadline      TIMESTAMPTZ,
  status        task_status  NOT NULL DEFAULT 'pending',
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT tasks_pkey PRIMARY KEY (id)
);

CREATE TRIGGER trg_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE  tasks               IS '사용자 업무 요청';
COMMENT ON COLUMN tasks.requester_id  IS '업무를 요청한 사용자 ID';
COMMENT ON COLUMN tasks.deadline      IS 'ISO 8601 마감일 (nullable)';
COMMENT ON COLUMN tasks.status        IS 'pending | running | completed | failed';

-- =============================================================
-- 2. workflows
--    tasks 1 : N workflows
--    AgentContext 전체를 JSONB 컬럼으로 직렬화하여 저장한다.
-- =============================================================
CREATE TYPE workflow_status AS ENUM (
  'pending',
  'analyzing',
  'planning',
  'matching',
  'validating',
  'saving',
  'notifying',
  'completed',
  'failed'
);

CREATE TABLE workflows (
  id         UUID             NOT NULL DEFAULT uuid_generate_v4(),
  task_id    UUID             NOT NULL,
  status     workflow_status  NOT NULL DEFAULT 'pending',
  context    JSONB            NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

  CONSTRAINT workflows_pkey    PRIMARY KEY (id),
  CONSTRAINT workflows_task_fk FOREIGN KEY (task_id)
    REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_workflows_task_id ON workflows(task_id);
-- JSONB 경로 검색 (e.g. context->>'status') 를 위한 GIN 인덱스
CREATE INDEX idx_workflows_context_gin ON workflows USING GIN (context);

CREATE TRIGGER trg_workflows_updated_at
  BEFORE UPDATE ON workflows
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE  workflows         IS '에이전트 워크플로우 인스턴스';
COMMENT ON COLUMN workflows.context IS 'AgentContext 전체 스냅샷 (JSONB)';

-- =============================================================
-- 3. workflow_steps
--    workflows 1 : N workflow_steps
--    각 에이전트 단계 실행 결과를 개별 행으로 저장한다.
--    UNIQUE(workflow_id, step_name) 으로 워크플로우 당 각 단계는
--    한 번만 저장된다. (재시도 시 upsert 처리)
-- =============================================================
CREATE TYPE agent_name AS ENUM (
  'analyzer',
  'planner',
  'matcher',
  'validator',
  'notifier'
);

CREATE TYPE step_status AS ENUM (
  'success',
  'failed'
);

CREATE TABLE workflow_steps (
  id          UUID         NOT NULL DEFAULT uuid_generate_v4(),
  workflow_id UUID         NOT NULL,
  step_name   agent_name   NOT NULL,
  step_status step_status  NOT NULL,
  -- 해당 에이전트가 실행 시점에 받은 AgentContext 스냅샷
  input       JSONB        NOT NULL DEFAULT '{}',
  -- 해당 에이전트가 생성한 결과 (AnalysisResult 등, 실패 시 NULL)
  output      JSONB,
  error       TEXT,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT workflow_steps_pkey        PRIMARY KEY (id),
  CONSTRAINT workflow_steps_workflow_fk FOREIGN KEY (workflow_id)
    REFERENCES workflows(id) ON DELETE CASCADE,
  -- 워크플로우 당 동일 에이전트 단계는 한 번만 저장
  CONSTRAINT workflow_steps_unique_step UNIQUE (workflow_id, step_name)
);

CREATE INDEX idx_workflow_steps_workflow_id ON workflow_steps(workflow_id);
CREATE INDEX idx_workflow_steps_step_name   ON workflow_steps(step_name);
CREATE INDEX idx_workflow_steps_output_gin  ON workflow_steps USING GIN (output);

COMMENT ON TABLE  workflow_steps             IS '에이전트 단계별 실행 결과 (워크플로우 당 단계 1회)';
COMMENT ON COLUMN workflow_steps.step_name   IS 'agent_name ENUM: analyzer | planner | matcher | validator | notifier';
COMMENT ON COLUMN workflow_steps.step_status IS 'success | failed';
COMMENT ON COLUMN workflow_steps.input       IS '실행 시 AgentContext 스냅샷';
COMMENT ON COLUMN workflow_steps.output      IS '에이전트 결과 (AnalysisResult 등)';
COMMENT ON COLUMN workflow_steps.error       IS '실패 시 에러 메시지';

-- =============================================================
-- 4. assignments
--    tasks 1 : N assignments
--    MatcherAgent가 결정한 최종 담당자 배정 결과를 저장한다.
--    동일 태스크에 재매칭이 발생하면 새 행이 추가된다.
-- =============================================================
CREATE TABLE assignments (
  id           UUID         NOT NULL DEFAULT uuid_generate_v4(),
  task_id      UUID         NOT NULL,
  member_id    VARCHAR(255) NOT NULL,
  score        SMALLINT     NOT NULL,
  reason       TEXT         NOT NULL,
  assigned_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT assignments_pkey    PRIMARY KEY (id),
  CONSTRAINT assignments_task_fk FOREIGN KEY (task_id)
    REFERENCES tasks(id) ON DELETE CASCADE,
  CONSTRAINT assignments_score_range CHECK (score BETWEEN 0 AND 100)
);

CREATE INDEX idx_assignments_task_id   ON assignments(task_id);
CREATE INDEX idx_assignments_member_id ON assignments(member_id);

COMMENT ON TABLE  assignments             IS 'MatcherAgent 담당자 배정 결과';
COMMENT ON COLUMN assignments.score       IS '적합도 점수 (0–100)';
COMMENT ON COLUMN assignments.reason      IS 'Claude가 생성한 자연어 추천 사유';

-- =============================================================
-- DOWN (롤백 시 아래 구문을 순서대로 실행)
-- =============================================================
-- DROP TABLE IF EXISTS assignments;
-- DROP TABLE IF EXISTS workflow_steps;
-- DROP TABLE IF EXISTS workflows;
-- DROP TABLE IF EXISTS tasks;
-- DROP TYPE  IF EXISTS step_status;
-- DROP TYPE  IF EXISTS agent_name;   -- values: analyzer | planner | matcher | validator | notifier
-- DROP TYPE  IF EXISTS workflow_status;
-- DROP TYPE  IF EXISTS task_status;
-- DROP FUNCTION IF EXISTS set_updated_at();
-- DROP EXTENSION IF EXISTS "uuid-ossp";
