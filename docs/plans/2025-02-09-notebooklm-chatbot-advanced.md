# NotebookLM Chatbot - Advanced Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the full NotebookLM chatbot with Azure AD authentication, ACL, nlm-proxy integration, and multi-channel support.

**Architecture:** Extends basic bot with Microsoft Graph API for user groups, YAML-based ACL, nlm-proxy OpenAI client, and Telegram channel support.

**Tech Stack:** Python 3.11+, botbuilder-python, aiohttp, openai SDK, msal, msgraph-sdk, redis, pydantic-settings

**Prerequisites:** Complete basic plan first (`2025-02-09-notebooklm-chatbot-basic.md`)

---

## Phase 2: Azure AD Authentication

### Task 2.1: Microsoft Graph Client
- **Files:** `src/knowledge_finder_bot/auth/graph_client.py`
- **Description:** Implement Graph API client for user group lookup using app-only authentication
- **Details:** TODO

### Task 2.2: User Info Extraction
- **Files:** `src/knowledge_finder_bot/auth/azure_ad.py`
- **Description:** Extract Azure AD Object ID from Teams activity, cache user info
- **Details:** TODO

### Task 2.3: Authentication Tests
- **Files:** `tests/test_auth.py`
- **Description:** Unit tests for Graph client and user info extraction
- **Details:** TODO

---

## Phase 3: ACL Implementation

### Task 3.1: ACL Configuration Schema
- **Files:** `config/acl.yaml`, `src/knowledge_finder_bot/acl/models.py`
- **Description:** Define YAML schema for group-to-notebook mapping
- **Details:** TODO

### Task 3.2: ACL Service
- **Files:** `src/knowledge_finder_bot/acl/service.py`
- **Description:** Service to resolve user groups to allowed notebooks
- **Details:** TODO

### Task 3.3: Redis Caching
- **Files:** `src/knowledge_finder_bot/acl/cache.py`
- **Description:** Redis integration for ACL caching
- **Details:** TODO

### Task 3.4: ACL Tests
- **Files:** `tests/test_acl.py`
- **Description:** Unit tests for ACL service and caching
- **Details:** TODO

---

## Phase 4: nlm-proxy Integration

### Task 4.1: nlm-proxy Client
- **Files:** `src/knowledge_finder_bot/nlm/client.py`
- **Description:** OpenAI SDK wrapper for nlm-proxy with streaming support
- **Details:** TODO

### Task 4.2: Session Mapping
- **Files:** `src/knowledge_finder_bot/nlm/session.py`
- **Description:** Map Teams/Telegram conversation IDs to nlm-proxy chat sessions
- **Details:** TODO

### Task 4.3: Response Formatting
- **Files:** `src/knowledge_finder_bot/utils/formatting.py`
- **Description:** Extract notebook name from reasoning, format with source attribution
- **Details:** TODO

### Task 4.4: Integration Tests
- **Files:** `tests/test_nlm_client.py`
- **Description:** Integration tests with mocked nlm-proxy
- **Details:** TODO

---

## Phase 5: Full Bot Implementation

### Task 5.1: Update Bot with Full Flow
- **Files:** `src/knowledge_finder_bot/bot/bot.py`
- **Description:** Replace echo with full auth → ACL → nlm-proxy → response flow
- **Details:** TODO

### Task 5.2: Teams Adaptive Cards
- **Files:** `src/knowledge_finder_bot/channels/teams.py`
- **Description:** Rich card formatting for Teams responses
- **Details:** TODO

### Task 5.3: Bot Commands
- **Files:** `src/knowledge_finder_bot/bot/handlers/commands.py`
- **Description:** Implement /help, /status, /clear commands
- **Details:** TODO

### Task 5.4: End-to-End Tests
- **Files:** `tests/test_e2e.py`
- **Description:** Full conversation flow tests
- **Details:** TODO

---

## Phase 6: Production Hardening

### Task 6.1: Rate Limiting
- **Files:** `src/knowledge_finder_bot/utils/rate_limiter.py`
- **Description:** Per-user rate limiting with Redis
- **Details:** TODO

### Task 6.2: Error Handling
- **Files:** `src/knowledge_finder_bot/bot/middleware/error_handler.py`
- **Description:** User-friendly error messages, retry logic
- **Details:** TODO

### Task 6.3: Structured Logging
- **Files:** `src/knowledge_finder_bot/logging.py`
- **Description:** Configure structlog with correlation IDs
- **Details:** TODO

### Task 6.4: Health Checks
- **Files:** `src/knowledge_finder_bot/main.py`
- **Description:** Add /ready endpoint, dependency health checks
- **Details:** TODO

---

## Phase 7: Telegram Channel

### Task 7.1: Telegram OAuth Flow
- **Files:** `src/knowledge_finder_bot/auth/telegram_oauth.py`
- **Description:** Link Telegram accounts to Azure AD
- **Details:** TODO

### Task 7.2: Telegram Formatter
- **Files:** `src/knowledge_finder_bot/channels/telegram.py`
- **Description:** Markdown V2 formatting for Telegram
- **Details:** TODO

### Task 7.3: Channel Integration Tests
- **Files:** `tests/test_telegram.py`
- **Description:** Telegram-specific tests
- **Details:** TODO

---

## Phase 8: Deployment

### Task 8.1: Dockerfile
- **Files:** `deploy/Dockerfile`
- **Description:** Multi-stage build for production image
- **Details:** TODO

### Task 8.2: Docker Compose
- **Files:** `deploy/docker-compose.yml`
- **Description:** Local dev with Redis
- **Details:** TODO

### Task 8.3: Kubernetes Manifests
- **Files:** `deploy/k8s/*.yaml`
- **Description:** Deployment, Service, ConfigMap, Secrets
- **Details:** TODO

### Task 8.4: Documentation
- **Files:** `docs/deployment.md`, `docs/configuration.md`
- **Description:** Deployment and configuration guides
- **Details:** TODO

---

## Phase 9: Monitoring

### Task 9.1: Prometheus Metrics
- **Files:** `src/knowledge_finder_bot/metrics.py`
- **Description:** Request counters, latency histograms
- **Details:** TODO

### Task 9.2: Grafana Dashboards
- **Files:** `deploy/grafana/dashboard.json`
- **Description:** Pre-built monitoring dashboard
- **Details:** TODO

---

## Notes

- Each task above is a placeholder. Add detailed steps (test first, implement, verify, commit) when ready to implement.
- Reference the design document: `docs/plans/notebooklm-chatbot-design.md`
- Use TDD approach: write failing test first, then implement
