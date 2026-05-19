/**
 * db/repositories/MemberRepository.ts
 * members 테이블에 대한 쿼리를 캡슐화한다.
 * MatcherAgent가 가용 인원을 조회할 때 사용한다.
 */

import { pool } from "../pool";
import { MemberRecord, MemberProfile } from "../models/Member";

export class MemberRepository {
  /**
   * 가용 멤버 목록을 반환한다.
   *
   * 조건:
   * - capacity > 0  (업무 수용 가능)
   * - requiredSkills가 주어지면, 해당 스킬을 1개 이상 보유한 멤버만 포함
   *   (완전 일치가 아닌 교집합(&&) 기준 — 관련 기술이 있는 인원 우선)
   *
   * 정렬: capacity DESC (여유 있는 인원 우선)
   */
  async findAvailable(requiredSkills?: string[]): Promise<MemberRecord[]> {
    const hasSkillFilter = Array.isArray(requiredSkills) && requiredSkills.length > 0;

    const query = `
      SELECT
        id,
        name,
        email,
        team,
        skills,
        capacity,
        timezone,
        created_at AS "createdAt",
        updated_at AS "updatedAt"
      FROM members
      WHERE capacity > 0
        ${hasSkillFilter ? "AND skills && $1::text[]" : ""}
      ORDER BY capacity DESC
    `;

    const params = hasSkillFilter ? [requiredSkills] : [];
    const { rows } = await pool.query<MemberRecord>(query, params);
    return rows;
  }

  /** 전체 멤버 목록 (관리용) */
  async findAll(): Promise<MemberRecord[]> {
    const { rows } = await pool.query<MemberRecord>(`
      SELECT
        id, name, email, team, skills, capacity, timezone,
        created_at AS "createdAt",
        updated_at AS "updatedAt"
      FROM members
      ORDER BY team, name
    `);
    return rows;
  }

  async findById(id: string): Promise<MemberRecord | null> {
    const { rows } = await pool.query<MemberRecord>(
      `SELECT id, name, email, team, skills, capacity, timezone,
              created_at AS "createdAt", updated_at AS "updatedAt"
       FROM members WHERE id = $1`,
      [id]
    );
    return rows[0] ?? null;
  }

  /** Claude 프롬프트 주입용 축약 프로필로 변환 */
  toProfiles(members: MemberRecord[]): MemberProfile[] {
    return members.map(({ id, name, team, skills, capacity }) => ({
      id,
      name,
      team,
      skills,
      capacity,
    }));
  }
}
