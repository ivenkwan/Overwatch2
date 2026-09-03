# Security Policy

> **Compliance Scope:** ISO/IEC 27001:2022 · PCI-DSS v4.0.1 · OWASP Top 10 for LLM Applications 2025 · OWASP Agentic AI Top 10 (ASI) · AWS Agentic AI Security Prescriptive Guidance · CSA MAESTRO  
> **Last Reviewed:** <!-- INSERT DATE -->  
> **Policy Owner:** <!-- INSERT ROLE -->  
> **Review Cadence:** Quarterly or upon any material change to AI tooling, model versions, or external compliance guidance.

---

## 1. Reporting a Vulnerability

Report all security issues **privately** to the project security team before any public disclosure.

- Do **not** open public issues for credential leaks, prompt injection flaws, injection vulnerabilities, data exposure, or model misbehaviour.
- Use the project's private security advisory channel (e.g., GitHub Security Advisories or a designated email alias).
- Expected acknowledgement: **within 24 hours**; expected triage: **within 72 hours**.
- Reporters will be kept informed of remediation progress and credited (with consent) in the changelog.

> **ISO 27001 mapping:** A.6.8 (Information security event reporting), A.5.24 (Information security incident management planning and preparation)  
> **PCI-DSS mapping:** Requirement 12.10 (Incident response procedures)

---

## 2. Sensitive Data Handling

### 2.1 Secrets and Credentials

- **Never** commit secrets, access tokens, private keys, API keys, certificates, or passwords to the repository — including in comments, commit messages, test fixtures, or documentation.
- All secrets **must** be stored in an approved secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager, Azure Key Vault). Hard-coded credentials in source code or configuration files are prohibited.
- Secrets consumed by AI agents or agentic pipelines **must** use short-lived, dynamically generated credentials — **never** static long-lived tokens. Agents must authenticate via workload identity federation or equivalent ephemeral credential mechanisms.
- Pre-commit hooks implementing secret-scanning (e.g., `git-secrets`, `truffleHog`, `detect-secrets`) are **mandatory** for all contributors. CI pipelines must also run secret-scanning on every push and pull request.
- Rotate any credential that is suspected of exposure **immediately** and within **4 hours** of confirmed exposure.

> **ISO 27001 mapping:** A.8.10 (Information deletion), A.8.12 (Data leakage prevention), A.5.17 (Authentication information)  
> **PCI-DSS mapping:** Requirement 3 (Protect stored cardholder data), Requirement 8 (Identify users and authenticate access to system components)

### 2.2 Cardholder and Sensitive Authentication Data (PCI-DSS)

- AI agents, agentic pipelines, and LLM-based tools **must never** store, log, or transmit Primary Account Numbers (PAN), CVVs, PINs, or full magnetic stripe data in plaintext.
- All cardholder data transmitted by or through AI components must be encrypted in transit (TLS 1.2 minimum; TLS 1.3 preferred) and at rest using AES-256 or equivalent.
- Tokenisation or masking must be applied to cardholder data before it is passed to any AI model, vector store, embedding pipeline, or RAG context window.
- AI agent output filters must block PAN patterns (`[0-9]{13,19}`) from appearing in logs, traces, generated reports, or model responses.
- AI components handling cardholder data must be explicitly scoped within the Cardholder Data Environment (CDE) and included in the annual PCI assessment scope.

> **PCI-DSS mapping:** Requirements 3, 4, 7, 10

### 2.3 General Sensitive Data

- Treat warehouse metadata, lineage outputs, schema definitions, query histories, and infrastructure topology as potentially sensitive (internal classification minimum).
- Validate redaction rules before publishing any AI-generated reports externally. Automated output scanning must confirm no PII, PAN, or internal identifiers are present prior to export.
- Never use production data sets — including cardholder data, PII, or regulated data — in AI model prompts, fine-tuning pipelines, or evaluation suites without explicit data-minimisation and anonymisation controls in place.
- Apply data-masking or synthetic data substitution for all non-production (dev, test, staging) environments.

> **ISO 27001 mapping:** A.8.11 (Data masking), A.8.12 (Data leakage prevention)

---

## 3. Agentic AI Security Controls

This section governs the secure design, deployment, and operation of AI agents, LLM-powered tools, and autonomous agentic coding pipelines. Controls are mapped to the OWASP Top 10 for LLM Applications 2025 (LLM01–LLM10), the OWASP Agentic AI Top 10 (ASI01–ASI10), and AWS Agentic AI Security Prescriptive Guidance.

