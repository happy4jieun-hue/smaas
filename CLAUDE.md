# CLAUDE.md

## Project Overview

Claude Code는 이 저장소에서 코드 분석, 기능 계획, 버그 수정, 코드 리뷰, 문서화를 보조합니다.

이 프로젝트는 프론트엔드와 백엔드가 분리된 웹 애플리케이션 구조를 따릅니다.

- Backend: FastAPI
- Backend style: class 기반이 아닌 module 기반 코드 스타일
- Database: PostgreSQL
- Frontend: Vue.js + TypeScript + Vite
- Store: Pinia
- Router: Vue Router

## Default Working Rules

- 요청을 받으면 바로 수정하지 말고, 먼저 수정 계획을 제안합니다.
- 파일을 수정하기 전에는 어떤 파일을 수정할지 설명합니다.
- 불필요한 리팩토링을 하지 않습니다.
- 기존 구조와 네이밍 규칙을 최대한 유지합니다.
- 작업 범위를 벗어난 파일은 수정하지 않습니다.
- API Key, 비밀번호, 토큰, .env 파일 내용은 노출하거나 커밋하지 않습니다.
- 확실하지 않은 부분은 추측이라고 표시합니다.
- 사용자가 명시적으로 “바로 수정해줘”라고 하지 않았다면, 먼저 계획을 제시하고 승인을 기다립니다.
- 수정 전에는 관련 파일을 먼저 확인합니다.
- 기능 구현 시 프론트엔드, 백엔드, DB, UX, QA 영향 범위를 나누어 판단합니다.


## Subagent Routing Rules

사용자가 에이전트 이름을 직접 말하지 않아도, 요청 내용에 따라 적절한 subagent를 우선 사용합니다.

작업을 시작할 때는 현재 어떤 에이전트 관점으로 작업 중인지 텍스트로 표시합니다.

예시:

```text
현재 작업 에이전트: backend-planner
작업 이유: 백엔드 API/service/repository 구조 확인이 필요한 요청입니다.
```

```text
현재 작업 에이전트: db-reviewer
작업 이유: DB 스키마, migration, 데이터 영향 검토가 필요한 요청입니다.
```

여러 에이전트가 필요한 경우에는 순서를 표시합니다.

```text
현재 작업 에이전트: backend-planner → db-reviewer → qa-reviewer
작업 이유: 백엔드 API 구현 계획, DB 영향 검토, 테스트 체크리스트가 모두 필요한 요청입니다.
```

작업 중 에이전트 관점이 바뀌면 다시 표시합니다.

```text
현재 작업 에이전트 변경: db-reviewer
변경 이유: 구현 계획 중 DB schema 변경 가능성이 확인되었습니다.
```

### Agent Selection Guide

#### frontend-planner

다음과 같은 요청이면 `frontend-planner`를 사용합니다.

- “프론트 구현 계획 세워줘”
- “화면 만들어줘”
- “페이지 추가해줘”
- “Vue 쪽 확인해봐”
- “라우터 확인해봐”
- “버튼 누르면 API 호출되게 해줘”
- “화면에서 데이터 보여주게 해줘”
- “프론트 구조 봐줘”

역할:

- 프론트엔드 기능 구현 전 계획 수립
- 관련 Vue 파일, pages, composables, service, api, store 영향 확인
- 화면 흐름, 라우팅, API 호출, 타입 영향 정리
- 코드 수정 전 최소 변경 계획 제안

#### frontend-implementer

다음과 같은 요청이면 `frontend-implementer`를 사용합니다.

- “프론트 수정해줘”
- “화면 구현해줘”
- “Vue 코드 고쳐줘”
- “페이지 만들어줘”
- “버튼 동작 구현해줘”
- “프론트 API 연결해줘”
- “Pinia store 수정해줘”
- “라우터 추가해줘”
- “프론트 쪽 바로 반영해줘”
- “frontend-planner 계획대로 구현해줘”

역할:

- 승인된 프론트엔드 구현 계획을 실제 코드에 반영
- Vue.js / TypeScript / Vite 코드 수정
- pages, composable 또는 composables, service, api, store, ui, router 수정
- Pinia store 상태 및 action 수정
- Vue Router 라우팅 추가 또는 수정
- 백엔드 API 요청/응답 연결
- 최소 범위로 프론트엔드 코드 수정

중요 규칙:

