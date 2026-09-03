# Overwatch AML Platform - Build Tasks & Improvements

This document tracks all improvement recommendations organized by priority and dependencies.

---

## 🔴 P0 - Critical (Security & Compliance)

### Security Hardening
- [ ] **TASK-001**: Replace Hardcoded JWT Secret in Development
  - **Priority**: P0
  - **Category**: Security
  - **Dependencies**: None
  - **Description**: Remove fallback default value for JWT_SECRET_KEY, require environment variable, add startup validation to fail if not set
  - **Acceptance Criteria**: 
    - Application fails to start without JWT_SECRET_KEY env var
    - No hardcoded secrets in codebase
    - Documentation updated for deployment

- [ ] **TASK-002**: Implement Proper Keycloak Integration
  - **Priority**: P0
  - **Category**: Security
  - **Dependencies**: TASK-001
  - **Description**: Complete Keycloak OIDC integration, remove hardcoded admin bypass, implement proper token validation
  - **Acceptance Criteria**:
    - All authentication flows through Keycloak
    - No hardcoded credentials or bypasses
    - Token validation includes expiry, issuer, audience checks

- [ ] **TASK-003**: SQL Injection Prevention in Graph Queries
  - **Priority**: P0
  - **Category**: Security
  - **Dependencies**: None
  - **Description**: Use parameterized queries for all graph operations, sanitize inputs, add length limits
  - **Acceptance Criteria**:
    - All database queries use parameterized statements
    - Input validation on all graph query parameters
    - Maximum length constraints on user inputs

### Audit & Compliance
- [ ] **TASK-004**: Audit Log Persistence
  - **Priority**: P0
  - **Category**: Compliance
  - **Dependencies**: None
  - **Description**: Implement database audit table, add cryptographic hashing for integrity, enable export to SIEM systems
  - **Acceptance Criteria**:
    - All user actions logged to immutable audit table
    - Cryptographic hash chain for tamper detection
    - SIEM export functionality implemented

---

## 🟠 P1 - High (Compliance & Architecture)

### Regulatory Compliance
- [ ] **TASK-005**: PII Masking Enhancement
  - **Priority**: P1
  - **Category**: Compliance
  - **Dependencies**: TASK-004
  - **Description**: Implement granular field-level permissions, dynamic masking based on roles, log all unmasking events
  - **Acceptance Criteria**:
    - Role-based field visibility
    - Dynamic masking applied at API level
    - All unmasking events audited

- [ ] **TASK-006**: STR Regulatory Compliance
  - **Priority**: P1
  - **Category**: Compliance
  - **Dependencies**: TASK-005
  - **Description**: Add mandatory field validation for Suspicious Transaction Reports, version history tracking, PDF export, filing status tracking
  - **Acceptance Criteria**:
    - All mandatory STR fields validated before submission
    - Version history for all report changes
    - PDF export with digital signature capability
    - Filing workflow with status tracking

### Architecture & Infrastructure
- [ ] **TASK-007**: Environment Variable Management
  - **Priority**: P1
  - **Category**: Architecture
  - **Dependencies**: TASK-001
  - **Description**: Create .env template files, move all API URLs to configuration, add timeout policies for external services
  - **Acceptance Criteria**:
    - .env.example with all required variables
    - No hardcoded URLs in code
    - Configurable timeouts for all external calls

- [ ] **TASK-008**: Database Connection Pool Configuration
  - **Priority**: P1
  - **Category**: Architecture
  - **Dependencies**: None
  - **Description**: Add connection pool size limits, implement health checks, configure query timeouts
  - **Acceptance Criteria**:
    - Pool size configured via environment variables
    - Health check endpoint returns DB status
    - Query timeout prevents long-running queries

- [ ] **TASK-009**: Error Handling Standardization
  - **Priority**: P1
  - **Category**: Architecture
  - **Dependencies**: None
  - **Description**: Create custom exception hierarchy, implement global error handlers, standardize error response format
  - **Acceptance Criteria**:
    - Custom exception classes for all error types
    - Global middleware catches unhandled exceptions
    - Consistent JSON error response structure

- [ ] **TASK-010**: Docker Compose Improvements
  - **Priority**: P1
  - **Category**: DevOps
  - **Dependencies**: TASK-007
  - **Description**: Use Docker secrets for sensitive data, add resource limits, configure structured logging, add comprehensive health checks
  - **Acceptance Criteria**:
    - No secrets in docker-compose.yml
    - CPU/memory limits defined per service
    - JSON structured logging enabled
    - Health checks for all services

---

## 🟡 P2 - Medium (Performance & Features)

