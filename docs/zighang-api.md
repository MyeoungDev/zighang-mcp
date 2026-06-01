# Zighang API Specification

Collected from the public `https://zighang.com/recruitment` web app and direct public API calls on 2026-05-19 KST.

## Scope And Safety

- Uses only public web/app API requests observed from the Zighang site.
- Auth-required APIs are documented but not used unless the user provides `ZIGHANG_AUTH_TOKEN` or `ZIGHANG_COOKIE`.
- No scraping-defense bypass, token harvesting, or high-volume crawling is implemented.
- Client defaults include `REQUEST_DELAY_MS` to keep request rate conservative.

## Base Contract

- Base URL: `https://api.zighang.com/api`
- JSON envelope:

```json
{
  "timestamp": "2026-05-19T11:54:36.059149429",
  "success": true,
  "data": {},
  "code": "SUCCESS",
  "message": null
}
```

The web client sends arrays as repeated query keys, equivalent to Axios `paramsSerializer: { indexes: null }`.

## 공고 목록 API

`GET /recruitments/v3`

Public. Used for the main recruitment list and keyword search.

| Param | Type | Description |
| --- | --- | --- |
| `page` | number | 0-based page index. |
| `size` | number | Page size. Site uses `20`. |
| `keyword` | string | Keyword search. Highlight fields may be returned. |
| `depthOnes` | string[] | Top-level job categories. |
| `depthTwos` | string[] | Job subcategories. |
| `careerMin` | number | Minimum career year. `0` means 신입. |
| `careerMax` | number | Maximum career year. Open-ended result values can be `100`. |
| `includeCareerOpen` | boolean | Include 경력무관 postings. UI default is `true`. |
| `employeeTypes` | string[] | Employment type filters. |
| `regions` | string[] | Region filters. |
| `educations` | string[] | Education filters. |
| `companyTypes` | string[] | Company type filters. |
| `deadlineTypes` | string[] | Deadline type filters. |
| `affiliates` | string[] | Source/platform filters. |
| `startDate` | string | Local datetime string. Used by period UI. |
| `endDate` | string | Local datetime string. |
| `tag` | string | `NEKARA_KUBE` for the 네카라쿠배... toggle. |
| `sortCondition` | string | `ZIGHANG_SCORE`, `LATEST`, `VIEWS`, `DEADLINE`. |
| `orderCondition` | string | `ASC` for `DEADLINE`, otherwise `DESC`. |

Response `data`:

```json
{
  "content": [
    {
      "id": "5b6802b8-12b3-44a1-8ff0-ab5cceb9fd14",
      "affiliate": "고용24",
      "company": {"id": "31996768-1c90-4071-b65a-cf0353024ef8", "name": "에이티이정보주식회사", "image": null},
      "title": "Java 프론트엔트, 백엔드 개발 경력자 채용",
      "createdAt": "2026-05-19T10:44:16.070406",
      "endDate": "2026-05-29T23:59:59",
      "deadlineType": "마감일",
      "careerMin": 4,
      "careerMax": 100,
      "regions": ["서울"],
      "employeeTypes": ["정규직"],
      "educations": ["학사"],
      "depthOnes": ["IT_개발"],
      "depthTwos": ["웹풀스택", "서버_백엔드"],
      "depthThrees": [],
      "views": 0,
      "highlightedTitle": null,
      "highlightedCompanyName": null,
      "bookmarked": false,
      "tags": [],
      "keywords": ["선유도역", "전자정부프레임워크", "JAVA개발"],
      "badges": []
    }
  ],
  "page": 0,
  "size": 1,
  "totalElements": 986,
  "totalPages": 986,
  "last": false
}
```

## 공고 상세 API

`GET /recruitments/{id}`

Public. Returns the list fields plus rich detail fields.

Important fields:

- `summary`: TipTap JSON doc with normalized job text.
- `content`: TipTap JSON doc, sometimes only image content.
- `redirectUrl`: original apply/source URL.
- `status`: e.g. `ACTIVE`.
- `company.hasDetailInfo`
- `pinned`
- `app.id`

The implementation converts TipTap JSON into plain text for MCP output.

## 키워드 검색 API

Keyword search uses the list API:

```bash
GET /recruitments/v3?keyword=Java&page=0&size=1&sortCondition=LATEST&orderCondition=DESC
```

Observed keyword results include `highlightedTitle` and `highlightedCompanyName`.

## 필터 목록/메타데이터 API

`GET /recruitments/job-categories`

Public. Returns dynamic job category metadata:

```json
[
  {
    "name": "IT_개발",
    "displayName": "IT·개발",
    "depthTwos": ["서버_백엔드", "프론트엔드"]
  }
]
```

Static filter options from the web bundle:

- Employment types: `체험형인턴`, `전환형인턴`, `정규직`, `계약직`, `일용직`, `프리랜서`, `병역특례`
- Regions: `서울`, `경기`, `인천`, `부산`, `대구`, `광주`, `대전`, `울산`, `세종`, `강원`, `경남`, `경북`, `전남`, `전북`, `충남`, `충북`, `제주`, `해외`
- Education: `무관`, `고졸`, `전문대졸`, `학사`, `석사`, `박사`
- Company types: `대기업`, `유니콘`, `스타트업`, `중견기업`, `중소기업`, `공공기관`, `외국계`
- Deadline types: `마감일`, `상시채용`, `채용시마감`
- Affiliates:
  - 민간 플랫폼: `V1`, `원티드`, `로켓펀치`, `그룹바이`, `랠릿`
  - 협회: `아이원잡`, `금융투자협회`, `여신금융협회`, `한국관세사회`, `한국공인회계사회`, `한국보험계리사회`, `한국상담학회`
  - 공공기관: `고용24`, `중소벤처기업진흥공단`, `잡알리오`, `나라일터`, `농촌일자리플러스`, `도농인력중개플랫폼`, `클린아이`, `아트모아`, `복지넷`, `병역일터`

Full job category values are fetched at runtime with `list_filter_options`.

## 기타 공고 API

- `GET /recruitments/pinned`: public pinned jobs, accepts the same filter params.
- `GET /open-recruitments`: public "2026 공채" list, accepts the same filter params.
- `GET /recruitments/client/{id}`: client-side state, public enough to return bookmark state.
- `POST /recruitments/views/{id}`: view count; web client skips known bots/headless user agents.
- `POST /recruitments/by-ids`: accepts `{ "ids": ["uuid"] }`.

## 북마크/저장 가능 여부

Observed web bundle endpoints:

- `GET /bookmarks`
- `POST /bookmarks` with body `{ "recruitmentId": "<id>" }`
- `DELETE /bookmarks/{id}`

Unauthenticated request returns HTTP 200 with envelope error:

```json
{
  "success": false,
  "data": null,
  "code": "GLOBAL-403",
  "message": "인증되지 않은 사용자입니다."
}
```

The MCP server therefore stores personal statuses locally by default. It can pass user-provided auth token/cookie to Zighang APIs, but does not attempt authentication itself.

## Error Response

Invalid detail ID returned HTTP 200 with:

```json
{
  "success": false,
  "data": null,
  "code": "GLOBAL-303",
  "message": "파라미터(id)의 값이 올바르지 않습니다."
}
```

The client treats `success: false` as an API error regardless of HTTP status.

## Rate Limit / Request Limit Observations

No explicit `429` or rate-limit headers were observed during low-volume validation calls. Response headers include no-cache and standard security headers. The local client still applies `REQUEST_DELAY_MS` between calls to avoid aggressive request behavior.