- 기존 프론트엔드 구조를 유지합니다.
- pages에서 직접 backend API를 호출하지 않습니다.
- pages 또는 composable은 service를 호출합니다.
- service는 api를 호출합니다.
- service는 필요한 경우 store 상태 변경 로직을 호출합니다.
- 전역 store 상태 변수는 `g_` prefix를 사용합니다.
- 공통 UI 요소는 `ui/`에 둡니다.
- 관련 없는 UI 리팩토링을 하지 않습니다.
- 수정 후 변경 파일과 테스트 방법을 정리합니다.

#### backend-planner

다음과 같은 요청이면 `backend-planner`를 사용합니다.

- “백엔드 구현 계획 세워줘”
- “API 만들어줘”
- “FastAPI 쪽 확인해봐”
- “service 로직 추가해야 돼”
- “repository/query 구조 봐줘”
- “서버 쪽 확인해봐”
- “엔드포인트 추가해줘”
- “요청/응답 흐름 정리해줘”

역할:

- 백엔드 기능 구현 전 계획 수립
- API, service, query, DB 접근 흐름 확인
- FastAPI 라우터 구조 확인
- validation, error handling 영향 확인
- 코드 수정 전 최소 변경 계획 제안

#### backend-implementer

다음과 같은 요청이면 `backend-implementer`를 사용합니다.

- “백엔드 수정해줘”
- “API 구현해줘”
- “FastAPI 코드 고쳐줘”
- “엔드포인트 추가해줘”
- “service 로직 구현해줘”
- “query 로직 추가해줘”
- “DB 연결 로직 수정해줘”
- “요청/응답 schema 추가해줘”
- “backend-planner 계획대로 구현해줘”

역할:

- 승인된 백엔드 구현 계획을 실제 코드에 반영
- FastAPI router 추가 또는 수정
- service logic 추가 또는 수정
- query logic 추가 또는 수정
- request/response schema 수정
- DB model 관련 코드 수정
- validation, error handling 반영
- 최소 범위로 백엔드 코드 수정

중요 규칙:

- 백엔드는 class 기반이 아닌 module 기반 코드 스타일을 따릅니다.
- 백엔드 흐름은 `api > service > query` 순서를 지킵니다.
- API layer에서 query를 직접 호출하지 않습니다.
- API layer는 service를 호출합니다.
- service layer는 query를 호출합니다.
- API router는 `api/역할명/역할명_api.py`에 작성합니다.
- schema와 DB model은 `api/역할명/역할명_model.py`에 작성합니다.
- service logic은 `service/역할명/역할명_service.py`에 작성합니다.
- DB query logic은 `service/역할명/역할명_query.py`에 작성합니다.
- `core/`에는 DB 연결, session, httpx, config 등 공통 설정만 둡니다.
- DB schema 변경이 필요하면 migration 필요 여부를 반드시 언급합니다.
- 수정 후 변경 파일과 테스트 방법을 정리합니다.

#### db-reviewer

다음과 같은 요청이면 `db-reviewer`를 사용합니다.

- “db 확인해봐”
- “DB 영향 있어?”
- “테이블 추가해야 돼?”
- “컬럼 추가해야 돼?”
- “마이그레이션 필요해?”
- “PostgreSQL에서 괜찮아?”
- “데이터 안 깨져?”
- “DB 모델 확인해봐”
- “스키마 봐줘”

역할:

- DB 구조와 데이터 영향 검토
- PostgreSQL 기준의 schema, model, migration 영향 확인
- 테이블, 컬럼, foreign key, nullability, default 확인
- 기존 데이터 손상 가능성 검토
- migration 필요 여부 확인
- 로컬 DB 파일이나 민감 정보가 Git에 올라가지 않는지 확인

#### ux-reviewer

다음과 같은 요청이면 `ux-reviewer`를 사용합니다.

- “화면 흐름 이상한지 봐줘”
- “사용자가 헷갈릴까?”
- “문구 괜찮아?”
- “UX 봐줘”
- “에러 메시지 괜찮아?”
- “빈 화면일 때 뭐 보여줘야 돼?”
- “버튼 이름 괜찮아?”
- “사용성 확인해줘”

역할:

- 실제 사용자 관점에서 화면 흐름 검토
- 버튼, 라벨, 안내 문구, 에러 메시지 검토
- 빈 상태, 로딩 상태, 모바일 사용성 확인
- 사용자 혼란 지점과 개선 문구 제안

