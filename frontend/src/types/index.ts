// ── Member ────────────────────────────────
export interface MemberInput {
  name: string;
  email?: string;
  team?: string;
  role?: string;
  grade?: string;
  userRole?: string;  // manager | worker
  skills: string[];
  preferred_stages: string[];
  services: string[];
  capacity: number;
  current_load: number;
  available_hours_today: number;
  available_hours_tomorrow: number;
  timezone: string;
}

export interface MemberRecord extends MemberInput {
  id: string;
  userRole: string;   // manager | worker (항상 존재)
  createdAt: string;
  updatedAt: string;
}

export type MemberUpdate = Partial<MemberInput>;

// ── Assignment ────────────────────────────
export type AssignmentStatus = "pending" | "approved" | "changed" | "rejected";

export interface AssigneeCandidate {
  memberId: string;
  score: number;
  reason: string;
}

export interface SubTaskAssignmentRecord {
  id: string;
  taskId: string;
  workflowId: string;
  subTaskIndex: number;
  subTaskTitle: string;
  subTaskDescription?: string;
  priority?: string;
  suggestedRole?: string;    // AI 추천 역할: planner | designer | frontend | backend | qa
  suggestedReason?: string;  // 역할 추천 사유
  candidates: AssigneeCandidate[];
  recommendedMemberId?: string; // legacy (미사용)
  approvedMemberId?: string;
  status: AssignmentStatus;
  reason?: string;
  memo?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AssignmentPatch {
  approvedMemberId?: string;
  status?: AssignmentStatus;
  memo?: string;
}

// ── Task ─────────────────────────────────
export type TaskStatus = "pending" | "running" | "completed" | "failed";

export interface TaskInput {
  title: string;
  description: string;
  deadline?: string;
}

export interface Task extends TaskInput {
  id: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
}

// ── Workflow ──────────────────────────────
export type WorkflowStatus =
  | "pending"
  | "analyzing"
  | "planning"
  | "matching"
  | "validating"
  | "saving"
  | "notifying"
  | "completed"
  | "failed";

export interface AnalysisResult {
  category: string;
  complexity: 1 | 2 | 3 | 4 | 5;
  requiredSkills: string[];
  estimatedHours: number;
  keywords: string[];
  summary: string;
}

export interface SubTask {
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  dependsOn: string[];
}

export interface PlanResult {
  subTasks: SubTask[];
  estimatedTotalHours: number;
}

export interface AssigneeCandidate {
  memberId: string;
  score: number;
  reason: string;
}

export interface RoleRecommendationResult {
  subTaskIndex: number;
  subTaskTitle: string;
  suggestedRole: string;   // planner | designer | frontend | backend | qa
  suggestedReason: string;
}

export interface RolesSummary {
  planner: number;
  designer: number;
  frontend: number;
  backend: number;
  qa: number;
}

export interface MatchResult {
  assignments: RoleRecommendationResult[];
  rolesSummary?: RolesSummary;
}

export interface ValidationResult {
  valid: boolean;
  issues: string[];
  retryFromAgent?: string;
}

export interface NotificationResult {
  channels: string[];
  success: boolean;
}

export interface AgentContext {
  workflowId: string;
  taskId: string;
  status: WorkflowStatus;
  steps: {
    analyzed?: AnalysisResult;
    planned?: PlanResult;
    matched?: MatchResult;
    validated?: ValidationResult;
    notified?: NotificationResult;
  };
  errors: { agentName: string; message: string; timestamp: string }[];
  startedAt: string;
  updatedAt: string;
}

export interface WorkflowRecord {
  id: string;
  taskId: string;
  status: WorkflowStatus;
  context: AgentContext;
  createdAt: string;
  updatedAt: string;
}
