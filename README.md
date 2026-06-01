# Zighang Personal MCP Server

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-unittest-lightgrey.svg)](#testing)

개인 이력서와 포트폴리오를 기준으로 Zighang 채용공고를 검색, 추천, 저장하고 일일 digest를 생성하는 MCP 서버입니다.

이 프로젝트는 “매일 볼 만한 공고를 MCP 클라이언트나 Agent가 호출해서 읽고 답변할 수 있게 만드는 것”에 초점을 둡니다. 채용공고 검색, 추천 점수화, 필터 프로필, 로컬 상태 저장, markdown/webhook/email digest 전송을 모두 로컬 중심으로 제공합니다.

## Highlights

- Public Zighang 공고 목록, 상세, 필터 메타 API client
- MCP tools: 검색, 상세 조회, 추천, 매칭 설명, 필터 프로필, 상태 저장, digest 생성
- 로컬 이력서/포트폴리오 분석: markdown/text/PDF 텍스트 추출 지원
- 결정적 추천 점수화: 기술 키워드, 프로젝트, 상태값 기반
- 일일 digest 생성: `reports/daily/YYYY-MM-DD.md`
- 알림 채널: `markdown`, `console`, `webhook`, `email`
- fixture 기반 unit test와 opt-in live API smoke test 분리

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests
```

MCP 서버 실행:

```bash
zighang-mcp
```

또는 editable install 없이 모듈로 실행:

```bash
.venv/bin/python -m src.mcp.server
```

## Configuration

```bash
cp .env.example .env
```

주요 환경변수:

| Variable | Default | Description |
| --- | --- | --- |
| `ZIGHANG_BASE_URL` | `https://api.zighang.com/api` | Zighang API base URL |
| `ZIGHANG_AUTH_TOKEN` | empty | 선택. 사용자가 직접 제공한 auth token |
| `ZIGHANG_COOKIE` | empty | 선택. 사용자가 직접 제공한 cookie |
| `DEFAULT_PAGE_SIZE` | `20` | 기본 공고 목록 page size |
| `REQUEST_DELAY_MS` | `300` | API 요청 간격 |
| `RESUME_PATH` | `resumes/resume.md` | 기본 이력서 파일 |
| `PORTFOLIO_PATH` | `portfolios/portfolio.md` | 기본 포트폴리오 파일 |
| `NOTIFICATION_CHANNEL` | `markdown` | `markdown`, `console`, `webhook`, `email`, `telegram`, `discord` |
| `WEBHOOK_URL` | empty | webhook digest 수신 URL |
| `EMAIL_HOST` | empty | SMTP host |
| `EMAIL_PORT` | `587` | SMTP port. STARTTLS 기준 |
| `EMAIL_USERNAME` | empty | SMTP username. 발신자와 수신자로도 사용 |
| `EMAIL_PASSWORD` | empty | SMTP password 또는 앱 비밀번호 |
| `TELEGRAM_BOT_TOKEN` | empty | Telegram bot token |
| `TELEGRAM_CHAT_ID` | empty | Telegram message 수신 chat ID |
| `DISCORD_WEBHOOK_URL` | empty | Discord channel webhook URL |

민감한 이력서, 포트폴리오, 캐시, 리포트는 기본적으로 git ignore 됩니다.

## MCP Client Setup

MCP 클라이언트 설정 예:

```json
{
  "mcpServers": {
    "zighang": {
      "command": "/absolute/path/to/zighang-mcp/.venv/bin/zighang-mcp",
      "env": {
        "ZIGHANG_BASE_URL": "https://api.zighang.com/api",
        "RESUME_PATH": "/absolute/path/to/zighang-mcp/resumes/resume.md",
        "PORTFOLIO_PATH": "/absolute/path/to/zighang-mcp/portfolios/portfolio.md",
        "NOTIFICATION_CHANNEL": "markdown"
      }
    }
  }
}
```

상대 경로는 실행 위치에 따라 달라질 수 있으므로 운영용 MCP client 설정에는 절대 경로를 권장합니다.

## Resume And Portfolio Files

기본 파일 위치:

- `resumes/resume.md`
- `resumes/resume.pdf`
- `portfolios/portfolio.md`
- `portfolios/portfolio.pdf`
- `portfolios/portfolio.html`

지원 범위:

- markdown/text 파일은 UTF-8 텍스트로 직접 읽습니다.
- 텍스트 기반 PDF는 `pypdf`로 페이지 텍스트를 추출합니다.
- 로컬 HTML 파일과 Notion HTML export는 화면에 보이는 텍스트를 추출합니다.
- `script`, `style`, `noscript` 내용은 분석에서 제외합니다.
- 스캔 PDF나 이미지 기반 PDF처럼 텍스트가 거의 추출되지 않는 파일은 OCR 필요 오류를 반환합니다.
- OCR은 아직 포함하지 않습니다. 필요한 경우 macOS Vision OCR, Tesseract, 외부 OCR API 같은 별도 단계가 필요합니다.
- 웹 URL 직접 fetch, private Notion API 접근, 인증 필요한 Notion page 분석은 아직 포함하지 않습니다.

## Notification Channels

`daily_job_digest`는 먼저 `reports/daily/YYYY-MM-DD.md`를 저장하고, `NOTIFICATION_CHANNEL`에 따라 추가 전송을 수행합니다.

### Markdown

```bash
NOTIFICATION_CHANNEL=markdown
```

기본값입니다. digest markdown 파일만 저장합니다.

### Console

```bash
NOTIFICATION_CHANNEL=console
```

digest markdown을 stdout으로 출력합니다. 로컬 디버깅이나 수동 실행에 유용합니다.

### Webhook

```bash
NOTIFICATION_CHANNEL=webhook
WEBHOOK_URL=https://example.com/webhook
```

전송 payload:

```json
{
  "text": "# Zighang Daily Job Digest - YYYY-MM-DD\n..."
}
```

HTTP 2xx가 아닌 응답이나 네트워크 오류는 MCP tool 호출 실패로 드러납니다.

### Email

```bash
NOTIFICATION_CHANNEL=email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-account@gmail.com
EMAIL_PASSWORD=your-app-password
```

동작:

- SMTP STARTTLS를 사용합니다.
- `EMAIL_USERNAME`과 `EMAIL_PASSWORD`로 로그인합니다.
- `EMAIL_USERNAME`을 발신자와 수신자로 모두 사용합니다.
- 메일 제목은 `Zighang Daily Job Digest`입니다.
- 본문은 markdown digest 원문을 plain text로 보냅니다.

Gmail 같은 서비스는 일반 계정 비밀번호가 아니라 앱 비밀번호 또는 별도 SMTP 정책 설정이 필요할 수 있습니다.

### Telegram

```bash
NOTIFICATION_CHANNEL=telegram
TELEGRAM_BOT_TOKEN=123456:bot-token
TELEGRAM_CHAT_ID=123456789
```

Telegram Bot API의 `sendMessage`를 호출해 digest markdown 원문을 보냅니다.

### Discord

```bash
NOTIFICATION_CHANNEL=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Discord webhook에 digest markdown 원문을 `content`로 보냅니다.

## Daily Operation

MCP 서버는 자체 scheduler를 포함하지 않습니다. 자동 digest 운영에는 cron, launchd, GitHub Actions 같은 외부 scheduler가 `zighang-digest` runner를 원하는 시간에 실행하도록 설정하세요.

### Agent/MCP 호출 모델

일반적인 사용 방식은 MCP client나 Agent가 `daily_job_digest` tool을 호출하고, 반환된 `markdown` 또는 `report_path`를 읽어 사용자에게 요약하는 것입니다.

예:

```text
직행 MCP의 daily_job_digest를 실행해줘. resume_profile_id는 default, top_n은 5로 해줘.
```

digest는 저장된 필터 프로필을 기준으로 추천 공고를 수집합니다. 먼저 `save_filter_profile`로 알림 대상 필터를 저장하세요.

예:

```text
직행 MCP에 백엔드 필터 프로필을 저장해줘.
profile_id는 backend, 이름은 Backend, notifications_enabled는 true로 해줘.
필터는 IT_개발 직군 중심으로 설정해줘.
```

활성 필터 프로필이 없으면 digest는 공고 추천을 시도하지 않고 `setup_required=true`와 설정 안내 markdown을 반환합니다.

### Scheduler runner

```bash
.venv/bin/zighang-digest
```

옵션:

```bash
.venv/bin/zighang-digest --resume-profile-id default --limit-per-profile 5 --top-n 5
.venv/bin/zighang-digest --include-seen
.venv/bin/zighang-digest --dry-run
.venv/bin/zighang-digest --json
```

기본 출력:

```text
report_path=reports/daily/YYYY-MM-DD.md
notification_channel=markdown
notification_result=reports/daily/YYYY-MM-DD.md
```

`--dry-run`은 digest report 생성까지 확인하되 webhook/email 전송은 하지 않습니다. cron이나 launchd에 올리기 전에 설정과 파일 경로를 점검할 때 사용하세요.

### cron 예시

매일 오전 9시에 자동 digest를 만드는 예시:

```cron
0 9 * * * cd /absolute/path/to/zighang-mcp && .venv/bin/zighang-digest >> logs/digest.log 2>&1
```

`zighang-digest`는 실행 위치의 `.env`를 자동으로 읽습니다. OS 환경변수가 이미 설정되어 있으면 OS 환경변수가 `.env`보다 우선합니다.

### macOS launchd 예시

운영에서는 launchd plist에서 repo 경로를 working directory로 지정하고, `ProgramArguments`에 `.venv/bin/zighang-digest`를 둡니다. `StandardOutPath`와 `StandardErrorPath`를 지정하면 실행 로그를 남길 수 있습니다.

### GitHub Actions 예시

GitHub Actions에서는 scheduled workflow에서 `.venv/bin/zighang-digest --json`을 실행할 수 있습니다. 이력서와 SMTP/webhook secret은 repository secrets로 다뤄야 하며, 개인 데이터가 로그에 출력되지 않도록 주의해야 합니다.

## Tools

대표 MCP tools:

| Tool | Purpose |
| --- | --- |
| `recommend_jobs` | 이력서/필터/선호값 기반 개인화 추천 |
| `search_latest_jobs_for_me` | 저장된 선호값 기반 최신 공고 검색 |
| `search_latest_it_jobs` | 개인화 없는 최신 IT_개발 공고 검색 |
| `search_today_it_jobs` | 오늘 등록된 IT_개발 공고 검색 |
| `search_jobs_posted_on` | 특정 날짜에 등록된 공고 검색 |
| `search_jobs` | 명시적 필터 기반 저수준 공고 검색 |
| `search_pinned_jobs` | 직행 pinned 공고 검색 |
| `get_job_detail` | 공고 상세 조회 |
| `list_filter_options` | 필터 옵션 조회 |
| `explain_job_match` | 특정 공고와 이력서의 매칭 설명 |
| `save_filter_profile` | 필터 프로필 저장 |
| `list_filter_profiles` | 저장된 필터 프로필 목록 |
| `update_filter_profile` | 필터 프로필 수정 |
| `delete_filter_profile` | 필터 프로필 삭제 |
| `daily_job_digest` | 활성 필터 기반 일일 digest 생성 및 알림 전송 |
| `track_job_status` | MCP 로컬 공고 상태 저장 |
| `list_tracked_jobs` | MCP 로컬 추적 공고 조회 |
| `mark_job_status` | `track_job_status` 호환 alias |
| `list_saved_jobs` | `list_tracked_jobs` 호환 alias |
| `get_user_preferences` | 로컬 사용자 선호값 조회 |
| `update_user_preferences` | 로컬 사용자 선호값 수정 |
| `update_user_preferences_from_text` | 자연어 설명에서 로컬 사용자 선호값 추출/저장 |
| `clear_user_preferences` | 로컬 사용자 선호값 초기화 |
| `load_resume_profile` | 파일에서 이력서 프로필 로드 |
| `update_resume_profile` | inline text 또는 path로 이력서 프로필 갱신 |
| `analyze_resume_profile` | 이력서 프로필 분석 |
| `extract_skills_from_resume` | 기술 키워드 추출 |
| `extract_projects_from_portfolio` | 프로젝트 라인 추출 |

상세 입력/출력은 [MCP Tool Specification](docs/mcp-tools.md)을 참고하세요.

### Agent tool 선택 기준

| 사용자 요청 | 우선 사용할 tool |
| --- | --- |
| "나에게 맞는 공고", "내 이력 기준 추천" | `recommend_jobs` |
| "내 선호도 기준 최신 공고" | `search_latest_jobs_for_me` |
| "직행 최신 IT 공고" | `search_latest_it_jobs` |
| "오늘 올라온 IT 공고" | `search_today_it_jobs` |
| "2026-05-20에 올라온 공고" | `search_jobs_posted_on` |
| "Java, 서울, 정규직으로 검색" | `search_jobs` |
| "나는 백엔드/데이터 플랫폼, 서울 정규직, 인턴 제외를 원해" | `update_user_preferences_from_text` |

`recommend_jobs`는 `score_breakdown`, `matched_signals`, `risk_flags`, `evidence_snippets`, `detail_fetched`를 함께 반환합니다. Agent는 이 구조화 근거를 사용해 추가 상세 조회를 줄이고 최종 설명을 만들 수 있습니다.

`list_saved_jobs`는 기존 호환 alias입니다. 직행 계정의 관심공고가 아니라 MCP 로컬 추적 상태를 읽으므로 새 호출에서는 `list_tracked_jobs`를 사용하세요.

## Usage Examples

### 필터 기반 검색

```json
{
  "keyword": "Java",
  "job_categories": ["IT_개발"],
  "job_subcategories": ["서버_백엔드"],
  "regions": ["서울"],
  "career_min": 2,
  "career_max": 5,
  "employment_types": ["정규직"],
  "sort": "latest",
  "page": 0,
  "size": 10
}
```

### 필터 프로필 저장

```json
{
  "profile_id": "backend-seoul",
  "name": "백엔드 / 서울 / 2~5년차",
  "filters": {
    "job_categories": ["IT_개발"],
    "job_subcategories": ["서버_백엔드"],
    "regions": ["서울"],
    "career_min": 2,
    "career_max": 5,
    "employment_types": ["정규직"],
    "sort": "latest"
  },
  "notifications_enabled": true
}
```

### Digest 생성

```json
{
  "resume_profile_id": "default",
  "limit_per_profile": 5,
  "top_n": 5,
  "exclude_seen": true
}
```

반환값에는 `report_path`, `markdown`, `profiles`, `notification_channel`, `notification_result`가 포함됩니다.

## Data Layout

| Path | Purpose |
| --- | --- |
| `data/cache/state.json` | 필터 프로필, 이력서 프로필, 공고 상태 저장 |
| `reports/daily/YYYY-MM-DD.md` | 일일 digest markdown |
| `resumes/` | 개인 이력서 파일 |
| `portfolios/` | 개인 포트폴리오 파일 |
| `tests/fixtures/` | unit test fixture |

## Testing

기본 테스트:

```bash
.venv/bin/python -m unittest discover -s tests
```

MCP 서버 생성 확인:

```bash
.venv/bin/python -c "from src.mcp.server import build_server; print(type(build_server()).__name__)"
```

Live API smoke test는 기본 테스트에서 skip됩니다. 실제 Zighang API 호출을 확인할 때만 실행하세요.

```bash
RUN_LIVE_API_TESTS=1 .venv/bin/python -m unittest tests.test_smoke_live_api
```

Live notification smoke test도 opt-in입니다. 실제 webhook 또는 SMTP 설정이 있을 때만 실행하세요.

```bash
RUN_LIVE_NOTIFICATION_TESTS=1 .venv/bin/python -m unittest tests.test_smoke_live_notifications
```

개별 채널만 검증하려면 unittest 테스트 이름을 지정하세요.

```bash
RUN_LIVE_NOTIFICATION_TESTS=1 .venv/bin/python -m unittest tests.test_smoke_live_notifications.LiveNotificationSmokeTests.test_live_webhook_delivery
RUN_LIVE_NOTIFICATION_TESTS=1 .venv/bin/python -m unittest tests.test_smoke_live_notifications.LiveNotificationSmokeTests.test_live_email_delivery
```

## Documentation

- [Zighang API notes](docs/zighang-api.md)
- [Zighang recruitment API notes](docs/zighang-recruitment-api.md)
- [MCP Tool Specification](docs/mcp-tools.md)
- [Recommendation Logic](docs/recommendation-logic.md)
- [Implementation Plan](docs/implementation-plan.md)

## Security And Privacy

- 개인 이력서, 포트폴리오, 캐시, 리포트는 git ignore 대상입니다.
- `ZIGHANG_AUTH_TOKEN`, `ZIGHANG_COOKIE`, `EMAIL_PASSWORD`, webhook URL은 repository에 커밋하지 마세요.
- webhook/email 전송 시 digest 본문에 개인 이력서 기반 추천 정보가 포함될 수 있습니다.
- 외부 scheduler나 CI를 사용할 때 secret 출력과 artifact 업로드 설정을 확인하세요.

## Project Status

현재는 개인용 MCP 서버로 설계된 초기 구현입니다. Zighang public API 형태 변화, 인증 정책, SMTP provider 정책에 따라 운영 설정이 달라질 수 있습니다.