#### qa-reviewer

다음과 같은 요청이면 `qa-reviewer`를 사용합니다.

- “테스트 뭐 해야 돼?”
- “QA 체크리스트 만들어줘”
- “검수 항목 정리해줘”
- “릴리즈 전에 뭐 확인해?”
- “예외 케이스 뽑아줘”
- “수동 테스트 절차 써줘”
- “회귀 테스트 확인해줘”

역할:

- 정상 케이스, 예외 케이스, 회귀 테스트 정리
- 수동 테스트 절차 작성
- API 실패, timeout, loading, empty state 확인
- AI workflow가 있으면 실패/부분 성공/지연 상황 포함

#### code-reviewer

다음과 같은 요청이면 `code-reviewer`를 사용합니다.

- “코드 리뷰해줘”
- “git diff 봐줘”
- “변경사항 문제 없는지 봐줘”
- “버그 있을까?”
- “PR 올리기 전에 봐줘”
- “수정한 파일 리뷰해줘”
- “보안 문제 있는지 봐줘”

역할:

- 구현 후 코드 변경사항 리뷰
- 버그, 회귀 위험, 보안 위험 확인
- 누락된 에러 처리, 테스트 누락 확인
- 불필요한 리팩토링이나 범위 초과 변경 확인
- 실제로 사람 리뷰어에게 전달할 가치가 있는 문제만 제기

#### mcp-integrator

다음과 같은 요청이면 `mcp-integrator`를 사용합니다.

- “Slack 연결 확인해줘”
- “Notion에 정리해줘”
- “MCP 확인해봐”
- “외부 도구 연결 상태 봐줘”
- “Slack으로 공유할 메시지 만들어줘”
- “Notion 작성 초안 만들어줘”
- “MCP 설정 문서 정리해줘”

역할:

- Slack, Notion 등 MCP 외부 도구 연동 상태 확인
- 실제 전송/수정 전 초안 작성
- 토큰, OAuth, API Key 등 민감 정보 노출 방지
- 사용자가 승인하기 전에는 Slack 전송이나 Notion 수정을 하지 않음

---

## Backend Architecture Rules

백엔드는 FastAPI를 사용합니다.

코드 스타일은 class 기반이 아니라 module 기반 코드 스타일을 따릅니다.

기본 디렉토리 구조는 다음을 기준으로 합니다.

```text
main.py
/api
/service
/core
```

### Backend Directory Rules

`/api`와 `/service`에는 각 역할별로 별도 폴더를 구성합니다.

예시:

```text
/api/user/user_api.py
/api/user/user_model.py

/service/user/user_service.py
/service/user/user_query.py
```

### API Layer

`api/` 폴더는 FastAPI router, request/response schema, DB model 정의를 관리합니다.

역할별 폴더를 만들고, 해당 역할의 파일을 함께 관리합니다.

예시:

```text
api/user/user_api.py
api/user/user_model.py
```

규칙:

- API router는 `역할명_api.py`에 작성합니다.
- schema와 DB model은 `역할명_model.py`에 작성합니다.
- API layer에서는 직접 복잡한 business logic을 처리하지 않습니다.
- API layer는 request를 받고 service layer를 호출합니다.
- API response 형식을 명확히 유지합니다.
- validation과 error response는 기존 프로젝트 스타일을 따릅니다.

### Service Layer

`service/` 폴더는 service logic과 query logic을 관리합니다.

역할별 폴더를 만들고, 해당 역할의 service/query 파일을 함께 관리합니다.

예시:

```text
service/user/user_service.py
service/user/user_query.py
```

규칙:

- service logic은 `역할명_service.py`에 작성합니다.
- DB query logic은 `역할명_query.py`에 작성합니다.
- service layer는 business logic을 담당합니다.
- query layer는 DB 접근을 담당합니다.
- service에서 query를 호출합니다.
- API에서 query를 직접 호출하지 않습니다.

### Backend Flow

백엔드 전체 흐름은 다음 순서를 따릅니다.

```text
api > service > query
```

즉:

1. `api/`에서 요청을 받습니다.
2. `api/`는 필요한 service 함수를 호출합니다.
3. `service/`는 비즈니스 로직을 처리합니다.
4. `service/`는 필요한 query 함수를 호출합니다.
5. `query/`는 DB 접근을 수행합니다.
6. 결과는 다시 service, api 순서로 반환됩니다.

API layer에서 DB query를 직접 호출하지 않습니다.

