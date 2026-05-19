/**
 * types/agent.types.ts
 * 에이전트 실행 관련 공통 타입을 정의한다.
 * 각 에이전트의 입출력 구조와 실행 상태를 표현한다.
 */

// WorkflowEngine 내부 흐름 제어용 (orchestrator 포함)
export type AgentName =
  | "orchestrator"
  | "analyzer"
  | "planner"
  | "matcher"
  | "validator"
  | "notifier";

// DB workflow_steps.step_name ENUM 과 1:1 대응 (orchestrator 제외)
export type AgentStepName = Exclude<AgentName, "orchestrator">;

export type AgentStatus = "idle" | "running" | "success" | "failed";

// 분석 에이전트 출력
export interface AnalysisResult {
  category: string;          // 업무 분류 (예: "개발", "디자인", "마케팅")
  complexity: 1 | 2 | 3 | 4 | 5;
  requiredSkills: string[];  // 필요한 스킬 목록
  estimatedHours: number;    // 예상 소요 시간
  keywords: string[];        // 핵심 키워드
  summary: string;           // 1~2문장 요약
}

// 계획 에이전트 출력
export interface SubTask {
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  dependsOn: string[]; // 의존하는 서브태스크 title 목록
}

export interface PlanResult {
  subTasks: SubTask[];
  estimatedTotalHours: number;
}

// 매칭 에이전트 출력
export interface AssigneeCandidate {
  memberId: string;
  score: number;       // 0~100
  reason: string;      // 자연어 추천 사유
}

export interface MatchResult {
  candidates: AssigneeCandidate[];
  topCandidateId: string;
}

// 검증 에이전트 출력
export interface ValidationResult {
  valid: boolean;
  issues: string[];              // 문제 항목 목록
  retryFromAgent?: AgentStepName; // 재시도 필요 시 어느 에이전트부터 (orchestrator 불가)
}

// 알림 에이전트 출력
export interface NotificationResult {
  channels: string[];  // 전송된 채널 목록
  success: boolean;
}
