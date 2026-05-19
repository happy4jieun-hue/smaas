"""
app/utils/safe_log.py - Windows cp949 콘솔 안전 출력 헬퍼
=========================================================
3중 방어 구조:
  1. safe_str()      - 문자 치환 + cp949 encode fallback
  2. SafeLogFilter   - logging 시스템 전체에 걸린 필터
  3. configure_safe_logging() - stdout/stderr reconfigure + 필터 설치 + asyncio 핸들러
"""

import logging
import sys
from typing import Any


# cp949에서 인코딩 불가능한 특수문자 -> ASCII 대체 매핑
_CHAR_MAP = str.maketrans({
    '\u2014': '-',    # — em dash
    '\u2013': '-',    # - en dash
    '\u2026': '...',  # ... ellipsis
    '\u2192': '->',   # -> right arrow
    '\u2190': '<-',   # <- left arrow
    '\u2022': '*',    # * bullet
    '\u25b6': '>',    # > right-pointing triangle
    '\u25bc': 'v',    # v down-pointing triangle
    '\u25b2': '^',    # ^ up-pointing triangle
    '\u25c0': '<',    # < left-pointing triangle
    '\u2714': 'v',    # v heavy check mark
    '\u2716': 'x',    # x heavy multiplication
    '\u274c': 'x',    # x cross mark
    '\u2764': '<3',   # <3 heart
    '\u2605': '*',    # * black star
    '\u2606': '*',    # * white star
    # box drawing characters
    '\u2500': '-',    # - horizontal
    '\u2501': '=',    # = heavy horizontal (━)
    '\u2502': '|',    # | vertical
    '\u2503': '|',    # | heavy vertical
    '\u250c': '+',    # + box corners
    '\u2510': '+',
    '\u2514': '+',
    '\u2518': '+',
    '\u251c': '+',
    '\u2524': '+',
    '\u252c': '+',
    '\u2534': '+',
    '\u253c': '+',
    '\u2550': '=',    # = double horizontal
    '\u2551': '|',    # | double vertical
    '\u256c': '+',    # + double cross
    # white/black squares
    '\u25a0': '#',
    '\u25a1': '#',
    '\u25aa': '#',
    '\u25ab': '#',
})


def safe_str(value: Any) -> str:
    """
    cp949 콘솔에서 안전하게 출력 가능한 문자열로 변환한다.

    1단계: 알려진 특수문자를 ASCII로 치환
    2단계: 그래도 cp949 인코딩 불가면 errors='replace'로 마지막 정리
    """
    text = value if isinstance(value, str) else str(value)
    text = text.translate(_CHAR_MAP)
    try:
        text.encode('cp949')
        return text
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode('cp949', errors='replace').decode('cp949')


def safe_print(*args: Any, **kwargs: Any) -> None:
    """safe_str()을 거쳐 print하는 래퍼."""
    safe_args = tuple(safe_str(a) for a in args)
    print(*safe_args, **kwargs)


class SafeLogFilter(logging.Filter):
    """
    logging 시스템 전체에 걸어두는 필터.
    모든 LogRecord의 msg와 args를 safe_str()로 정규화한다.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg:
            record.msg = safe_str(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: safe_str(v) if isinstance(v, str) else v
                               for k, v in record.args.items()}
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(safe_str(v) if isinstance(v, str) else v
                                    for v in record.args)
        return True


def _asyncio_exception_handler(loop: Any, context: dict) -> None:
    """
    asyncio 백그라운드 태스크의 미처리 예외를 안전하게 로그한다.
    기본 핸들러는 cp949 콘솔에서 UnicodeEncodeError를 일으킬 수 있다.
    """
    exc = context.get('exception')
    msg = context.get('message', 'Unknown asyncio error')
    if exc:
        safe_print(f"[asyncio] unhandled exception: {type(exc).__name__}: {exc}")
    else:
        safe_print(f"[asyncio] {msg}")


def configure_safe_logging() -> None:
    """
    서버 시작 시 1회 호출한다 (main.py 최상단에서 호출).

    - sys.stdout / sys.stderr 를 UTF-8 + errors='replace'로 재설정
    - root logger에 SafeLogFilter 설치 (uvicorn 포함 모든 핸들러에 전파)
    - 이미 등록된 핸들러에도 개별 필터 추가
    """
    # 1. stdout/stderr 재설정 (TextIOWrapper.reconfigure는 in-place 수정)
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    # 2. root logger + uvicorn 관련 logger 전체에 SafeLogFilter 설치
    safe_filter = SafeLogFilter()

    def _attach(logger_obj: logging.Logger) -> None:
        if not any(isinstance(f, SafeLogFilter) for f in logger_obj.filters):
            logger_obj.addFilter(safe_filter)
        for h in logger_obj.handlers:
            if not any(isinstance(f, SafeLogFilter) for f in h.filters):
                h.addFilter(safe_filter)

    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        _attach(logging.getLogger(name))


def install_asyncio_exception_handler() -> None:
    """
    이벤트 루프가 준비된 후 호출한다 (lifespan 함수 내부).
    asyncio 태스크의 미처리 예외를 safe_print로 출력한다.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(_asyncio_exception_handler)
    except RuntimeError:
        pass
