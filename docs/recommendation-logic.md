# Recommendation Logic

The first implementation uses deterministic local scoring. It does not send resume or portfolio content to any external model.

## Inputs

- Zighang job summary/detail fields:
  - title
  - company
  - keywords
  - job categories
  - career range
  - regions
  - end date
- Resume profile:
  - extracted skills
  - extracted project lines
  - extracted keywords
- Local job status:
  - viewed/bookmarked/interested/applied/rejected/ignored
- Cached details for locally tracked jobs, when available

## Scoring

Base score: `40`.

Positive signals:

- Skill overlap with job title, job keywords, or job category: up to `35`.
- Resume keyword overlap: up to `15`.
- Project line overlap: up to `10`.
- Bookmarked/interested status: `+10`.
- Similarity to locally tracked positive jobs: up to `+20`.
- Deadline within 7 days: `+6`.
- Deadline within 3 days: `+12`.

Negative signals:

- Viewed/applied status: `-10`.
- Ignored/rejected status: `-35`.
- Similarity to locally tracked ignored/rejected jobs: down to `-20`.
- Already closed deadline: `-20`.

Scores are clamped to `0..100`.

## Explanation Rules

Every recommendation includes:

- concrete matched skill/keyword evidence when available
- deadline context when relevant
- mismatch warnings
- local feedback reasons and warnings when prior tracked jobs are similar
- resume highlight suggestions
- pre-apply improvement tips

The output must avoid generic statements such as "적합합니다" without evidence.

## Duplicate Removal

The default duplicate key is:

```text
lower(company_name), lower(title), affiliate
```

This is conservative enough for a first pass and avoids collapsing different source postings with similar titles unless they share the same source label.
