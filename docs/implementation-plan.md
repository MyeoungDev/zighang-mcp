# Implementation Plan

## Phase 1: API And Design

- Inspect current repository structure.
- Confirm public Zighang API contract.
- Write `docs/zighang-api.md`.
- Write `docs/mcp-tools.md`.
- Write `docs/recommendation-logic.md`.

## Phase 2: Minimal MCP Server

- Implement Zighang client with public API support.
- Implement models for list/detail parsing.
- Implement MCP tool functions.
- Store personal state locally.

## Phase 3: Recommendation And Digest

- Parse local resume/portfolio text.
- Extract skills and project lines locally.
- Score jobs deterministically.
- Generate markdown daily digest.

## Phase 4: Tests And Docs

- Add fixture-based unit tests.
- Keep live API smoke tests separate.
- Add README and `.env.example`.

## Phase 5: Later Improvements

- Add real PDF extraction behind an explicit dependency.
- Add webhook/email implementations.
- Add optional authenticated bookmark sync when the user supplies cookies/tokens.
- Add richer NLP scoring if a local or user-approved model is configured.

