-- =============================================================
-- members.seed.sql
-- MatcherAgent 테스트용 팀원 시드 데이터
--
-- 실행: psql -h <host> -U <user> -d <db> -f members.seed.sql
-- =============================================================

INSERT INTO members (id, name, email, team, skills, capacity, timezone) VALUES

-- ── 백엔드 팀 ────────────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000001',
  '김민준',
  'minjun.kim@example.com',
  '백엔드팀',
  ARRAY['TypeScript', 'Node.js', 'PostgreSQL', 'REST API', 'Docker', 'AWS'],
  90,
  'Asia/Seoul'
),
(
  'a1000000-0000-0000-0000-000000000002',
  '이서연',
  'seoyeon.lee@example.com',
  '백엔드팀',
  ARRAY['Python', 'FastAPI', 'PostgreSQL', 'Redis', 'AWS', 'Kafka'],
  60,
  'Asia/Seoul'
),
(
  'a1000000-0000-0000-0000-000000000003',
  '박준혁',
  'junhyeok.park@example.com',
  '백엔드팀',
  ARRAY['Java', 'Spring Boot', 'MySQL', 'Kubernetes', 'gRPC'],
  0,   -- 현재 업무 가득 참 (배정 불가)
  'Asia/Seoul'
),

-- ── 프론트엔드 팀 ────────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000004',
  '최지우',
  'jiwoo.choi@example.com',
  '프론트엔드팀',
  ARRAY['TypeScript', 'React', 'Vue', 'CSS', 'Figma', 'Storybook'],
  100,
  'Asia/Seoul'
),
(
  'a1000000-0000-0000-0000-000000000005',
  '정하은',
  'haeun.jung@example.com',
  '프론트엔드팀',
  ARRAY['TypeScript', 'React', 'Next.js', 'Tailwind CSS', 'GraphQL'],
  80,
  'Asia/Seoul'
),

-- ── 풀스택 / 플랫폼 ──────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000006',
  '강도현',
  'dohyeon.kang@example.com',
  '플랫폼팀',
  ARRAY['TypeScript', 'Node.js', 'React', 'PostgreSQL', 'Docker', 'AWS', 'CI/CD'],
  70,
  'Asia/Seoul'
),

-- ── DevOps / 인프라 ──────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000007',
  '윤서준',
  'seojun.yoon@example.com',
  'DevOps팀',
  ARRAY['AWS', 'Kubernetes', 'Terraform', 'Docker', 'CI/CD', 'Monitoring', 'Linux'],
  50,
  'Asia/Seoul'
),

-- ── 데이터 / AI ──────────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000008',
  '임나영',
  'nayoung.lim@example.com',
  '데이터팀',
  ARRAY['Python', 'Machine Learning', 'SQL', 'Pandas', 'TensorFlow', 'Airflow'],
  100,
  'Asia/Seoul'
),

-- ── 디자인 ───────────────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000009',
  '한지민',
  'jimin.han@example.com',
  '디자인팀',
  ARRAY['Figma', 'UI/UX', 'CSS', 'Prototyping', 'User Research', 'Adobe XD'],
  90,
  'Asia/Seoul'
),

-- ── 기획 / PM ────────────────────────────────────────────────
(
  'a1000000-0000-0000-0000-000000000010',
  '송민호',
  'minho.song@example.com',
  'PM팀',
  ARRAY['Project Management', 'Agile', 'Jira', 'Requirements Analysis', 'Stakeholder Management'],
  100,
  'Asia/Seoul'
);
