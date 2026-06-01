# MCP Tool Specification

## Tool Selection Guide

| User intent | Preferred tool |
| --- | --- |
| "나에게 맞는 공고", "내 이력 기준 추천", "이를 토대로 맞는 공고" | `recommend_jobs` |
| "내 선호도 기준 최신 공고" | `search_latest_jobs_for_me` |
| "직행 최신 IT 공고" | `search_latest_it_jobs` |
| "오늘 올라온 IT 공고" | `search_today_it_jobs` |
| Specific posted date search | `search_jobs_posted_on` |
| Explicit keyword/filter search | `search_jobs` |
| Natural-language preference update | `update_user_preferences_from_text` |

`search_jobs` is the low-level escape hatch. Agents should prefer the intent-specific tools above before making multiple ad-hoc keyword searches. `list_saved_jobs` is a deprecated compatibility alias for MCP-local tracking; use `list_tracked_jobs` for new calls.

## Public Zighang Tools

### `search_jobs`

Low-level explicit-filter search for public Zighang job postings. Prefer intent-specific tools for personalized, latest IT, or posted-date requests.

Inputs:

- `keyword`
- `job_categories`
- `job_subcategories`
- `regions`
- `career_min`
- `career_max`
- `include_career_open`
- `employment_types`
- `education_levels`
- `company_types`
- `deadline_types`
- `affiliates`
- `sort`
- `page`
- `size`
- `start_date`
- `end_date`
- `open_recruitments`
- `nekara_kube`
- `exclude_keywords`

Output includes job ID, company, title, job categories, regions, career condition, deadline, original Zighang URL, source affiliate, keywords, and pagination.

### `search_jobs_posted_on`

Searches public Zighang job postings posted on one Asia/Seoul calendar date. This is the preferred tool for prompts such as "직행에 오늘 올라온 공고 탐색".

Inputs:

- `posted_date`: `YYYY-MM-DD`. Defaults to today's date in `Asia/Seoul`.
- `keyword`
- `job_categories`
- `job_subcategories`
- `regions`
- `career_min`
- `career_max`
- `include_career_open`
- `employment_types`
- `education_levels`
- `company_types`
- `deadline_types`
- `affiliates`
- `page`
- `size`
- `open_recruitments`
- `nekara_kube`
- `exclude_keywords`

Internally this calls `search_jobs` with `sort=latest`, `start_date=<date>T00:00:00`, and `end_date=<date>T23:59:59`.

### `search_pinned_jobs`

Searches the pinned recruitment endpoint used by the Zighang recruitment page. The site calls this alongside the normal list when the "2026 공채" toggle is off.

Inputs:

- `keyword`
- `job_categories`
- `job_subcategories`
- `regions`
- `career_min`
- `career_max`
- `employment_types`
- `education_levels`
- `company_types`
- `deadline_types`
- `affiliates`
- `start_date`
- `end_date`
- `nekara_kube`
- `exclude_keywords`

This maps to `GET /recruitments/pinned`. The live site does not send pagination or sort parameters for pinned jobs.

### Intent-Specific Search Tools

- `search_latest_it_jobs(size, include_pinned, exclude_internships)`: latest `IT_개발` postings.
- `search_today_it_jobs(size, include_pinned, exclude_internships)`: today's `IT_개발` postings in `Asia/Seoul`.
- `search_latest_jobs_for_me(size, include_pinned)`: latest postings using stored user preferences.

These tools use local `user_preferences` defaults, including internship exclusion and excluded keywords/company names.

### `get_job_detail`

Fetches one job detail by Zighang recruitment ID.

Output includes normalized detail text, source/apply URL, status, company info, job categories, requirements summary, conditions, deadline, and original Zighang URL.

### `list_filter_options`

Returns dynamic job categories from Zighang plus static filter options observed from the web bundle.

## Recommendation Tools

### `recommend_jobs`

Ranks jobs for a resume/profile, optional filter, and stored user preferences. This is the preferred tool for "나에게 맞는 공고" and resume/profile-based recommendation prompts.

Inputs:

- `filter_profile_id`
- `inline_filter`
- `resume_profile_id`
- `inline_resume`
- `limit`
- `include_evidence`: defaults to `true`. When enabled, recommendations can use job detail text for evidence snippets.
- `max_detail_fetch`: optional cap for detail fetches. Remaining jobs are scored from summary fields.

Output:

