# Zighang Recruitment API Spec

Collected from `https://zighang.com/recruitment` on 2026-05-19 KST by inspecting the live Next.js bundles and validating direct API calls.

## Base Contract

- Base URL: `https://api.zighang.com/api`
- Client: Axios-style JSON API, `GET` params serialized with repeated keys for arrays (`paramsSerializer: { indexes: null }`).
- Response envelope:

```json
{
  "timestamp": "2026-05-19T11:50:54.239939045",
  "success": true,
  "data": {},
  "code": "SUCCESS",
  "message": null
}
```

## Recruitment List

`GET /recruitments/v3`

Query params:

| Param | Type | Notes |
| --- | --- | --- |
| `page` | number | 0-based page index. |
| `size` | number | Page size. Site uses `20` for listing. |
| `keyword` | string | Search keyword. |
| `depthOnes` | string[] | Top-level job category names. Repeat key for multiple values. |
| `depthTwos` | string[] | Second-level job category names. Repeat key for multiple values. |
| `careerMin` | number | Minimum selected career year. `0` means new grad. |
| `careerMax` | number | Maximum selected career year. Site slider max is `10`; internal open-ended sentinel is `100`. |
| `includeCareerOpen` | boolean | "경력 무관 포함" toggle. Default UI state is `true`. |
| `employeeTypes` | string[] | Employment type filters. |
| `regions` | string[] | Region filters. |
| `educations` | string[] | Education filters. |
| `companyTypes` | string[] | Company scale/type filters. |
| `deadlineTypes` | string[] | Deadline type filters. |
| `affiliates` | string[] | Source/platform filters. |
| `startDate` | string | Local datetime string, e.g. `2026-05-12T00:00:00`. |
| `endDate` | string | Local datetime string. |
| `tag` | string | `NEKARA_KUBE` for "네카라쿠배당토직야몰두센" toggle. |
| `sortCondition` | string | `ZIGHANG_SCORE`, `LATEST`, `VIEWS`, `DEADLINE`. |
| `orderCondition` | string | Site uses `ASC` when `sortCondition=DEADLINE`, otherwise `DESC`. |

Response `data` is paginated:

```json
{
  "content": [
    {
      "id": "uuid",
      "affiliate": "고용24",
      "company": { "id": "uuid", "name": "회사명", "image": null },
      "title": "공고명",
      "createdAt": "2026-05-19T10:48:38.945881",
      "endDate": "2026-06-10T23:59:59",
      "deadlineType": "마감일",
      "careerMin": 0,
      "careerMax": 100,
      "regions": ["부산"],
      "employeeTypes": ["계약직"],
      "educations": ["무관"],
      "depthOnes": ["서비스"],
      "depthTwos": ["환경미화원"],
      "depthThrees": [],
      "views": 0,
      "highlightedTitle": null,
      "highlightedCompanyName": null,
      "bookmarked": false,
      "tags": [],
      "keywords": ["분리수거"],
      "badges": []
    }
  ],
  "page": 0,
  "size": 20,
  "totalElements": 104691,
  "totalPages": 5235,
  "last": false
}
```

## Related Recruitment Endpoints

- `GET /recruitments/pinned`: same filter params as `/recruitments/v3`, without pagination/sort params in the site call.
- `GET /open-recruitments`: used by the "2026 공채" toggle. Accepts the same list filters, plus paging/sort.
- `GET /recruitments/{id}`: detail.
- `GET /recruitments/client/{id}`: client-side detail/bookmark state.
- `POST /recruitments/views/{id}`: increment view count, skipped for bots/headless UAs by the site.
- `POST /recruitments/by-ids` body: `{ "ids": ["uuid"] }`.
- `GET /recruitments/job-categories`: dynamic job category metadata.

## Static Filter Values

### Sort

- `ZIGHANG_SCORE`: 추천순
- `LATEST`: 최신순
- `VIEWS`: 조회순
- `DEADLINE`: 마감임박순

### Date Range UI

The UI maps date ranges to `startDate`.