### 3.1 Agent Identity and Access (Least Privilege)

> OWASP LLM06:2025 Excessive Agency · ASI01 Agent Goal Hijack · ISO 27001 A.8.2, A.8.3, A.5.15

- Every AI agent must be assigned a **unique, non-shared identity** (service account, OIDC workload identity, or equivalent). Shared credentials across agents are prohibited.
- Apply **role-based access control (RBAC) or attribute-based access control (ABAC)** to each agent identity. Agents receive the minimum permissions needed to complete their specific task — not broad administrative or wildcard roles.
- Agent permissions must be **task-scoped and time-bounded**. Use short-lived credentials and session tokens; avoid persistent elevated access.
- Maintain an inventory of all agent identities (Non-Human Identities / NHIs), their associated permissions, owning team, and last-reviewed date. Review and prune stale or over-privileged identities **quarterly**.
- All agents must authenticate to downstream APIs and infrastructure using standard cryptographic mechanisms (OAuth 2.0, mTLS, OIDC). Unauthenticated agent-to-service calls are prohibited.
- High-risk or irreversible actions (production deployments, database writes, secret rotation, billing operations) initiated by an agent **must require human approval** via an explicit gate in the CI/CD or ticketing workflow.

### 3.2 Prompt Injection Prevention

> OWASP LLM01:2025 Prompt Injection · ASI02 Tool Misuse · AWS Agentic AI Security §4

- Treat **all inputs to AI agents as untrusted** by default — including user-supplied text, retrieved documents, web content, tool outputs, and upstream agent messages. Apply multi-layered sanitisation before inputs reach the model.
- Strip or escape control characters, hidden Unicode, newlines, and special tokens that could be interpreted as instructions (Content Disarm and Reconstruction / CDR).
- Apply a **trust hierarchy** to input sources: verified internal system outputs (`high`), direct authenticated user input (`medium`), external web content or documents (`low`). Validation aggressiveness must be calibrated to trust level.
- Keep system prompts strictly separated from user-supplied data. Use structured prompt templates that clearly delimit trusted instructions from untrusted content.
- Deploy automated prompt injection classifiers (e.g., Azure Prompt Shields, Lakera Guard, or equivalent) in the request pipeline; log and alert on classifier rejections.
- Never pass full environment configs, `printenv` outputs, Kubernetes manifests, Terraform state files, or equivalent broad-scope data objects directly into agent context windows. Replace with narrow, field-level queries.
- Implement **memory segmentation**: isolate user session memory from shared organisational memory. Validate all content before committing it to shared memory stores (vector databases, RAG indices).

### 3.3 AI-Generated Code Security

> OWASP LLM03:2025 Supply Chain · LLM05:2025 Improper Output Handling · ISO 27001 A.8.28 · PCI-DSS Requirement 6.2

- AI-generated code is subject to the **same review, testing, and approval gates** as human-authored code. It must not be merged to production branches without peer review.
- All AI-generated code must pass automated Static Application Security Testing (SAST) and, where applicable, Dynamic Application Security Testing (DAST) and Interactive Application Security Testing (IAST) prior to merge.
- AI coding tools are prohibited from generating or suggesting: hard-coded credentials, disabled TLS certificate validation, MD5/SHA1 hashing of sensitive data, `eval()`-style execution of model-provided strings, or unrestricted file system access patterns.
- Clearly label AI-generated code blocks in pull requests (e.g., via a PR label, commit metadata, or inline comment) to enable targeted review.
- AI coding tools are restricted from accessing: authentication modules, payment processing logic, cryptographic key management code, and compliance-critical components unless explicitly approved by the security team.

### 3.4 Output Handling and Validation

> OWASP LLM05:2025 Improper Output Handling · ASI02 Tool Misuse

- **Never** execute model output directly as shell commands, SQL, code, or system calls without intermediate validation and sanitisation.
- AI agent outputs that invoke tools or system APIs must pass through an output-validation layer that enforces an allow-list of permitted actions before execution.
- Sandbox AI command execution in isolated environments (Docker, Firecracker, gVisor) before allowing propagation to production systems.
- Validate that agent outputs do not contain: credentials, PAN/CHD, PII, internal hostnames, API keys, or proprietary metadata before logging, displaying, or transmitting externally.

### 3.5 LLM and Model Supply Chain

> OWASP LLM03:2025 Supply Chain · LLM04:2025 Data and Model Poisoning · ISO 27001 A.5.21, A.5.22