### Performance Optimization
- [ ] **TASK-011**: Graph Query Optimization
  - **Priority**: P2
  - **Category**: Performance
  - **Dependencies**: TASK-003
  - **Description**: Implement cursor-based pagination for large graphs, add Redis caching for frequent queries, pre-compute exclusion lists
  - **Acceptance Criteria**:
    - Pagination works for graphs with 10k+ nodes
    - Cache hit ratio > 80% for repeated queries
    - Exclusion lists pre-computed nightly

- [ ] **TASK-012**: Alert Feed Performance
  - **Priority**: P2
  - **Category**: Performance
  - **Dependencies**: None
  - **Description**: Add database indexes on filter columns, implement server-side filtering, add HTTP caching headers
  - **Acceptance Criteria**:
    - Alert feed loads in < 500ms for 10k alerts
    - All filters executed server-side
    - Proper cache headers for CDN support

- [ ] **TASK-013**: Frontend Bundle Optimization
  - **Priority**: P2
  - **Category**: Performance
  - **Dependencies**: None
  - **Description**: Enable bundle analyzer, implement lazy loading for routes, tree-shake unused icons and components
  - **Acceptance Criteria**:
    - Initial bundle size < 500KB
    - Routes loaded on demand
    - Unused code eliminated

### Feature Implementation
- [ ] **TASK-014**: Screening Module Implementation
  - **Priority**: P2
  - **Category**: Features
  - **Dependencies**: None
  - **Description**: Integrate sanctions lists (OFAC, UN, EU), implement fuzzy matching algorithms, add wallet address screening
  - **Acceptance Criteria**:
    - Daily sanctions list updates
    - Fuzzy matching with configurable thresholds
    - Wallet screening against known bad actors

- [ ] **TASK-015**: Case Management Enhancements
  - **Priority**: P2
  - **Category**: Features
  - **Dependencies**: TASK-004
  - **Description**: Add assignment workflows, case notes with attachments, timeline visualization, bulk action capabilities
  - **Acceptance Criteria**:
    - Cases can be assigned/reassigned
    - Notes support file attachments
    - Visual timeline of case activity
    - Bulk status updates supported

- [ ] **TASK-016**: KPI Dashboard Real-time Updates
  - **Priority**: P2
  - **Category**: Features
  - **Dependencies**: TASK-011
  - **Description**: Implement WebSocket for real-time metrics, add historical trend charts, customizable widgets, export functionality
  - **Acceptance Criteria**:
    - Metrics update in real-time without refresh
    - Historical data visualized (30/60/90 days)
    - Users can customize dashboard layout
    - Export to CSV/PDF supported

- [ ] **TASK-017**: Workflow Engine Integration
  - **Priority**: P2
  - **Category**: Features
  - **Dependencies**: TASK-004
  - **Description**: Track workflow instances, add event listeners for state changes, implement task assignment, handle workflow failures
  - **Acceptance Criteria**:
    - All workflow instances tracked in DB
    - Events trigger appropriate actions
    - Tasks assigned to users/roles
    - Failed workflows alert operators

---

## 🟢 P3 - Low (Quality & UX)

### Code Quality
- [ ] **TASK-018**: Type Safety Improvements
  - **Priority**: P3
  - **Category**: Quality
  - **Dependencies**: None
  - **Description**: Add type hints to all functions, enable mypy strict mode, use TypedDict for complex structures
  - **Acceptance Criteria**:
    - 100% type hint coverage
    - mypy passes with strict settings
    - Complex data structures use TypedDict

- [ ] **TASK-019**: Test Coverage Gap
  - **Priority**: P3
  - **Category**: Quality
  - **Dependencies**: None
  - **Description**: Add pytest fixtures for common scenarios, implement integration tests, achieve >80% code coverage, add load testing
  - **Acceptance Criteria**:
    - Test coverage > 80%
    - Integration tests for critical paths
    - Load tests simulate production traffic

- [ ] **TASK-020**: API Documentation
  - **Priority**: P3
  - **Category**: Quality
  - **Dependencies**: TASK-009
  - **Description**: Auto-generate OpenAPI/Swagger docs, add request/response examples, document all error codes, generate TypeScript types
  - **Acceptance Criteria**:
    - Live Swagger UI available
    - All endpoints documented with examples
    - Error codes documented
    - TS types auto-generated for frontend

- [ ] **TASK-021**: CI/CD Pipeline
  - **Priority**: P3
  - **Category**: DevOps
  - **Dependencies**: TASK-019
  - **Description**: Add GitHub Actions workflow, run tests on PRs, integrate security scanning, automate deployment
  - **Acceptance Criteria**:
    - Tests run on every PR
    - Security scan (SAST/DAST) in pipeline
    - Automated deployment to staging