- `today`: 오늘
- `7days`: 7일
- `30days`: 30일
- `all`: 기간 전체, no date params

### Employment Types

- `체험형인턴`
- `전환형인턴`
- `정규직`
- `계약직`
- `일용직`
- `프리랜서`
- `병역특례`

### Regions

- `서울`
- `경기`
- `인천`
- `부산`
- `대구`
- `광주`
- `대전`
- `울산`
- `세종`
- `강원`
- `경남`
- `경북`
- `전남`
- `전북`
- `충남`
- `충북`
- `제주`
- `해외`

Note: another shared constant includes `기타`, but the recruitment filter modal options omit it.

### Educations

- `무관`
- `고졸`
- `전문대졸`
- `학사`
- `석사`
- `박사`

### Company Types

- `대기업`
- `유니콘`
- `스타트업`
- `중견기업`
- `중소기업`
- `공공기관`
- `외국계`

### Deadline Types

- `마감일`
- `상시채용`
- `채용시마감`

### Affiliates

Full grouped source filter in the modal:

- 민간 플랫폼: `V1`, `원티드`, `로켓펀치`, `그룹바이`, `랠릿`
- 협회: `아이원잡`, `금융투자협회`, `여신금융협회`, `한국관세사회`, `한국공인회계사회`, `한국보험계리사회`, `한국상담학회`
- 공공기관: `고용24`, `중소벤처기업진흥공단`, `잡알리오`, `나라일터`, `농촌일자리플러스`, `도농인력중개플랫폼`, `클린아이`, `아트모아`, `복지넷`, `병역일터`

Some carousel/simple filter surfaces expose only:

- `원티드`
- `그룹바이`
- `랠릿`
- `로켓펀치`
- `잡알리오`
- `고용24`
- `나라일터`
- `병역일터`

### Tags

- `NEKARA_KUBE`: "네카라쿠배당토직야몰두센" toggle.

## Job Categories

`GET /recruitments/job-categories` returns `name`, `displayName`, and `depthTwos`.