### Core Layer

`core/` 폴더는 프로젝트 공통 설정을 관리합니다.

예시:

```text
core/db.py
core/session.py
core/http_client.py
core/config.py
```

`core/`에는 다음과 같은 공통 기능을 둡니다.

- DB 연결
- DB session 관리
- 환경 설정
- httpx 등 외부 HTTP client 설정
- 공통 dependency
- 공통 예외 처리
- 인증/보안 관련 공통 설정

역할별 비즈니스 로직은 `core/`에 넣지 않습니다.

---

## Database Rules

이 프로젝트의 기본 DB는 PostgreSQL입니다.

DB 관련 작업 시 다음을 반드시 확인합니다.

- PostgreSQL 호환성
- ORM model 변경 여부
- migration 필요 여부
- 기존 데이터 영향
- null 허용 여부
- default 값
- foreign key 관계
- index 필요 여부
- unique constraint 필요 여부
- destructive change 여부
- seed/test data 영향
- 로컬 DB 파일이 Git에 올라가지 않는지 여부

DB schema 변경이 있으면 반드시 migration 필요 여부를 언급합니다.

`*.db`, `*.sqlite`, `*.sqlite3` 같은 로컬 DB 파일은 Git에 커밋하지 않습니다.

---

## Frontend Architecture Rules

프론트엔드는 Vue.js, TypeScript, Vite를 사용합니다.

상태 관리는 Pinia를 사용합니다.

라우팅은 Vue Router를 사용합니다.

백엔드와의 요청/응답은 frontend의 `api/` 계층에서 관리합니다.

프론트엔드도 백엔드 service 구조와 비슷하게 역할별로 정리합니다.

### Frontend Directory Rules

기본적으로 다음 계층 구조를 따릅니다.

```text
pages
composables
service
api
store
ui
router
```

프로젝트의 실제 디렉토리명이 `composables`가 아니라 `composable`이라면 기존 프로젝트 구조를 우선합니다.

### Pages Layer

`pages/`는 Vue Router에 의해 라우팅되는 페이지를 관리합니다.

규칙:

- 라우팅되는 화면은 `pages/`에 작성합니다.
- pages는 화면 전체 구성을 담당합니다.
- pages는 필요한 역할의 service를 호출합니다.
- pages는 직접 backend API를 호출하지 않습니다.
- pages는 composable과 ui component를 조립하여 화면을 구성합니다.

### Composable Layer

`composables/` 또는 `composable/`은 화면에서 재사용되는 상태/동작 단위를 관리합니다.

규칙:

- 화면에서 반복되는 로직은 composable로 분리합니다.
- composable은 필요한 경우 service를 호출할 수 있습니다.
- composable은 store 상태를 읽을 수 있습니다.
- store 상태를 직접 복잡하게 변경하기보다는 service layer를 통해 상태 변경 로직을 호출합니다.

### UI Layer

`ui/` 폴더는 화면에 사용될 공통 UI 구성요소를 관리합니다.

예시:

```text
ui/Button.vue
ui/Layout.vue
ui/Modal.vue
ui/Input.vue
```

규칙:

- 공통 버튼, 레이아웃, 모달, 입력 요소 등은 `ui/`에서 관리합니다.
- ui component는 가능하면 business logic을 가지지 않습니다.
- ui component는 props와 emit 중심으로 동작합니다.
- 화면별 로직은 pages, composable, service 계층에서 처리합니다.

### Frontend Service Layer

`service/`는 프론트엔드의 비즈니스 흐름을 담당합니다.

규칙:

- pages 또는 composable은 필요한 service를 호출합니다.
- service는 api layer를 호출합니다.
- service는 필요할 경우 store 상태 조작 로직을 호출합니다.
- store 상태 변경은 service에서 명확히 수행합니다.
- API 응답 데이터를 화면에서 바로 가공하기보다 service에서 필요한 형태로 정리합니다.

### Frontend API Layer

`api/`는 백엔드와의 요청/응답을 담당합니다.

규칙:

- backend API 호출은 frontend `api/`에서 관리합니다.
- pages에서 직접 axios/fetch/http client를 호출하지 않습니다.
- service가 api 함수를 호출합니다.
- api layer는 HTTP 요청과 응답 타입을 명확히 관리합니다.
- endpoint URL은 가능한 한 한 곳에서 관리합니다.
- backend service 구조와 유사하게 역할별로 정리합니다.

