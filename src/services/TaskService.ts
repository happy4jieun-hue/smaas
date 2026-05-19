/**
 * services/TaskService.ts
 * Task 생성 및 조회 비즈니스 로직을 담당한다.
 * Controller → Service → Repository 레이어 순서로 호출된다.
 * AI 에이전트와 직접 통신하지 않으며, 순수한 데이터 처리만 담당한다.
 */

import { TaskRepository } from "../db/repositories/TaskRepository";
import { WorkflowService } from "./WorkflowService";
import { TaskInput, Task } from "../types/task.types";
import { v4 as uuidv4 } from "uuid";

export class TaskService {
  private taskRepo: TaskRepository;
  private workflowService: WorkflowService;

  constructor() {
    this.taskRepo = new TaskRepository();
    this.workflowService = new WorkflowService();
  }

  async createTask(input: TaskInput): Promise<Task> {
    const id = uuidv4();
    const record = await this.taskRepo.create({
      id,
      title: input.title,
      description: input.description,
      requesterId: input.requesterId,
      deadline: input.deadline ?? null,
      status: "running",
    });



    // 워크플로우는 비동기로 시작하고 즉시 태스크를 반환한다
    this.workflowService.startWorkflow(id, input).catch((err) => {
      console.error(`[TaskService] workflow failed for task ${id}:`, err.message);
      this.taskRepo.updateStatus(id, "failed");
    });

    return {
      id: record.id,
      title: record.title,
      description: record.description,
      requesterId: record.requesterId,
      deadline: record.deadline ?? undefined,
      status: "running",
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
    };
  }

  async getTaskById(id: string): Promise<Task> {
    const record = await this.taskRepo.findById(id);
    if (!record) throw Object.assign(new Error(`Task not found: ${id}`), { status: 404 });

    return {
      id: record.id,
      title: record.title,
      description: record.description,
      requesterId: record.requesterId,
      deadline: record.deadline ?? undefined,
      status: record.status as Task["status"],
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
    };
  }
}