| `depthOnes` value | Display | `depthTwos` values |
| --- | --- | --- |
| `IT_개발` | IT·개발 | `서버_백엔드`, `프론트엔드`, `웹풀스택`, `안드로이드`, `iOS`, `크로스플랫폼`, `DBA`, `DevOps_SRE`, `시스템_네트워크`, `시스템소프트웨어`, `소프트웨어엔지니어`, `정보보호_보안`, `임베디드소프트웨어`, `로봇SW`, `QA_테스트`, `사물인터넷_IoT`, `응용프로그램`, `블록체인`, `개발PM`, `웹퍼블리싱`, `VR_AR_3D`, `ERP_SAP`, `그래픽스`, `하드웨어엔지니어`, `기타IT_개발` |
| `AI_데이터` | AI·데이터 | `데이터분석가`, `데이터사이언티스트`, `데이터엔지니어`, `머신러닝엔지니어`, `멀티모달엔지니어`, `생성형AI`, `영상_음성AI`, `자율주행`, `컴퓨터비전`, `AI비즈니스`, `AI서비스기획`, `AI리서치`, `NLP`, `LLM`, `MLOps`, `RAG`, `기타AI_데이터` |
| `게임` | 게임 | `게임기획_PM`, `게임운영`, `게임QA`, `게임개발_클라이언트`, `게임개발_서버`, `게임개발_모바일`, `테크니컬아티스트`, `게임아트`, `게임3D모델링`, `게임애니메이션`, `게임이펙트_FX`, `게임인터페이스`, `게임연출_영상`, `게임사운드`, `기타게임` |
| `디자인` | 디자인 | `웹디자인`, `UXUI_프로덕트`, `디자인리서치`, `그래픽_시각`, `일러스트레이터`, `브랜딩_BI_BX`, `공간_실내_VMD`, `산업_제품`, `패키지`, `광고_콘텐츠`, `영상_모션`, `3D_VFX`, `출판_편집`, `건축_공공_조경디자인`, `패션_텍스타일`, `기타디자인` |
| `기획_전략_경영` | 기획·전략 | `PM_PO`, `서비스_상품기획`, `사업_전략기획`, `컨설팅`, `기술기획`, `사업개발_분석`, `프로젝트매니저`, `운영관리_OM`, `경영지원`, `기타기획_전략_경영` |
| `마케팅_광고_홍보` | 마케팅·광고 | `마케팅기획_전략`, `퍼포먼스마케팅`, `콘텐츠마케팅`, `SNS마케팅`, `브랜드마케팅`, `CRM마케팅`, `글로벌마케팅`, `광고기획_AE`, `홍보_PR`, `전시_행사마케팅`, `기타마케팅` |
| `상품기획_MD` | 상품기획·MD | `상품기획`, `온라인MD`, `식품MD`, `패션MD`, `뷰티MD`, `영업MD`, `리테일MD`, `기타상품기획_MD` |
| `영업` | 영업 | `B2C영업`, `B2B영업`, `일반영업`, `영업관리_지원`, `기술_IT영업`, `금융_보험영업`, `해외영업`, `제약_의료영업`, `기타영업` |
| `무역_물류_유통` | 무역·물류 | `해외_상사영업`, `수출입관리_사무`, `관세사`, `무역금융`, `포워딩`, `구매_조달`, `물류_SCM`, `입출고_포장`, `자재_재고관리`, `운송`, `유통관리`, `설비_시설관리`, `기타무역_물류_유통` |
| `운송_배송` | 운송·배송 | `배송_배달`, `승객운송`, `물류운송`, `전문운전`, `배차관리`, `기타운전_운송` |
| `법률_법무_컴플라이언스` | 법률·법무 | `변호사`, `변리사`, `법무`, `컴플라이언스`, `내부감사`, `ESG_윤리`, `특허_IP`, `기타법률` |
| `인사_노무_HRD_총무` | HR·총무 | `인사기획`, `평가_보상`, `HRD_조직문화`, `리크루터_헤드헌터`, `노무관리`, `총무_비서`, `기타HR_총무` |
| `회계_세무_재무` | 회계·세무·재무 | `재무`, `회계`, `세무`, `IR_공시`, `경리_회계보조`, `기타회계_재무_세무` |
| `증권_운용` | 증권·운용 | `운용_트레이딩`, `리스크_준법_심사`, `VC_PE`, `증권IB`, `부동산_인프라금융`, `PB_WM`, `경영지원_관리`, `금융상품개발_영업`, `기타증권_운용` |
| `은행_보험_카드_캐피탈` | 은행·카드·보험 | `은행`, `카드사`, `캐피탈`, `보험설계`, `계리`, `손해사정`, `언더라이팅_심사`, `청구_보상`, `보험상품개발`, `기타은행_보험` |
| `엔지니어링_연구_RND` | 엔지니어링·R&D | `반도체_디스플레이`, `전기_전자_제어`, `통신기술_네트워크구축`, `기계`, `기계설계_CAD`, `자동차`, `조선_항공_우주`, `금속_철강`, `화학`, `화장품`, `바이오_제약`, `식품`, `에너지`, `환경`, `기타엔지니어링_RND` |
| `건설_건축` | 건설·건축 | `건축설계_시공`, `토목_측량_조경_환경`, `기계_전기_소방_설비`, `설계_감리_시공_공무`, `안전_품질_재료`, `사무_관리_전산`, `건설특수_일용직`, `기타건설_건축` |
| `생산_기능` | 생산·기능직 | `생산`, `공무`, `설비`, `환경안전`, `물류`, `품질`, `건설_공사_프로젝트`, `설계_CAD_CAM`, `시설관리`, `기타생산_기능직` |
| `의료_보건` | 의료·보건 | `의사`, `한의사`, `수의사`, `약사_약무보조`, `간호사`, `간호조무사`, `치위생사`, `응급구조사`, `물리치료_작업치료`, `영상의학_임상병리_검사`, `영양사_임상영양사`, `의료미용_에스테틱`, `병원행정_접수_수납`, `요양보호사`, `조리원`, `안경_검안사`, `기타의료_보건` |
| `공공_복지` | 공공·복지 | `행정_사무_운영`, `기술_전산_시설`, `복지_사회서비스`, `교육_연구`, `공공안전`, `상담_심리`, `종교`, `아동_청소년복지`, `노인_여성복지`, `자원봉사`, `기타공공_복지` |
| `교육` | 교육 | `유치원_보육교사`, `기간제_사립교사`, `방과후_시간교사`, `대학교수_강사`, `교직원_조교`, `입시학원강사`, `국어_외국어강사`, `기술_전문강사`, `학습지_방문교사`, `학원상담_운영`, `교재개발_교수설계`, `기타교육` |
| `미디어_엔터_방송` | 미디어·엔터 | `PD_감독`, `콘텐츠기획_에디터`, `방송작가`, `촬영감독_카메라`, `영상편집`, `CG_모션그래픽`, `사운드디자이너`, `기자_리포터`, `아나운서_쇼호스트`, `성우_나래이터`, `크리에이터_인플루언서`, `모델_연기자`, `사진작가`, `방송기술_중계`, `송출_편성`, `아티스트매니지먼트`, `배급_제작사`, `음원_음반`, `웹툰_웹소설`, `출판`, `통_번역`, `전시기획_큐레이터`, `기타미디어_엔터` |
| `고객상담_TM` | 고객상담·TM | `인바운드`, `아웃바운드`, `CS`, `CX매니저`, `기타고객상담` |
| `서비스` | 서비스 | `설치_수리기사`, `주차_주유`, `가사도우미`, `애견미용_훈련`, `경호_경비`, `호텔서비스`, `관광서비스`, `항공서비스`, `매장관리`, `안내_리셉션`, `헤어디자이너`, `메이크업_네일`, `피부관리`, `마사지_체형관리`, `웨딩플래너`, `환경미화원`, `기타서비스` |
| `식음료` | 식음료 | `식품가공_개발`, `주방조리`, `제과_제빵`, `음료_주류`, `매장운영`, `서비스_홀스태프`, `식음컨설팅_지원`, `기타식음료` |