- Third-party AI models, plugins, fine-tuned adapters, and embedding models must undergo a **vendor security assessment** before use in production, including review for known supply chain vulnerabilities.
- Pin all model versions, plugin versions, and embedding model identifiers explicitly in configuration. Unversioned (`latest`) model references are prohibited in production.
- Treat pre-trained model weights and fine-tuned checkpoints as sensitive artefacts: store in access-controlled repositories, scan for backdoors or data poisoning indicators, and maintain an integrity hash.
- Document AI model data provenance: training dataset sources, licensing, and any known biases or data quality issues must be recorded in the model card.
- Apply the same CVE-scan and update policy (see §4) to AI SDKs, agent frameworks (LangChain, AutoGen, CrewAI, etc.), and model-serving infrastructure.

### 3.6 Excessive Agency and Autonomy Guardrails

> OWASP LLM06:2025 Excessive Agency · ASI01–ASI10 · CSA MAESTRO

- Define explicit **action allow-lists** for each agent: enumerate the tools, APIs, file paths, and data sources the agent is authorised to interact with. All other actions are denied by default.
- Implement runtime policy engines (e.g., OPA, custom middleware) that enforce action constraints at execution time — not only at prompt construction time.
- Scope agent resource consumption: impose rate limits, token budgets, and execution time-outs to prevent runaway agent loops or unbounded resource consumption (OWASP LLM10:2025 Unbounded Consumption).
- Require **explicit user-intent confirmation** before agents execute irreversible actions (file deletion, external data transmission, production deployments, billing changes).
- Maintain a full **action audit trail**: every agent invocation must log the agent identity, tool called, input parameters, output summary, authorisation decision, and human approval status (where applicable). Logs must be immutable and retained per §5.

### 3.7 Multi-Agent and Orchestration Security

> ASI06 Memory Poisoning · ASI07 Agent Impersonation

- In multi-agent architectures, treat messages received from upstream agents as **untrusted** unless cryptographically signed and verified.
- Orchestrator agents must not inherit permissions beyond their own assigned role. Delegated tasks to sub-agents must be scoped to the minimum permissions required for that sub-task.
- Implement mutual authentication (mTLS or signed JWT) for agent-to-agent communication.
- Monitor inter-agent message flows for prompt injection payloads embedded within agent outputs propagating through the pipeline.

### 3.8 Agentic Coding Tool Configuration

- Maintain an `.aiignore` (or equivalent tool-specific exclusion file) that prevents AI coding assistants from reading or generating code in: authentication flows, cryptographic key management, payment processing modules, PII handling routines, and compliance-critical logic.
- AI coding tool access to the repository must be gated by the same IAM controls as human developer access. Tokens used by AI tools must be scoped to the minimum repository permissions required.
- Audit the list of permitted AI coding tools annually and upon material version changes. Unapproved tools must not be used on this codebase.

---

## 4. Dependency Security

- All Python packages in `requirements.txt` (and any equivalent files: `pyproject.toml`, `setup.cfg`, `Pipfile`) must have an **explicit version pin** (e.g., `requests==2.31.0`). Unpinned or wildcard (`>=`, `~=`) dependencies are not permitted in production configurations.
- Every dependency update **must** be accompanied by a CVE scan (`make security-scan`) with a **current timestamp** recorded in the file header or scan artefact.
- CVE scans must also be run on:
  - All AI/ML frameworks and agentic libraries (LangChain, AutoGen, transformers, etc.)
  - Model-serving infrastructure dependencies
  - CI/CD pipeline tool dependencies
- A Software Bill of Materials (SBOM) in SPDX or CycloneDX format must be generated and stored with each release artefact.
- Dependencies with known **Critical** (CVSS ≥ 9.0) or **High** (CVSS ≥ 7.0) unpatched CVEs must not be merged to the default branch. A documented exception with security team sign-off is required if no upstream fix exists.
- Automated dependency scanning (e.g., `dependabot`, `snyk`, `pip-audit`) must be enabled in the CI pipeline and configured to block merges on High/Critical findings.

> **ISO 27001 mapping:** A.8.8 (Management of technical vulnerabilities), A.5.21 (Managing information security in the ICT supply chain)  
> **PCI-DSS mapping:** Requirement 6.3 (Security vulnerabilities are identified and addressed), Requirement 6.3.2 (Maintain an inventory of all bespoke and custom software)

---

## 5. Audit Logging and Monitoring

> ISO 27001 A.8.15 (Logging), A.8.16 (Monitoring activities) · PCI-DSS Requirements 10, 11

