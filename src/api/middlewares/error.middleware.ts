/**
 * api/middlewares/error.middleware.ts
 * Express 전역 에러 핸들러.
 * Controller에서 next(err)로 전달된 에러를 일관된 JSON 포맷으로 반환한다.
 * 운영 환경에서는 스택 트레이스를 숨긴다.
 */

import { Request, Response, NextFunction } from "express";
import { config } from "../../config";

export function errorMiddleware(
  err: Error,
  req: Request,
  res: Response,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  next: NextFunction
): void {
  const status = (err as { status?: number }).status ?? 500;

  res.status(status).json({
    error: {
      message: err.message,
      ...(config.nodeEnv === "development" && { stack: err.stack }),
    },
  });
}