- [ ] **TASK-022**: Monitoring & Observability
  - **Priority**: P3
  - **Category**: DevOps
  - **Dependencies**: TASK-010
  - **Description**: Add Prometheus metrics endpoints, implement distributed tracing, create Grafana dashboards, configure alerts
  - **Acceptance Criteria**:
    - Key metrics exposed to Prometheus
    - Traces visible in Jaeger/Tempo
    - Dashboards for system health
    - Alerts for critical conditions

### User Experience
- [ ] **TASK-023**: Frontend Accessibility
  - **Priority**: P3
  - **Category**: UX
  - **Dependencies**: None
  - **Description**: Add ARIA labels to all interactive elements, ensure keyboard navigation works, manage focus properly, meet WCAG 2.1 AA
  - **Acceptance Criteria**:
    - All elements have ARIA labels
    - Full keyboard navigation support
    - Focus management for modals/dialogs
    - WCAG 2.1 AA compliance verified

- [ ] **TASK-024**: Error Messages & User Feedback
  - **Priority**: P3
  - **Category**: UX
  - **Dependencies**: TASK-009
  - **Description**: Implement toast notifications for async actions, show clear error messages, add loading states, use optimistic updates
  - **Acceptance Criteria**:
    - Toast notifications for all async actions
    - Human-readable error messages
    - Loading indicators on all async operations
    - Optimistic updates where appropriate

- [ ] **TASK-025**: Data Visualization Improvements
  - **Priority**: P3
  - **Category**: UX
  - **Dependencies**: TASK-011
  - **Description**: Add node clustering for large graphs, implement search/filter within graphs, add timeline slider, support graph export
  - **Acceptance Criteria**:
    - Clustering for graphs with 1000+ nodes
    - Search highlights matching nodes
    - Timeline slider filters by date
    - Export to PNG/SVG supported

### Documentation
- [ ] **TASK-026**: Developer Onboarding
  - **Priority**: P3
  - **Category**: Documentation
  - **Dependencies**: TASK-007
  - **Description**: Create quickstart guide, document architecture decisions, write API guidelines, add troubleshooting section
  - **Acceptance Criteria**:
    - New developers can setup in < 1 hour
    - ADRs for major decisions
    - API development guidelines documented
    - Common issues and solutions listed

- [ ] **TASK-027**: Runbook Creation
  - **Priority**: P3
  - **Category**: Documentation
  - **Dependencies**: TASK-022
  - **Description**: Document incident response procedures, failure scenarios and recovery, escalation matrix, support contacts
  - **Acceptance Criteria**:
    - Incident response playbook
    - Recovery steps for common failures
    - Clear escalation paths
    - 24/7 contact information

### Backup & Disaster Recovery
- [ ] **TASK-028**: Backup & Disaster Recovery
  - **Priority**: P1
  - **Category**: DevOps
  - **Dependencies**: TASK-010
  - **Description**: Implement automated database backups, test restore procedures, document RTO/RPO targets
  - **Acceptance Criteria**:
    - Daily automated backups
    - Restore tested monthly
    - RTO < 4 hours, RPO < 1 hour documented

---

## Dependency Graph

```
TASK-001 (JWT Secret) ─┬─> TASK-002 (Keycloak)
                       └─> TASK-007 (Env Management) ─┬─> TASK-010 (Docker)
                                                      └─> TASK-026 (Onboarding)

TASK-003 (SQL Injection) ─> TASK-011 (Graph Optimization) ─┬─> TASK-016 (KPI Dashboard)
                                                           └─> TASK-025 (Data Viz)

TASK-004 (Audit Logs) ─┬─> TASK-005 (PII Masking) ─> TASK-006 (STR Compliance)
                       ├─> TASK-015 (Case Management)
                       └─> TASK-017 (Workflow Engine)

TASK-009 (Error Handling) ─┬─> TASK-020 (API Docs)
                           └─> TASK-024 (Error Messages)

TASK-019 (Test Coverage) ─> TASK-021 (CI/CD)

TASK-010 (Docker) ─┬─> TASK-022 (Monitoring) ─> TASK-027 (Runbook)
                   └─> TASK-028 (Backup/DR)
```

---

## Progress Tracking

| Priority | Total Tasks | Completed | In Progress | Not Started |
|----------|-------------|-----------|-------------|-------------|
| P0       | 4           | 0         | 0           | 4           |
| P1       | 9           | 0         | 0           | 9           |
| P2       | 7           | 0         | 0           | 7           |
| P3       | 8           | 0         | 0           | 8           |
| **Total**| **28**      | **0**     | **0**       | **28**      |

---

## Notes

- Tasks should be completed in priority order (P0 → P1 → P2 → P3)
- Dependencies must be resolved before starting dependent tasks
- Each task should have a corresponding GitHub issue created
- Estimated effort and assignee should be added to each task as planning progresses