- recommendation score
- `score_breakdown` with base, resume, preference, deadline, saved-status, and penalty components
- `matched_signals` from job categories, skills, keywords, regions, employment types, and deadline signals
- `risk_flags` for career, preference mismatch, disliked terms, excluded companies, saved status, or deadline issues
- `evidence_snippets` from title, keywords, categories, and detail text when fetched
- `detail_fetched` showing whether the recommendation used detail text or summary-only data
- reasons
- preference reasons and warnings
- mismatch risks
- resume highlights
- pre-apply tips
- detailed job summary

### `explain_job_match`

Explains one job against a resume/profile.

Inputs:

- `job_id`
- `resume_profile_id`
- `inline_resume`

Output:

- score
- strengths
- gaps
- resume/portfolio emphasis points
- application strategy

## Filter Profile Tools

- `save_filter_profile(profile_id, name, filters, notifications_enabled)`
- `list_filter_profiles()`
- `update_filter_profile(profile_id, name, filters, notifications_enabled)`
- `delete_filter_profile(profile_id)`

Profiles are stored locally under `data/cache/state.json`.

## Digest And Status Tools

### `daily_job_digest`

Generates `reports/daily/YYYY-MM-DD.md` from enabled filter profiles and sends the same markdown through the configured notification channel.

At least one enabled filter profile is required. If none exists, the tool returns `setup_required=true`, writes a setup guidance digest, and skips recommendation lookup.

Inputs:

- `resume_profile_id`
- `limit_per_profile`
- `top_n`
- `exclude_seen`
- `send_notification`
- `only_new`
- `include_tracked`
- `include_pinned`

Output:

- `report_path`
- `markdown`
- `profiles`
- `new_job_count`
- `deadline_soon_count`
- `excluded_existing_count`
- `digest_history`
- `notification_channel`
- `notification_result`
- `setup_required`
- `setup_message` when setup is required

Notification channels:

- `markdown`: saves the report and returns the report path.
- `console`: prints the digest to stdout.
- `webhook`: POSTs `{"text": "<markdown>"}` to `WEBHOOK_URL`.
- `email`: sends the markdown as a plain text SMTP email.
- `telegram`: sends the markdown through Telegram Bot API `sendMessage`.
- `discord`: sends the markdown to a Discord webhook as `content`.

`NOTIFICATION_CHANNEL` accepts one channel or a comma-separated list such as `markdown,email,telegram`. Fanout runs in order and stops on the first delivery error.

Schedulers should use the `zighang-digest` console script for direct one-shot digest runs. MCP clients and agents can call `daily_job_digest` directly when interactive tool orchestration is preferred.

### `track_job_status`

Stores local per-job state. This is MCP-local tracking, not a Zighang account bookmark.

Allowed statuses:

- `new`
- `viewed`
- `bookmarked`
- `interested`
- `applied`
- `rejected`
- `ignored`

### `list_tracked_jobs`

Lists locally stored job states, optionally filtered by status.

Compatibility aliases:

- `mark_job_status`: alias for `track_job_status`
- `list_saved_jobs`: alias for `list_tracked_jobs`

## User Preference Tools

- `get_user_preferences()`
- `update_user_preferences(preferences)`
- `update_user_preferences_from_text(text, merge=True)`
- `clear_user_preferences()`

Preferences are stored locally under `data/cache/state.json` and are used by intent-specific search, recommendation scoring, and internship/exclusion defaults. `update_user_preferences_from_text` is rules-based and handles common Korean/English phrases such as backend, data platform, DevOps/SRE, regions, employment types, skills, and exclusion phrases like "인턴 제외" or "프론트엔드 제외".

Supported v1 fields:

- `preferred_job_categories`
- `preferred_job_subcategories`
- `preferred_regions`
- `preferred_employment_types`
- `excluded_keywords`
- `excluded_company_names`
- `preferred_keywords`
- `preferred_skills`
- `disliked_keywords`
- `default_exclude_internships`

## Resume And Portfolio Tools

- `load_resume_profile`
- `update_resume_profile`
- `analyze_resume_profile`
- `extract_skills_from_resume`
- `extract_projects_from_portfolio`

Default local files:

- `resumes/resume.md`
- `resumes/resume.pdf`
- `portfolios/portfolio.md`
- `portfolios/portfolio.pdf`
- `portfolios/portfolio.html`

The parser is local-only. Markdown/text files are parsed directly. Text-based PDFs are parsed with `pypdf`; scanned or image-based PDFs require OCR and currently raise a clear OCR-needed error. Local `.html`/`.htm` files, including Notion HTML exports, are parsed by extracting visible text and ignoring script/style/noscript content. Live URL fetching and Notion API access are intentionally out of scope.
