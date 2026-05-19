/**
 * api/middlewares/auth.middleware.ts
 * API 요청의 인증을 처리하는 미들웨어.
 * Authorization 헤더의 Bearer 토큰을 검증한다.
 * TODO: JWT 검증 또는 API Key 방식 구현
 */

import { Request, Response, NextFunction } from "express";

export function authMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  // TODO: extract and verify token from Authorization header
  // const token = req.headers.authorization?.split(" ")[1];
  // if (!token) { res.status(401).json({ error: "Unauthorized" }); return; }
  next(); // 구현 전 임시 통과
}
