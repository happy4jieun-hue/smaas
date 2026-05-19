/**
 * db/models/Member.ts
 * members 테이블의 행을 표현하는 인터페이스.
 */

export interface MemberRecord {
  id: string;
  name: string;
  email: string | null;
  team: string | null;
  skills: string[];
  capacity: number;   // 0~100
  timezone: string;
  createdAt: string;
  updatedAt: string;
}

/** MatcherAgent가 Claude 프롬프트에 주입하는 축약 프로필 */
export interface MemberProfile {
  id: string;
  name: string;
  team: string | null;
  skills: string[];
  capacity: number;
}