- Audit logs **must** capture: timestamp (UTC, millisecond precision), actor identity (human or agent), action performed, target resource, outcome (success/failure), and source IP.
- Agent-specific logs must additionally record: agent identity and version, tool(s) invoked, prompt hash (never full prompt content unless required for forensics and appropriately access-controlled), authorisation decision, and human approval reference (if applicable).
- Logs containing cardholder data or PII must be masked or tokenised at the point of ingestion into the logging pipeline.
- Log integrity must be protected via append-only storage, cryptographic hashing, or equivalent tamper-evident mechanisms.
- Logs must be retained for a minimum of **12 months** (with 3 months immediately available for review) in accordance with PCI-DSS Requirement 10.7 and ISO 27001 A.8.15.
- Export all security-relevant logs to a SIEM. Configure real-time alerts for: anomalous agent behaviour, permission escalation attempts, secret access outside approved workflows, and high-volume data access by agent identities.
- Conduct log reviews and anomaly reports **weekly** at minimum; automated continuous monitoring is the preferred posture.

---

## 6. Secure Development Lifecycle (SDL) for AI Features

> PCI-DSS Requirements 6.1, 6.2, 6.5 · ISO 27001 A.8.25, A.8.28, A.8.29

- Threat modelling **must** be performed for all new AI/agentic features at the design stage, explicitly covering: prompt injection vectors, excessive agency risk, model supply chain integrity, data exposure through context windows, and multi-agent trust boundaries.
- Prompts used in production must be treated as **code artefacts**: version-controlled, peer-reviewed, and subject to change management processes equivalent to application code.
- AI-related security training covering OWASP Top 10 for LLMs, prompt injection, and agentic security risks is **mandatory** for all developers working on AI-integrated features, with training records retained for compliance evidence (PCI-DSS Requirement 6.2.2).
- All changes to AI model versions, agent orchestration logic, prompt templates, or agentic tool configurations must follow the standard change management process, including security review and staged rollout.
- Conduct adversarial red-team testing (including prompt injection scenarios) against agentic features prior to production release and at least annually thereafter.

---

## 7. Incident Response — AI-Specific Addendum

> ISO 27001 A.5.24–A.5.28 · PCI-DSS Requirement 12.10

In addition to the standard incident response plan, the following AI-specific procedures apply:

1. **Agent containment:** Upon suspected compromise or misbehaviour, immediately revoke agent tokens, suspend agent identities, and halt agent task queues. This must be achievable within **15 minutes** of detection.
2. **Prompt injection investigation:** Preserve input logs (prompt hashes, retrieved context sources) as forensic evidence. Replay agent action chains from audit logs to reconstruct the attack path.
3. **Model integrity check:** If a model supply chain compromise is suspected, roll back to the last known-good pinned model version and re-validate the integrity hash.
4. **Notification obligations:** Incidents involving cardholder data exposure trigger PCI-DSS notification obligations to the acquiring bank and card brands. Incidents involving personal data may trigger GDPR/local data protection notification requirements.
5. **Post-incident review:** Complete a root cause analysis and document lessons learned within **5 business days** of incident closure. Update guardrails, allow-lists, or monitoring rules as corrective actions.

---

## 8. Compliance Mapping Quick Reference

| Control Area | ISO 27001:2022 Annex A | PCI-DSS v4.0.1 Requirement | OWASP LLM Top 10 2025 |
|---|---|---|---|
| Secrets management | A.5.17, A.8.12 | Req. 3, 8 | LLM02, LLM07 |
| Access control / NHI | A.5.15, A.8.2, A.8.3 | Req. 7, 8 | LLM06 |
| Prompt injection | A.8.28, A.8.29 | Req. 6.2, 6.4 | LLM01, LLM05 |
| AI-generated code review | A.8.28 | Req. 6.2.3, 6.2.4 | LLM03, LLM05 |
| Supply chain / dependencies | A.5.21, A.5.22, A.8.8 | Req. 6.3, 12.3 | LLM03, LLM04 |
| Audit logging | A.8.15, A.8.16 | Req. 10 | LLM06 |
| Cardholder data protection | A.8.11, A.8.12 | Req. 3, 4 | LLM02 |
| Incident response | A.5.24–A.5.28 | Req. 12.10 | — |
| Vulnerability management | A.8.8 | Req. 6.3 | LLM03 |
| Developer training | A.6.3 | Req. 6.2.2 | — |

---

*This policy should be reviewed in conjunction with the project's Information Security Management System (ISMS) Statement of Applicability (SoA) and the organisation's PCI DSS Self-Assessment Questionnaire (SAQ) or Report on Compliance (RoC).*