## Validated Calls

These calls returned `success: true` on 2026-05-19:

```bash
curl --get 'https://api.zighang.com/api/recruitments/v3' \
  --data-urlencode 'page=0' \
  --data-urlencode 'size=2' \
  --data-urlencode 'sortCondition=LATEST' \
  --data-urlencode 'orderCondition=DESC'
```

```bash
curl --get 'https://api.zighang.com/api/recruitments/v3' \
  --data-urlencode 'page=0' \
  --data-urlencode 'size=1' \
  --data-urlencode 'depthOnes=IT_개발' \
  --data-urlencode 'depthTwos=서버_백엔드' \
  --data-urlencode 'sortCondition=LATEST' \
  --data-urlencode 'orderCondition=DESC'
```

```bash
curl --get 'https://api.zighang.com/api/recruitments/v3' \
  --data-urlencode 'page=0' \
  --data-urlencode 'size=1' \
  --data-urlencode 'careerMin=4' \
  --data-urlencode 'careerMax=4' \
  --data-urlencode 'includeCareerOpen=false' \
  --data-urlencode 'sortCondition=LATEST' \
  --data-urlencode 'orderCondition=DESC'
```

```bash
curl --get 'https://api.zighang.com/api/recruitments/v3' \
  --data-urlencode 'page=0' \
  --data-urlencode 'size=1' \
  --data-urlencode 'regions=부산' \
  --data-urlencode 'sortCondition=LATEST' \
  --data-urlencode 'orderCondition=DESC'
```

```bash
curl --get 'https://api.zighang.com/api/open-recruitments' \
  --data-urlencode 'page=0' \
  --data-urlencode 'size=1' \
  --data-urlencode 'includeCareerOpen=true' \
  --data-urlencode 'sortCondition=LATEST' \
  --data-urlencode 'orderCondition=DESC'
```
