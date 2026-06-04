# Zighang Personal MCP Server

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-unittest-lightgrey.svg)](#testing)

개인 이력서와 포트폴리오를 기준으로 Zighang 채용공고를 검색, 추천, 저장하고 일일/주간 리포트로 분석할 수 있게 해주는 MCP 서버입니다.

핵심 목표는 단순 검색이 아니라, Agent에게 아래 흐름을 맡길 수 있게 만드는 것입니다.

```text
사용자 선호조건 설정
-> 오늘 맞는 공고 검색/추천
-> 매일 digest 저장 및 알림
-> 관심/제외/지원 상태 기록
-> 주간 공고 트렌드와 이력서 보완점 분석
```

## What You Can Ask

MCP 클라이언트나 Agent에서는 자연어로 이렇게 요청하는 것을 목표로 합니다.

| 하고 싶은 일 | 예시 요청 | 주로 쓰는 MCP tool |
| --- | --- | --- |
| 선호조건 저장 | "백엔드/데이터 플랫폼, 서울 정규직, 인턴 제외 조건으로 저장해줘" | `update_user_preferences_from_text` |
| 선호조건으로 오늘 공고 보기 | "저장된 선호조건으로 오늘 올라온 공고 보여줘" | `search_today_jobs_for_me` |
| 이력서 기준 추천 | "등록된 이력서 기준으로 맞는 공고 추천해줘" | `recommend_jobs` |
| 오늘자 리포트 생성 | "직행 오늘자 보고서 만들어줘" | `daily_job_digest_for_me` |
| 매일 알림용 digest | "저장된 필터 기준으로 daily digest 실행해줘" | `daily_job_digest` |
| 특정 공고 분석 | "이 공고가 등록된 이력서와 왜 맞는지 설명해줘" | `explain_job_match` |
| 공고 상태 기록 | "이 공고는 관심 있음으로 표시해줘" | `track_job_status` |
| 주간 분석 | "이번 주 공고 흐름 요약해줘" | `get_weekly_job_summary` |
| 시장 트렌드 | "최근 백엔드 공고 키워드 변화 알려줘" | `get_job_market_trends` |
| 이력서 보완점 | "최근 공고 기준으로 이력서 보완점 알려줘" | `get_resume_gap_analysis` |

## Recommended Workflow

### 1. 처음 한 번: 이력서와 선호조건 준비

이력서와 포트폴리오 파일을 로컬에 둡니다.

```text
resumes/resume.md
portfolios/portfolio.md
```

MCP에서 선호조건을 저장합니다.

```text
관심 직무는 백엔드와 데이터 플랫폼이고, 선호 지역은 서울/경기입니다.
정규직 위주로 보고 싶고, Spring Boot, Airflow, Kubernetes 경험을 활용할 수 있는 공고를 우선해줘.
인턴 공고는 제외해줘.
```

이 요청은 `user_preferences`에 저장되고 이후 검색, 추천, digest에 반영됩니다.

### 2. 매일: 오늘 맞는 공고 확인

즉시 확인할 때:

```text
저장된 선호조건으로 오늘 올라온 공고 중 괜찮은 것만 보여줘.
```

리포트로 남길 때:

```text
직행 오늘자 보고서 만들어줘. 상위 5개만 요약해줘.
```

생성된 digest는 기본적으로 아래 파일에 저장됩니다.

```text
reports/daily/YYYY-MM-DD.md
```

### 3. 자동 운영: 매일 정해진 시간에 digest 실행

MCP 서버 자체에는 scheduler가 없습니다. 자동 실행은 cron, launchd, GitHub Actions 같은 외부 scheduler가 `zighang-digest`를 실행하는 방식으로 구성합니다.

```bash
.venv/bin/zighang-digest --resume-profile-id default --limit-per-profile 5 --top-n 5
```

예: 매일 오전 8시 30분 cron 실행

```cron
30 8 * * * cd /absolute/path/to/zighang-mcp && .venv/bin/zighang-digest >> logs/digest.log 2>&1
```

알림은 `NOTIFICATION_CHANNELS`로 설정합니다.

```bash
NOTIFICATION_CHANNELS=markdown,telegram
```

지원 채널:

- `markdown`: 파일 저장
- `console`: stdout 출력
- `webhook`: HTTP webhook 전송
- `email`: SMTP email 전송
- `telegram`: Telegram Bot API 전송
- `discord`: Discord webhook 전송

### 4. 선택 사항: 피드백으로 추천 품질 개선

사용자가 매일 피드백을 남기지 않아도 중복 제거, 마감 관리, 주간 트렌드 분석은 가능합니다. 다만 관심/제외/지원 상태를 남기면 개인화 추천이 더 좋아집니다.

```text
이 공고는 관심 있음으로 표시해줘.
이 공고는 제외해줘.
이 공고는 지원 완료로 표시해줘.
```

저장 가능한 상태:

- `viewed`
- `bookmarked`
- `interested`
- `applied`
- `rejected`
- `ignored`

이 상태는 Zighang 계정 북마크가 아니라 MCP 로컬 상태입니다.

### 5. 주간: 누적 리포트 분석

매일 digest가 쌓이면 Agent에게 이런 분석을 요청할 수 있습니다.

```text
이번 주 공고 요약해줘.
최근 공고에서 많이 등장한 기술 키워드 알려줘.
지난주 대비 늘어난 직무/회사/지역을 알려줘.
등록된 이력서 기준으로 반복적으로 부족하게 보이는 부분 알려줘.
```

이 분석은 markdown을 다시 파싱하지 않고, digest 실행 시 함께 저장되는 구조화 snapshot을 사용합니다.

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

## MCP Client Setup

MCP 클라이언트에는 서버 실행 command만 등록하면 됩니다. 가장 단순한 설정은 아래 형태입니다.

```json
{
  "mcpServers": {
    "zighang": {
      "command": "/absolute/path/to/zighang-mcp/.venv/bin/zighang-mcp"
    }
  }
}
```

`command`는 MCP 클라이언트가 어디에서 실행되든 서버를 찾을 수 있어야 하므로 절대 경로를 권장합니다. `ZIGHANG_BASE_URL`, `RESUME_PATH`, `PORTFOLIO_PATH`, `DATA_DIR`, `REPORTS_DIR`, `NOTIFICATION_CHANNELS`는 기본값을 그대로 써도 됩니다.

MCP 클라이언트가 repo root가 아닌 위치에서 서버를 실행하거나, 이력서/리포트 경로를 명확히 고정하고 싶다면 아래처럼 로컬 데이터 경로도 절대 경로로 지정하세요.

```json
{
  "mcpServers": {
    "zighang": {
      "command": "/absolute/path/to/zighang-mcp/.venv/bin/zighang-mcp",
      "env": {
        "ZIGHANG_BASE_URL": "https://api.zighang.com/api",
        "RESUME_PATH": "/absolute/path/to/zighang-mcp/resumes/resume.md",
        "PORTFOLIO_PATH": "/absolute/path/to/zighang-mcp/portfolios/portfolio.md",
        "DATA_DIR": "/absolute/path/to/zighang-mcp/data/cache",
        "REPORTS_DIR": "/absolute/path/to/zighang-mcp/reports/daily",
        "NOTIFICATION_CHANNELS": "markdown"
      }
    }
  }
}
```

## Main MCP Tools

### Personal Search And Recommendation

| Tool | Purpose |
| --- | --- |
| `update_user_preferences_from_text` | 자연어에서 직무, 지역, 고용형태, 기술, 제외조건 추출 및 저장 |
| `get_user_preferences` | 저장된 사용자 선호조건 조회 |
| `search_latest_jobs_for_me` | 저장된 선호조건 기준 최신 공고 검색 |
| `search_today_jobs_for_me` | 저장된 선호조건 기준 오늘 등록 공고 검색 |
| `recommend_jobs` | 이력서/포트폴리오/선호조건 기반 추천 점수화 |
| `explain_job_match` | 특정 공고와 이력서의 매칭 이유 설명 |

### Digest And Analytics

| Tool | Purpose |
| --- | --- |
| `daily_job_digest_for_me` | 저장된 선호조건 기준 오늘자 digest 생성 |
| `daily_job_digest` | 활성 필터 프로필 기준 digest 생성 및 알림 전송 |
| `get_digest_history` | 최근 일일 digest snapshot 조회 |
| `get_weekly_job_summary` | 누적 snapshot 기반 주간 요약 |
| `get_job_market_trends` | 최근 기간과 이전 기간의 키워드/회사/지역/직무 변화 비교 |
| `get_resume_gap_analysis` | 반복 risk/gap 신호 기반 이력서 보완 분석 |

### Filters, Details, And Tracking

| Tool | Purpose |
| --- | --- |
| `search_jobs` | 명시적 필터 기반 저수준 공고 검색 |
| `search_jobs_posted_on` | 특정 날짜 등록 공고 검색 |
| `search_latest_it_jobs` | 개인화 없는 최신 IT_개발 공고 검색 |
| `search_today_it_jobs` | 개인화 없는 오늘 등록 IT_개발 공고 검색 |
| `search_pinned_jobs` | Zighang pinned 공고 검색 |
| `get_job_detail` | 공고 상세 조회. 기본적으로 로컬 상세 캐시 사용 |
| `save_filter_profile` | digest용 필터 프로필 저장 |
| `list_filter_profiles` | 필터 프로필 목록 조회 |
| `update_filter_profile` | 필터 프로필 수정 |
| `delete_filter_profile` | 필터 프로필 삭제 |
| `track_job_status` | 공고 상태를 MCP 로컬 상태로 저장 |
| `list_tracked_jobs` | MCP 로컬 추적 공고 조회 |

상세 입력/출력은 [MCP Tool Specification](docs/mcp-tools.md)을 참고하세요.

## Digest Output

Digest markdown은 사용자가 바로 판단할 수 있도록 아래 섹션으로 구성됩니다.

- `오늘의 최우선 공고`
- `새로 발견된 고득점 공고`
- `마감 임박`
- `관심 공고와 유사`
- `확인 필요`
- `필터별 추천`

각 공고에는 점수, 회사, 제목, 조건, 직무/키워드, 매칭 신호, 확인 필요 사항, 지원 URL이 포함됩니다.

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
| `DATA_DIR` | `data/cache` | 로컬 상태, 캐시, digest snapshot 저장 경로 |
| `REPORTS_DIR` | `reports/daily` | 일일 digest markdown 저장 경로 |
| `NOTIFICATION_CHANNELS` | `markdown` | `markdown`, `console`, `webhook`, `email`, `telegram`, `discord` |
| `WEBHOOK_URL` | empty | webhook digest 수신 URL |
| `EMAIL_HOST` | empty | SMTP host |
| `EMAIL_PORT` | `587` | SMTP port. STARTTLS 기준 |
| `EMAIL_USERNAME` | empty | SMTP username. 발신자와 수신자로도 사용 |
| `EMAIL_PASSWORD` | empty | SMTP password 또는 앱 비밀번호 |
| `TELEGRAM_BOT_TOKEN` | empty | Telegram bot token |
| `TELEGRAM_CHAT_ID` | empty | Telegram message 수신 chat ID |
| `DISCORD_WEBHOOK_URL` | empty | Discord channel webhook URL |
| `JOB_DETAIL_CACHE_TTL_HOURS` | `12` | 공고 상세 캐시 TTL |
| `JOB_DETAIL_CACHE_MAX_ENTRIES` | `500` | 로컬에 보관할 공고 상세 캐시 최대 개수 |

## Resume And Portfolio Files

지원 파일:

- `resumes/resume.md`
- `resumes/resume.pdf`
- `portfolios/portfolio.md`
- `portfolios/portfolio.pdf`
- `portfolios/portfolio.html`

지원 범위:

- markdown/text 파일은 UTF-8 텍스트로 직접 읽습니다.
- 텍스트 기반 PDF는 `pypdf`로 페이지 텍스트를 추출합니다.
- 로컬 HTML 파일과 Notion HTML export는 화면에 보이는 텍스트를 추출합니다.
- 스캔 PDF나 이미지 기반 PDF는 OCR이 필요하며 현재 내장 OCR은 없습니다.
- 웹 URL 직접 fetch, private Notion API 접근, 인증 필요한 Notion page 분석은 아직 포함하지 않습니다.

## Scheduler Runner

`zighang-digest`는 한 번 실행하고 종료되는 자동화용 runner입니다.

```bash
.venv/bin/zighang-digest
.venv/bin/zighang-digest --resume-profile-id default --limit-per-profile 5 --top-n 5
.venv/bin/zighang-digest --include-seen
.venv/bin/zighang-digest --dry-run
.venv/bin/zighang-digest --json
```

기본 출력:

```text
started_at=YYYY-MM-DDTHH:MM:SS+09:00
finished_at=YYYY-MM-DDTHH:MM:SS+09:00
duration_seconds=1.234
report_path=reports/daily/YYYY-MM-DD.md
notification_channel=markdown
notification_result=reports/daily/YYYY-MM-DD.md
```

`--dry-run`은 digest report 생성까지 확인하되 webhook/email/telegram/discord 전송은 하지 않습니다.

## Data Layout

| Path | Purpose |
| --- | --- |
| `data/cache/state.json` | 필터 프로필, 사용자 선호조건, 공고 상태, 상세 캐시, digest snapshot 저장 |
| `reports/daily/YYYY-MM-DD.md` | 일일 digest markdown |
| `resumes/` | 개인 이력서 파일 |
| `portfolios/` | 개인 포트폴리오 파일 |
| `tests/fixtures/` | unit test fixture |

민감한 이력서, 포트폴리오, 캐시, 리포트는 기본적으로 git ignore 됩니다.

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

## Documentation

- [MCP Tool Specification](docs/mcp-tools.md)
- [Recommendation Logic](docs/recommendation-logic.md)
- [Zighang API notes](docs/zighang-api.md)
- [Zighang recruitment API notes](docs/zighang-recruitment-api.md)
- [Implementation Plan](docs/implementation-plan.md)

## License

MIT License. See [LICENSE](LICENSE).

## Security And Privacy

- 개인 이력서, 포트폴리오, 캐시, 리포트는 repository에 커밋하지 마세요.
- `ZIGHANG_AUTH_TOKEN`, `ZIGHANG_COOKIE`, `EMAIL_PASSWORD`, webhook URL은 repository에 커밋하지 마세요.
- webhook/email/telegram/discord 전송 시 digest 본문에 개인 이력서 기반 추천 정보가 포함될 수 있습니다.
- 외부 scheduler나 CI를 사용할 때 secret 출력과 artifact 업로드 설정을 확인하세요.

## API Usage Notice

- 이 프로젝트는 Zighang public API 형태를 기준으로 동작하며, API 구조나 정책이 바뀌면 동작이 달라질 수 있습니다.
- 고빈도 호출, 대량 수집, 우회성 크롤링 용도가 아닙니다. 개인 digest와 추천에 필요한 범위에서 사용하세요.
- `ZIGHANG_AUTH_TOKEN` 또는 `ZIGHANG_COOKIE`는 사용자가 직접 설정한 경우에만 요청에 포함됩니다. 프로젝트가 인증 정보를 수집하거나 발급하지 않습니다.
- Zighang 서비스 약관, robots 정책, API 사용 정책은 사용자가 직접 확인하고 준수해야 합니다.

## Project Status

현재는 개인용 MCP 서버로 설계된 초기 구현입니다. Zighang public API 형태 변화, 인증 정책, SMTP provider 정책에 따라 운영 설정이 달라질 수 있습니다.