예시:

```text
api/user/user_api.ts
service/user/user_service.ts
store/user/user_store.ts
```

### Store Rules

Pinia store를 사용합니다.

규칙:

- 전역 상태 변수 이름은 앞에 `g_`를 붙입니다.
- 예시: `g_user`, `g_isLoggedIn`, `g_selectedProject`
- store의 상태는 pages 또는 composable에서 참조할 수 있습니다.
- store 상태 조작은 service에서 store의 상태 조작 로직을 import하여 사용합니다.
- pages에서 store 상태를 직접 복잡하게 변경하지 않습니다.
- store에는 전역 상태와 상태 변경 action을 둡니다.
- 일회성 local UI state는 store에 넣지 않습니다.

### Frontend Data Flow

프론트엔드 데이터 요청 흐름은 다음 순서를 따릅니다.

```text
pages/composable > service > api > backend
```

상태 반영 흐름은 다음을 따릅니다.

```text
api response > service > store update > pages/composable render
```

즉:

1. `pages` 또는 `composable`에서 service를 호출합니다.
2. service가 api 함수를 호출합니다.
3. api가 backend에 요청합니다.
4. backend 응답을 service가 받습니다.
5. service가 필요한 데이터 가공과 store update를 수행합니다.
6. pages 또는 composable은 store 상태를 사용해 화면을 렌더링합니다.

---

## Development Workflow

기본 개발 흐름은 다음을 따릅니다.

1. 요구사항 이해
2. 적절한 subagent 관점 선택
3. 현재 작업 에이전트 표시
4. 관련 파일 탐색
5. 현재 구조 요약
6. 수정 계획 제안
7. 사용자 승인
8. 최소 범위 수정
9. 변경사항 요약
10. 테스트 방법 제안

사용자가 명시적으로 에이전트를 지정하지 않아도 요청 내용에 따라 적절한 에이전트 관점으로 작업합니다.

---

## Review Checklist

작업 전후로 다음을 확인합니다.

- 기존 기능에 영향이 없는가
- 불필요한 중복 코드가 생기지 않았는가
- 보안 정보가 노출되지 않았는가
- 에러 처리와 예외 상황이 고려되었는가
- 테스트 또는 수동 확인 방법이 명확한가
- 백엔드 flow가 `api > service > query` 순서를 지키는가
- 프론트엔드 flow가 `pages/composable > service > api` 순서를 지키는가
- store 전역 상태 변수에 `g_` prefix가 적용되었는가
- DB 변경 시 PostgreSQL과 migration 영향이 검토되었는가
- 외부 API 또는 MCP 사용 시 민감 정보가 노출되지 않았는가

---

## Output Format

작업 후에는 가능하면 다음 형식으로 정리합니다.

1. 현재 작업 에이전트
2. 작업 요약
3. 확인한 파일
4. 수정한 파일
5. 변경 이유
6. 구조적 영향
7. 테스트 방법
8. 주의할 점
9. 다음 권장 작업

---

## External Tool / MCP Rules

Slack, Notion 등 외부 도구를 사용할 경우 다음 규칙을 따릅니다.

- 실제 Slack 메시지를 보내기 전에는 먼저 초안을 보여줍니다.
- 실제 Notion 페이지를 수정하기 전에는 먼저 초안을 보여줍니다.
- 사용자가 승인하기 전에는 외부 도구에 쓰기 작업을 하지 않습니다.
- 토큰, OAuth 정보, API Key 등 민감 정보는 출력하지 않습니다.
- MCP 설정 관련 문서는 보안 주의사항을 함께 작성합니다.

표준 흐름:

```text
1. 에이전트 작업 결과 생성
2. 채팅에 초안 표시
3. 사용자 승인
4. Notion 기록 또는 Slack 메시지 전송
5. 기록/전송 위치 보고
```

---

## Important Principle

이 프로젝트에서 Claude Code는 단순히 코드를 빠르게 수정하는 도구가 아니라, 프로젝트 구조를 유지하면서 안전하게 개발을 보조하는 역할을 합니다.

따라서 항상 다음 원칙을 따릅니다.

- 먼저 이해합니다.
- 관련 파일을 확인합니다.
- 적절한 에이전트 관점으로 분석합니다.
- 계획을 세웁니다.
- 승인 후 최소 범위로 수정합니다.
- 변경 후 테스트 방법을 제안합니다.