/**
 * db/pool.ts
 * PostgreSQL 연결 풀을 생성하고 내보낸다.
 * 모든 Repository는 직접 연결을 생성하지 않고 이 풀을 공유한다.
 */

import { Pool } from "pg";
import { config } from "../config";

export const pool = new Pool({
  host: config.db.host,
  port: config.db.port,
  database: config.db.name,
  user: config.db.user,
  password: config.db.password,
  max: 10,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
});

pool.on("error", (err) => {
  console.error("[DB] Unexpected pool error:", err.message);
});
