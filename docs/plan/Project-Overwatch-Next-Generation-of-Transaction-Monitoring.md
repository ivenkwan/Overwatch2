**Project Overwatch**
**A Comprehensive Proposal for Unified Transaction Monitoring Across Fiat and Regulated Stablecoin Transactions**

**Executive Summary**
The convergence of traditional fiat payments and regulated stablecoin transactions has created a new frontier of compliance complexity for financial institutions. Stablecoin transaction volumes reached **$33 trillion globally in 2025**, a 72% year-on-year increase, and are projected to hit **$56 trillion by 2030**. Meanwhile, the regulatory landscape has rapidly crystallised: Hong Kong's Stablecoins Ordinance took effect on August 1, 2025, the EU's MiCA regulation imposed full stablecoin requirements from June 2024, and the US GENIUS Act formalised federal stablecoin oversight in mid-2025. All frameworks converge on a single expectation — stablecoin transactions must be monitored with the same rigour as traditional banking transactions.
**Project Overwatch** is a strategic initiative to design and implement a **Unified Transaction Monitoring Platform** that applies consistent Anti-Money Laundering (AML), Counter-Terrorist Financing (CTF), and sanctions screening controls across both fiat and regulated stablecoin payment rails. The proposal addresses the root causes of compliance fragmentation, defines the target operating model, and charts an implementation roadmap grounded in regulatory requirements across multiple jurisdictions.

**1. Problem Statement: The Dual-Rail Compliance Gap**
Financial institutions operating across both fiat and stablecoin rails have largely inherited a fragmented compliance architecture — separate monitoring systems, separate rule sets, and separate alert queues for each payment type. This architecture is no longer fit for purpose in a world where regulators, criminals, and customers all operate seamlessly across both rails.
**1.1 The Scale of the Challenge**
The stablecoin market has grown from a niche instrument to a **$255 billion market**, with projections placing it at **$2 trillion within a few years**. Major institutions — including Mastercard, Visa, and Worldpay — have embraced hybrid fiat-stablecoin payment infrastructure. Providers such as Mesta offer APIs handling fiat and stablecoin transactions across more than 100 countries. For financial institutions serving this market, the compliance burden has doubled without a commensurate increase in unified oversight.
Critically, **most on-chain illicit activity now involves stablecoins**, according to FATF's 2025 targeted report. A significant and growing share of money laundering patterns involves converting illicit crypto funds into stablecoins, then redeeming them into fiat via secondary bank accounts — a layering technique that is entirely invisible to monitoring systems that cover only one rail. Without unified oversight, these cross-rail laundering schemes leave no detectable footprint.
**1.2 The Cost of Fragmentation**
Operating parallel compliance systems is expensive in financial, operational, and reputational terms:
Traditional AML systems generate **false positive alert rates of 90–95%**, overwhelming compliance teams and masking genuine risk.
Compliance teams must manage **multiple rulebooks and workflows** across fiat and crypto channels, creating duplication and decision fatigue 
Siloed case queues mean that an analyst investigating a suspicious USDC transfer may have no visibility into the same customer's concurrent wire transfer activity 
Regulatory enforcement actions have imposed significant penalties on firms with insufficient AML controls — Paxos's $48.5 million fine stands as a direct precedent 
BIS and FSB have explicitly insisted that stablecoins performing payment-like functions be held to **equivalent standards as traditional banks** 

**2. Business Challenges**
**2.1 Regulatory Complexity: Overlapping and Evolving Frameworks**
Financial institutions operating in today's hybrid payment environment face compliance obligations drawn from multiple, sometimes overlapping, regulatory regimes simultaneously.
**2.1.1 Hong Kong (HKMA)**
Hong Kong's Stablecoins Ordinance (Cap. 656) came into operation on **August 1, 2025**, supervised by the HKMA. Licensed Stablecoin Issuers (SIs) are classified as "financial institutions" under the Anti-Money Laundering and Counter-Terrorist Financing Ordinance (AMLO, Cap.615) — placing them under the same AML/CFT framework as banks (Authorised Institutions) and stored value facility licensees. Key HKMA expectations include: 
Customer Due Diligence (CDD) for transactions at or above **HK$8,000**, covering both custodial and unhosted wallets 
**Enhanced monitoring** for stablecoin transfers to/from unhosted wallets, including screening, transaction limits, and possible blocking 
**Travel Rule** compliance under Section 13A of Schedule 2 of the AMLO, requiring originator/beneficiary information sharing on stablecoin transfers 
Adoption of **blockchain ****analytics tools** to screen transactions and wallet addresses on an ongoing basis 
**Ecosystem monitoring**: issuers must monitor tokens beyond their direct customers, extending oversight across the full stablecoin circulation lifecycle 
The HKMA further requires licensees to implement blacklisting of wallets linked to sanctioned or illicit actors, and to freeze stablecoins promptly upon regulatory or law enforcement request.
**2.1.2 European Union (****MiCA****)**
The EU's Markets in Crypto-Assets Regulation (MiCA) entered into force in June 2023, with stablecoin provisions fully applicable from **June 30, 2024**. MiCA defines two regulated stablecoin categories:
**E-money tokens (EMTs)**: value pegged to a single fiat currency, requiring EMI/credit institution licensing
**Asset-referenced tokens (ARTs)**: value pegged to a basket of assets, with stringent reserve and disclosure requirements
MiCA imposes a **cap of 1 million transactions per day** for non-EU currency stablecoins and mandates full Travel Rule compliance under the Transfer of Funds Regulation (TFR) for all crypto-asset service providers (CASPs) from December 2024. CASPs must verify customer identities, monitor transactions for suspicious activity, and report to financial intelligence units — mirroring traditional finance obligations. The European Banking Authority's guidance further urges a risk-based approach where high-risk transactions are flagged and reviewed in real time, regardless of whether they are fiat or crypto.
**2.1.3 United States (GENIUS Act & BSA)**
The GENIUS Act, passed in mid-2025, establishes federal licensing requirements for all stablecoin issuers and explicitly subjects them to **Bank Secrecy Act (BSA) requirements**. This mandates:
Comprehensive AML/CFT programs with formal risk assessments
Real-time monitoring across all major blockchains with automated detection of suspicious patterns
Enhanced due diligence for institutions facilitating stablecoin transactions
Foreign stablecoin issuers accessing US markets must meet identical AML and sanctions compliance standards as domestic players, eliminating regulatory arbitrage
**2.1.4 FATF Global Standards**
At the international level, FATF's **Recommendation 15** (virtual assets) and **Recommendation 16** (Travel Rule) form the baseline. Following the June 2025 FATF Plenary:
The Travel Rule has been revised to cover **peer-to-peer cross-border transfers above USD/EUR 1,000** with standardised originator and beneficiary data requirements
Beneficiary verification is now a **requirement, not a recommendation**
The revised rule is designed to work within **ISO 20022**, the global standard governing all cross-border SWIFT payments
As of early 2026, **42 countries** are Travel Rule compliant, and **85 of 117 FATF-member jurisdictions** have passed or are actively passing Travel Rule legislation
FATF's 2026 targeted report on stablecoins and unhosted wallets calls for advanced blockchain analytics, smart-contract-based controls, and strengthened cross-border supervisory coordination
**2.2 Operational Challenges**
Beyond regulatory complexity, financial institutions face a set of structural operational challenges when running fiat and stablecoin compliance in parallel:

| Challenge | Description | Impact |
| --- | --- | --- |
| Fragmented Systems | Separate blockchain monitoring tools and fiat transaction monitors with no shared data layer | Blind spots at the rail crossover; same customer, different risk profiles |
| Duplicate Rule Sets | Separate threshold configurations, detection scenarios, and alert queues for each rail | Analyst overload; conflicting risk thresholds for the same customer activity |
| No Customer 360 View | Customer's fiat and crypto activity visible in different systems | Inability to detect cross-rail laundering; layering patterns invisible |
| 24/7 Blockchain vs. Batch Fiat | On-chain transactions occur round-the-clock; legacy fiat systems operate in batch cycles | Monitoring latency for stablecoin flows; delay in detecting time-sensitive risks |
| Cross-Chain Fragmentation | Stablecoins existing across multiple blockchains via bridges/L2 networks that bypass issuer compliance layers | Audit trail fragmentation; Travel Rule gaps in multi-chain flows |
| Unhosted Wallet Opacity | Self-custodied wallets provide no built-in KYC; enhanced monitoring is required | Higher manual review burden; risk of sanctions evasion via private wallets |
| Ecosystem Monitoring Scope | Issuers must monitor tokens beyond their direct customers | Requires blockchain analytics beyond internal transaction data |
| High False Positive Rate | Traditional rule-based systems flag 90–95% of alerts as non-suspicious | Compliance team burnout; genuine risks buried in noise |
| Legacy System Auditability | Older solutions lack version-controlled configuration changes, explainability logs | Regulatory examination failures; inability to demonstrate model governance |
| Cross-Rail Layering | Illicit funds converted to stablecoin, then redeemed as fiat in different accounts | Undetectable without unified, cross-rail transaction history |

**2.3 Strategic Business Risks of Inaction**
Failure to address these challenges carries compounding consequences:
**Regulatory enforcement risk**: Regulators in HK, EU, and US have signalled zero tolerance for gaps in AML controls. Enforcement actions carry monetary penalties and, increasingly, operating licence revocations.
**Reputational risk**: Public regulatory actions erode customer trust and institutional partnerships.
**Revenue opportunity cost**: 52% of corporate/financial services executives cite lower transaction costs as the top reason for adopting stablecoins; 48% cite faster settlements. Institutions that cannot compliantly support stablecoins will cede this market to competitors.
**Operational inefficiency**: Maintaining two parallel compliance teams, toolsets, and vendor contracts is materially more expensive than a unified approach.
**Criminal exploitation**: Sophisticated actors actively exploit the gap between fiat and crypto monitoring systems. Without unified oversight, institutions become inadvertent conduits.
**3. Proposed Solution: Project Overwatch — Unified Transaction Monitoring Platform**
Project Overwatch proposes a **purpose-built, unified compliance platform** that applies consistent AML, CTF, fraud detection, sanctions screening, and regulatory reporting controls across both fiat and regulated stablecoin payment rails — eliminating the seams that financial crime currently exploits.
The core design principle is **rail abstraction**: the compliance engine treats a $10,000 SWIFT wire, a $10,000 ACH transfer, and a 10,000 USDC on-chain transfer with identical analytical rigour under a unified risk model, while preserving rail-specific contextual data necessary for regulatory reporting.
**3.1 Business Case**
**3.1.1 Strategic Rationale**
Project Overwatch positions the institution as:
**Regulatory-ready**: Pre-compliant with HKMA Stablecoins Ordinance, MiCA, GENIUS Act, and FATF Recommendations 15 and 16, reducing the risk of enforcement actions
**Market-competitive**: Capable of onboarding regulated stablecoin clients and supporting hybrid fiat-stablecoin payment flows that represent the industry's fastest-growing segment
**Operationally efficient**: Single system, single team, single vendor relationship for end-to-end transaction monitoring across all rails
**Intelligence-superior**: Cross-rail customer intelligence that identifies complex laundering patterns invisible to siloed systems
**3.1.2 Quantified Benefits**
**False positive reduction**: AI-powered unified monitoring can reduce false positive alert rates by **70–80%** compared to traditional rule-based systems; HSBC reduced alerts by over **60%** while finding 2–4 times more confirmed suspicious activity using AI-enhanced monitoring
**Cost savings**: Eliminating duplicate vendors, toolsets, and analyst workflows; unified platforms have demonstrated **93% reductions in false positive alerts**, translating to material savings in analyst time and operational costs
**Revenue enablement**: Stablecoin payment flows are projected to reach **$56 trillion by 2030**; institutions with compliant infrastructure can capture a disproportionate share of institutional and fintech client mandates
**Regulatory capital efficiency**: Demonstrably robust AML controls may support more favourable treatment in supervisory reviews, reducing capital buffers held against operational risk
**3.2 Compliance & Regulatory Design**
**3.2.1 Unified Customer Due Diligence (CDD) Framework**
Project Overwatch consolidates CDD data into a single customer risk profile that aggregates identity, KYC documentation, and transaction history across all rails. Key design elements:
**Unified onboarding**: Single KYC/KYB workflow applied at customer onboarding, with outcomes feeding both fiat and crypto monitoring engines
**Wallet attribution**: For each customer, custodial wallets are linked to the customer profile; unhosted wallet interactions trigger enhanced due diligence workflows per HKMA guidance
**Dynamic risk scoring**: Customer risk ratings updated in real time as fiat and stablecoin transactions accumulate, using behavioural baselining to distinguish legitimate from anomalous activity
**VASP counterparty due diligence**: For stablecoin transfers involving other virtual asset service providers (VASPs), automated due diligence against VASP registries and AML ratings
**3.2.2 Travel Rule Engine**
A dedicated Travel Rule module handles information collection and transmission for both payment legs:
**Fiat leg**: ISO 20022-structured originator/beneficiary data collection for SWIFT MX/SEPA/ACH transfers
**Stablecoin leg**: Automated collection and transmission of VASP-to-VASP originator/beneficiary data for on-chain transfers in compliance with FATF Recommendation 16
**Threshold management**: Configurable per jurisdiction (USD/EUR 1,000 for FATF members; jurisdiction-specific thresholds as required)
**Protocol interoperability**: Integration with leading Travel Rule data-sharing protocols to ensure counterparty VASPs can receive and transmit required data
**Unhosted**** wallet enhanced monitoring**: When transfers involve unhosted wallets, automatic escalation to enhanced screening workflows per HKMA and FATF requirements
**3.2.3 Ecosystem-Wide Stablecoin Monitoring**
Beyond direct customer transactions, Project Overwatch implements the **ecosystem monitoring** mandated by the HKMA and expected under MiCA — extending surveillance across the full stablecoin circulation lifecycle:
On-chain monitoring of the institution's issued or supported stablecoins, tracking token flows beyond direct counterparties
Automated blacklisting of wallet addresses linked to sanctioned entities, with integration into freezing workflows
Smart-contract-level compliance controls where technically feasible, enforcing prohibition on transfers to sanctioned entities through programmable rules
Scheduled and event-driven risk re-assessments of stablecoins in circulation
**3.2.****4 Sanctions**** Screening**
All transactions — fiat and stablecoin — are screened in real time against:
OFAC, UN, EU, and HK sanctions lists
Politically Exposed Person (PEP) databases
Adverse media and law enforcement watchlists
On-chain entity attribution databases mapping wallet addresses to known sanctioned entities, exchanges, mixers, and dark market services
Screening results are logged with timestamps and attached to the transaction record for audit purposes.
**3.2.5 Regulatory Reporting**
A unified reporting module automates the generation and submission of regulatory reports across jurisdictions:
**SAR/STR filing**: Automated Suspicious Activity Report / Suspicious Transaction Report generation with pre-populated transaction data, customer risk context, and analyst notes
**HKMA reporting**: Compliance with AMLO Schedule 2 reporting obligations for stablecoin transfers
**Cross-jurisdictional mapping**: Configurable report templates mapped to jurisdiction-specific formats (FinCEN SAR, JFIU STR, FIU reports)
**Audit-ready case logs**: Every investigative action, rule configuration change, and alert disposition is logged with full version control and approver sign-off, addressing the auditability requirements flagged by regulators
**3.3 Technology Architecture**
**3.3.1 Architecture Principles**
Project Overwatch is designed on four architectural principles:
**Rail abstraction**: A normalisation layer translates fiat transaction events and on-chain blockchain events into a common transaction schema before monitoring, ensuring uniform analytical treatment
**Real-time processing**: Sub-second transaction screening for both fiat and stablecoin transactions, supporting 24/7 blockchain operations alongside traditional banking hours
**Horizontal scalability**: Microservices-based architecture enabling independent scaling of monitoring, screening, and case management components under peak load
**Explainability and governance**: All AI model outputs are accompanied by human-readable explanations; all rule and model changes are version-controlled with mandatory approval workflows
**3.3.2 System Architecture Overview**
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                         │
│  ┌─────────────────┐    ┌──────────────────────────────────┐    │
│  │  FIAT RAIL      │    │  STABLECOIN / ON-CHAIN RAIL      │    │
│  │  SWIFT/MX       │    │  Blockchain Nodes (ETH, SOL...)  │    │
│  │  ACH / SEPA     │    │  USDC, USDT, HKD Stablecoin      │    │
│  │  FPS / FPS-C    │    │  Multi-chain Bridge Events       │    │
│  │  Card Networks  │    │  VASP Transfer Events            │    │
│  └────────┬────────┘    └───────────────┬──────────────────┘    │
│           │                             │                       │
│           └──────────────┬──────────────┘                       │
│                          ▼                                      │
│           ┌──────────────────────────────┐                      │
│           │   NORMALISATION ENGINE       │                      │
│           │   (Common Transaction Schema)│                      │
│           │   ISO 20022 Data Mapping     │                      │
│           └──────────────┬───────────────┘                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  MONITORING & INTELLIGENCE LAYER                │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ RULE-BASED      │  │  AI/ML       │  │  BLOCKCHAIN        │  │
│  │ TRANSACTION     │  │  ANOMALY     │  │  ANALYTICS         │  │
│  │ MONITORING      │  │  DETECTION   │  │  ENGINE            │  │
│  │ (Configurable   │  │  (Behavioural│  │  (On-chain risk    │  │
│  │ scenarios)      │  │  baselining) │  │  scoring, graph    │  │
│  └────────┬────────┘  └──────┬───────┘  │  analytics)        │  │
│           │                  │          └──────────┬─────────┘  │
│  ┌────────▼──────────────────▼───────────────────▼──────────┐   │
│  │                RISK SCORING ENGINE                       │   │
│  │  (Unified Customer 360 Risk Profile — Fiat + Stablecoin) │   │
│  └────────────────────────────────┬─────────────────────────┘   │
│                                   │                             │
│  ┌────────────────────────────────▼──────────────────────────┐  │
│  │            SANCTIONS & PEP SCREENING MODULE               │  │
│  │  (Real-time screening: OFAC, UN, EU, HK + On-chain lists) │  │
│  └────────────────────────────────┬──────────────────────────┘  │
│                                   │                             │
│  ┌────────────────────────────────▼──────────────────────────┐  │
│  │               TRAVEL RULE ENGINE                          │  │
│  │  (ISO 20022 fiat leg + VASP-to-VASP stablecoin leg)       │  │
│  └────────────────────────────────┬──────────────────────────┘  │
└──────────────────────────────────┼──────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────┐
│                  CASE MANAGEMENT & REPORTING LAYER              │
│  ┌─────────────────────┐  ┌───────────────────────────────────┐ │
│  │  UNIFIED CASE       │  │   REGULATORY REPORTING MODULE     │ │
│  │  MANAGEMENT         │  │   SAR / STR Generation            │ │
│  │  (Single alert      │  │   HKMA / MiCA / FinCEN reporting  │ │
│  │  queue, RBAC,       │  │   Version-controlled audit logs   │ │
│  │  audit trails)      │  └───────────────────────────────────┘ │
│  └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘

**3.3.3 Core Technical Components**
**A. Data Ingestion and ****Normalisation**
The platform ingests transactions from multiple sources through an API gateway and event streaming infrastructure:
**Fiat sources**: Core banking system feeds, payment network APIs (SWIFT, SEPA, ACH, Faster Payments, card network settlement files)
**On-chain sources**: Direct node connections or third-party blockchain data providers for Ethereum, Solana, Tron, and other major stablecoin networks; USDC, USDT, and licensed stablecoin token event streams
**Normalisation**: All events are mapped to a unified transaction schema using ISO 20022 as the structural reference, enabling consistent field mapping across rail types
**Message streaming**: Apache Kafka or equivalent event-streaming infrastructure supports asynchronous, high-volume ingestion without creating bottlenecks
**B. AI-Augmented Transaction Monitoring Engine**
The monitoring engine combines rule-based and machine-learning approaches in a hybrid architecture:
**Rule-based layer**: Configurable detection scenarios covering structuring, velocity breaches, high-risk jurisdiction flows, and known typologies — mapped to FATF red flag indicators and jurisdiction-specific guidance
**Machine learning layer**: Behavioural baselining models that learn what is "normal" for each customer across both rails, flagging deviations rather than absolute thresholds. This approach is the primary driver of false positive reduction — a $20,000 payment is suspicious only if it is unusual for that specific customer
**Graph analytics**: Network relationship analysis to detect hidden connections between entities, mule account clusters, and layering networks that are invisible in transaction-level analysis
**Continuous model calibration**: Models retrained on a rolling basis using confirmed case outcomes; all model versions version-controlled and subject to model governance review
**C. Blockchain Analytics Integration**
On-chain risk intelligence is integrated via API from specialised blockchain analytics providers (e.g., Chainalysis, Elliptic, Scorechain), supplemented by the platform's own on-chain monitoring:
**Wallet risk scoring**: Each wallet address involved in a stablecoin transaction receives a risk score based on its transaction history, exposure to dark markets, exchanges, mixers, and sanctioned entities
**Taint analysis**: Funds tracing using proportional taint scoring to assess the provenance of received funds
**Entity attribution**: Wallet addresses matched to known entities (exchanges, VASPs, institutional wallets) for counterparty due diligence
**Ecosystem monitoring feeds**: Continuous on-chain monitoring of stablecoins in circulation, feeding back into the unified risk engine 
**D. Microservices Architecture and Scalability**
The platform is built on a microservices architecture to support modularity, independent scaling, and continuous deployment:
Each functional domain (ingestion, monitoring, screening, Travel Rule, case management, reporting) operates as an independent service
Services communicate via RESTful APIs for synchronous operations and event streams for asynchronous processing
Container orchestration (Kubernetes) enables horizontal scaling of compute-intensive components during peak transaction volumes
API gateway provides unified entry point with authentication, rate limiting, and request routing
Near-100% uptime SLA, supporting 24/7 blockchain monitoring without maintenance windows
**E. Case Management and Audit**
**Unified alert queue**: All alerts — whether triggered by fiat or stablecoin activity — feed into a single case management interface, with full cross-rail transaction history visible to the investigating analyst
**Role-based access control (RBAC)**: Tiered access for analysts, managers, compliance officers, and external auditors
**Audit trail**: Every transaction event, alert disposition, rule change, and model update is immutably logged with user identity, timestamp, and justification
**Configurable investigation templates**: Jurisdiction-specific case templates aligned with HKMA, FIU, and FinCEN investigation requirements
**SAR/STR automation**: Pre-populated regulatory reports generated from case data, reducing filing time and improving accuracy

**4. Implementation Roadmap**
Project Overwatch is proposed as a three-phase implementation over 18 months, aligned with the KPMG stablecoin implementation framework:
**Phase 1: Foundation (Months 1–6)**
**Core Infrastructure and Fiat Monitoring Enhancement**

| Workstream | Deliverable |
| --- | --- |
| Data architecture | Common transaction schema; API gateway; Kafka event streaming setup |
| Fiat monitoring uplift | Migration of existing fiat TM rules to new unified engine; RBAC configuration |
| Blockchain data integration | Blockchain analytics API integration; wallet screening baseline |
| CDD/KYC unification | Unified customer risk profile schema; wallet attribution workflow |
| Travel Rule (fiat) | ISO 20022 fiat-leg Travel Rule compliance; SWIFT MX migration |
| Regulatory mapping | Jurisdiction-specific rule mapping (HKMA AMLO, MiCA TFR, BSA) |

**Exit Criteria**: All fiat transactions monitored through new unified engine; blockchain analytics integrated for wallet screening; regulatory mapping documented.
**Phase 2: Integration (Months 7–12)**
**Stablecoin Rail Integration and AI Augmentation**

| Workstream | Deliverable |
| --- | --- |
| Stablecoin ingestion | Live ingestion of USDC, USDT, and licensed stablecoin on-chain events |
| Unified monitoring engine | Single monitoring engine processing fiat and stablecoin transactions under unified risk model |
| AI/ML deployment | Behavioural baselining models live; false positive reduction baseline established |
| Travel Rule (stablecoin) | VASP-to-VASP Travel Rule data exchange live; unhosted wallet enhanced monitoring |
| Ecosystem monitoring | On-chain ecosystem monitoring of stablecoins in circulation per HKMA/MiCA requirements |
| Unified case management | Single alert queue; cross-rail case visibility; SAR/STR automation |

**Exit Criteria**: All stablecoin transactions co-monitored with fiat in unified engine; Travel Rule operational for both legs; false positive rate measurably reduced vs baseline.
**Phase 3: ****Optimisation**** (Months 13–18)**
**Advanced Intelligence and Full Regulatory Readiness**

| Workstream | Deliverable |
| --- | --- |
| Graph analytics | Network analysis models deployed for entity relationship detection |
| Smart contract controls | Smart contract-level compliance controls for issued stablecoins (where applicable) |
| Multi-chain coverage | Extended blockchain coverage for bridging/L2 activity; cross-chain audit trail |
| Model governance | Full model governance framework; version control; independent model validation |
| Regulatory examination readiness | Mock regulatory examination; audit trail review; SAR quality assurance |
| Continuous improvement | Feedback loop from confirmed cases to model retraining; quarterly rule tuning |

**Exit Criteria**: Full regulatory examination readiness across HKMA, MiCA, and FATF standards; false positive rate reduced by 70%+ vs pre-Project baseline; unified platform certified as single source of truth for all transaction monitoring.
**5. Governance and Risk Management**
**5.1 Project Governance**
A Project Overwatch Steering Committee should include representation from:
**Compliance / Financial Crime** (executive sponsor)
**Technology / Architecture**
**Legal / Regulatory Affairs**
**Business Lines** (treasury, payments, digital assets)
**Risk Management**
**Internal Audit** (observer)
Quarterly milestone reviews against the implementation roadmap, with monthly working group meetings for each functional workstream.
**5.2 Key Risks and Mitigations**

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Data quality from legacy fiat systems | High | High | Data quality assessment in Phase 1; cleansing workstream; parallel running period |
| Regulatory requirements evolving during build | Medium | High | Modular architecture with configurable rule sets; dedicated regulatory change monitoring function |
| Blockchain data provider dependency | Medium | Medium | Dual-provider strategy; API abstraction layer to enable provider switching |
| AI model explainability challenged by regulators | Medium | High | Explainable AI (XAI) design requirement; model governance framework from Phase 1 |
| Cross-chain bridge coverage gaps | High | Medium | Phased coverage; documented residual risk; manual review escalation for bridge activity |
| Staff change management | Medium | Medium | Training programme; phased analyst onboarding aligned with platform rollout |
| Third-party VASP Travel Rule non-compliance | High | Medium | VASP due diligence framework; escalation workflows for non-responsive counterparties |

**5.3 Regulatory Engagement Strategy**
Given the novelty of the unified fiat-stablecoin monitoring approach, proactive engagement with regulators is recommended:
**HKMA pre-engagement**: Brief the HKMA on the Project Overwatch architecture, particularly the ecosystem monitoring and Travel Rule components, as part of the stablecoin licensing application process
**MiCA**** compliance documentation**: Prepare a MiCA compliance mapping document demonstrating how Project Overwatch satisfies EMT/ART issuer AML obligations for EU regulators
**Model governance transparency**: Maintain documentation suitable for supervisory examination of AI model design, training data, validation methodology, and governance controls

**6. Competitive Landscape and Vendor Considerations**
The unified compliance platform market is evolving rapidly. Key platform categories and exemplars relevant to Project Overwatch include:

| Category | Representative Players | Relevance to Project Overwatch |
| --- | --- | --- |
| Unified fiat + crypto AML platforms | Flagright, iComply, Napier AI | Core monitoring engine candidates; evaluate for rail coverage, API design, HKMA/MiCA certification |
| Blockchain analytics | Chainalysis, Elliptic, Scorechain | On-chain risk scoring, wallet screening, taint analysis, ecosystem monitoring |
| Travel Rule infrastructure | OpenVASP, Notabene, Sygna | VASP-to-VASP data exchange for stablecoin Travel Rule compliance |
| AI/ML transaction monitoring | Lucinity, Consilient | False positive reduction; behavioural baselining; graph analytics |
| Case management and SAR filing | NICE Actimize, Quantexa, Oracle FCCM | Investigation workflow; SAR automation; audit trail management |

A build-vs-buy analysis should be conducted during Phase 1 scoping, evaluating total cost of ownership, time-to-compliance, and vendor regulatory certification status across relevant jurisdictions. A hybrid approach — leveraging a unified monitoring platform from a specialist vendor, integrated with best-of-breed blockchain analytics — is likely to offer the optimal combination of speed-to-compliance and analytical depth.

**7. Conclusion**
The convergence of fiat and regulated stablecoin transactions is not a future scenario — it is today's operational reality. With global stablecoin transaction volumes at **$33 trillion and rising**, regulatory frameworks firmly in place across Hong Kong, the EU, and the US, and criminal exploitation of the compliance gap already well-documented, the case for a unified transaction monitoring architecture is both commercially and regulatorily compelling.
Project Overwatch addresses the root causes of fragmented compliance — siloed systems, duplicate rule sets, blind spots at the rail crossover, and unsustainable false positive rates — through a purpose-designed unified platform. The solution delivers measurable business outcomes: **70–80% reductions in false positives**, materially lower operational costs, regulatory examination readiness across HKMA, MiCA, and FATF standards, and the commercial capability to serve the fastest-growing segment of the payments market.
The three-phase implementation roadmap is designed to deliver early value — compliance-ready fiat monitoring and blockchain analytics integration within six months — while building toward a fully unified, AI-augmented, and ecosystem-aware monitoring architecture that will remain fit for purpose as regulatory expectations continue to evolve.
Project Overwatch is not merely a compliance investment. It is the foundational infrastructure for participating in the next era of financial services.

*This proposal has been prepared based on current regulatory requirements and market intelligence as of April 2026. Regulatory frameworks referenced include HKMA Stablecoins Ordinance (Cap. 656), EU **MiCA** Regulation, US GENIUS Act, and FATF Recommendations 15 and 16 as revised at **the June** 2025 FATF Plenary.*

# AML Admin Portal — Functional & Non-Functional Requirements Specification
## Executive Summary
This document specifies the functional and non-functional requirements for an AML (Anti-Money Laundering) admin portal comprising four integrated modules: a KPI Monitoring and Alerting Dashboard, a Case Management system, an Interactive Network Visualization layer for fund flow analysis, and an ETL pipeline serving a PostgreSQL transaction database and Apache AGE graph exploration layer. The specification targets the established stack of Next.js + React + TypeScript on the frontend and Python + FastAPI + PostgreSQL + Apache AGE + Temporal on the backend.[1][2][3]
The system must satisfy global regulatory frameworks including the Bank Secrecy Act (BSA), EU AML Directives (AMLD5 and AMLD6), FATF recommendations, and GDPR, all of which mandate transaction monitoring, suspicious activity reporting, audit documentation, and risk-based controls.[4][5][3]

## Module 1: KPI Monitoring and Alerting Dashboard
## Functional Requirements
### FR-D01 — KPI Metrics Display
The dashboard must display the following AML operational KPIs in real time, updated at intervals not exceeding 60 seconds for live alert queues:[6][7][8][9]
Alert volume (total, by rule, by risk tier, by channel)
Alert-to-case conversion rate
False-positive rate and trend line
SAR/STR filing volume and status
Average case resolution time (time-to-close)
Queue backlog count and aging distribution
SLA compliance percentage per investigator and team
Customer risk tier breakdown (low, medium, high, PEP, sanctions)
KYC completion rate
Cost-per-case (computed from case count and team hour inputs)
### FR-D02 — Traffic-Light Indicators
Each KPI card must display a three-level traffic-light indicator (green, amber, red) against configurable thresholds, providing at-a-glance health status for the AML/CFT compliance officer and management. Threshold values must be configurable per role without requiring a code deployment.[9][6]
### FR-D03 — Alert Volume Charts
The dashboard must render time-series charts for alert volume, SAR filing volume, and false-positive rate across configurable rolling windows (24 h, 7 d, 30 d, 90 d). Charts must support zoom, pan, and data-point inspection, and must use ECharts or a comparable library capable of handling large time-series datasets.[8][10]
### FR-D04 — Tiered Alert Notification
The system must deliver automated notifications using a tiered strategy to prevent alert fatigue:[9]
**Critical** (high-risk, threshold-amount breach): immediate push notification and email to assigned compliance officer
**High** (SLA risk, escalation pending): in-app notification and email digest every 2 hours
**Medium** (routine monitoring pattern): aggregated daily digest
**Low / Informational**: visible in-portal only, no push
Each tier's threshold conditions must be configurable by compliance administrators.
### FR-D05 — Analyst Operational View
The dashboard must provide a dedicated operational view for transaction monitoring analysts showing alert volume, backlog, alerts resolved, alerts escalated, and a throughput trend, updated in real time. Managers must see aggregated team-level views.[10]
### FR-D06 — Rule and Scenario Performance
The dashboard must display per-rule performance metrics including: hit rate, false-positive rate, number of cases generated, and last modification timestamp. Rules with a false-positive rate above a configurable threshold must be highlighted automatically.[7]
### FR-D07 — Exportable Compliance Reports
Compliance officers must be able to export dashboard snapshots and metric summaries as PDF and CSV for board reporting, regulator inspection, and internal audit.[11][9]
### Frontend Requirements (Module 1)

| Requirement | Detail |
| --- | --- |
| Technology | Next.js App Router page, TanStack Query for polling/cache, ECharts for time-series |
| Refresh strategy | TanStack Query refetchInterval for live KPI cards; WebSocket or SSE for critical alert counters |
| Layout | KPI cards row → trend charts → alert queue summary table, following top-KPI-then-detail hierarchy |
| Responsive | Full-width at 1280px+; KPI cards stack vertically at ≤768px |
| Skeleton states | All KPI cards and charts must render shimmer skeletons during load |
| Accessibility | WCAG AA contrast, keyboard navigable, screen-reader labels on all chart elements |

### Backend Requirements (Module 1)

| Endpoint | Method | Description |
| --- | --- | --- |
| /dashboard/kpis | GET | Returns all current KPI values with computed traffic-light status |
| /dashboard/alerts/timeseries | GET | Returns alert volume time-series for a given window and granularity |
| /dashboard/rules/performance | GET | Returns per-rule hit rate, FP rate, case conversion |
| /dashboard/alerts/notifications | GET (SSE or WS) | Streams critical alert events to connected clients |
| /dashboard/export | POST | Generates PDF or CSV report snapshot |

## Module 2: Case Management
### Functional Requirements
### FR-C01 — Case Creation
Cases must be createable by two triggers:[12][2][13]
**Automatic**: an alert fired by the transaction monitoring rules engine, with case metadata pre-populated from the alert payload (entity, rule ID, alert severity, triggering transaction IDs)
**Manual**: an investigator or supervisor creates a case from the alert queue, a graph investigation, or a scheduled review
### FR-C02 — Case Lifecycle Workflow
Each case must follow a defined lifecycle with configurable stage transitions:[2][3]
NEW → TRIAGED → UNDER_INVESTIGATION → ESCALATED → CLOSED (cleared or SAR filed) or REOPENED
Workflow transitions must enforce role-based gate conditions (e.g., only a supervisor can approve escalation)
Stage durations must be tracked for SLA monitoring
### FR-C03 — Role-Based Access Control (RBAC)
The system must implement a role matrix with at minimum the following roles:[3][14]
**Analyst**: create, view, edit assigned cases; add notes; request escalation
**Supervisor**: view all team cases; approve/reject escalations; override dispositions
**QA Reviewer**: read-only access to closed cases for quality control auditing
**Compliance Officer (MLRO)**: view all cases; approve SAR filing; access board-level reporting
**Compliance Admin**: configure rules, thresholds, workflow stages, and user assignments
**System Admin**: manage users, roles, integrations, and audit log access
No role may exceed its defined permissions; privilege escalation must require MLRO or admin approval.[3]
### FR-C04 — Case Workspace
Each case must have a workspace containing:[13][12][2]
Case summary (entity, risk score, alerts linked, assigned investigator, status, age)
Transaction evidence viewer (linked transactions with amounts, timestamps, counterparties)
Graph investigation panel (embedded Cytoscape.js fund-flow view for case entities)
Timeline of all case actions in chronological order
Notes and tagging with multi-investigator collaboration support
File attachment for supporting evidence (KYC documents, screenshots, external reports)
SAR/STR preparation form with regulatory template fields
### FR-C05 — SAR/STR Generation
The system must support generation of SAR (Suspicious Activity Reports) and STR (Suspicious Transaction Reports) pre-populated with case data, supporting jurisdiction-specific templates. Completed reports must be exportable in the format required by the relevant financial intelligence unit (FIU). Filing status and confirmation must be recorded in the case audit trail.[4][13]
### FR-C06 — Audit Trail and Chain of Custody
Every case action must be persisted as an immutable, append-only audit event including:[11][15][3]
Action type (create, edit, note, status change, file attach, SAR file, escalate, close)
Actor (user ID, role, IP address)
Timestamp (UTC, millisecond precision)
Before/after state for field changes
Rule version and model version in effect at time of alert
Approval workflow log and MLRO sign-off
Audit records must be stored in a tamper-evident log and must meet FATF, AMLD5/6, and EBA documentation requirements.[15][3]
### FR-C07 — SLA and KPI Tracking
The system must track per-case SLA targets and surface breaches in both the case workspace and the dashboard:[16][3]

| Priority | Response Target | Resolution Target |
| --- | --- | --- |
| Critical (P1) | 15 minutes | 4 hours (24/7) |
| High (P2) | 30 minutes | 8 hours (24/7) |
| Medium (P3) | 1 hour | 1 business day |
| Low (P4) | 2 hours | 2 business days |

### FR-C08 — Case Linking and Entity Resolution
Cases involving overlapping entities (shared account, device, customer, jurisdiction) must be surfaced as related cases and linkable into a case cluster for joint investigation. Entity resolution must allow analysts to merge or link entities across cases when duplicates are identified.[3]
### FR-C09 — Integration Points
The case management module must integrate via API with:[12][2]
Transaction monitoring rules engine (alert ingestion)
KYC/CDD provider (customer risk profile enrichment)
Sanctions and PEP screening API (entity screening at case open and on demand)
Graph investigation service (network subgraph for case entities)
Regulatory reporting system (SAR/STR export and submission confirmation)
### Frontend Requirements (Module 2)

| Requirement | Detail |
| --- | --- |
| Technology | Next.js, TanStack Table for case queues, React Hook Form + Zod for case forms and SAR templates |
| Case queue | Faceted filter sidebar (risk, status, rule, assignee, date); column-sortable TanStack Table; bulk disposition actions |
| Case workspace | Split-pane layout: left summary + evidence; right notes + timeline; full-screen graph investigation modal |
| Notifications | In-app toast for SLA breach, escalation, and assignment; SSE feed from backend |
| Optimistic updates | Case status and note additions must optimistically update before server confirmation |

### Backend Requirements (Module 2)

| Endpoint | Method | Description |
| --- | --- | --- |
| /cases | GET / POST | List cases with filters; create manual case |
| /cases/{id} | GET / PATCH / DELETE | Retrieve, update, or soft-delete a case |
| /cases/{id}/transitions | POST | Execute workflow state transition with role validation |
| /cases/{id}/notes | GET / POST | List or add case notes |
| /cases/{id}/attachments | GET / POST | List or upload case attachments |
| /cases/{id}/audit | GET | Retrieve immutable audit log for the case |
| /cases/{id}/sar | POST | Generate or submit SAR/STR document |
| /cases/{id}/graph | GET | Return Cytoscape-ready subgraph for case entities |
| /alerts | GET | List alerts with filtering and pagination |
| /alerts/{id}/case | POST | Convert alert to case |

## Module 3: Interactive Network Visualization (Fund Flow Analysis)
### Functional Requirements
### FR-G01 — Entity and Relationship Model
The graph visualization must represent AML-relevant entities and relationships:[17][18][19]
**Node types**: Account, Customer, Merchant, Device, Wallet, Transaction, Case
**Edge types**: SENT, RECEIVED, OWNS, CONTROLS, SHARES_DEVICE, SHARES_IP, LINKED_TO_CASE, INTERMEDIARY_FOR
Each node must display: entity ID, type label, risk score (color-coded), jurisdiction flag, KYC status indicator, and case count badge. Each edge must display: amount (or count for aggregated edges), direction, timestamp range, and suspicious flag.
### FR-G02 — Interactive Traversal
The investigation canvas must support:[20][18][19]
Seed-node selection by entity search or from a case workspace
Configurable hop expansion (1–4 hops, defaulting to 2) with expansion triggered by double-click or context menu
Shortest path trace between any two nodes
Circular flow detection highlighting (fund paths that return to the origin node)
Fan-in / fan-out view (entities sending to or receiving from many counterparties)
Collapse benign branches into a summary node
Filter by time window, amount threshold, currency, jurisdiction, edge type, and risk score
### FR-G03 — AML Pattern Highlighting
The system must programmatically highlight known typologies on the graph:[18][21][20]
**Structuring/Smurfing**: one node sending many sub-threshold transactions to multiple destinations (fan-out)
**Layering**: long chain of intermediate accounts with rapid successive transfers
**Integration**: funds converging from many sources into a single endpoint (fan-in)
**Round-tripping**: circular paths where funds return to the originating account or beneficial owner
**Hub/bridge account**: a node with unusually high betweenness centrality connecting otherwise disconnected clusters
Detected patterns must be marked with distinct visual indicators and listed in the investigation sidebar.
### FR-G04 — Graph Layout and Navigation
The canvas must support at minimum two layout modes:[22][23]
**Force-directed** (fCoSE) for relationship exploration
**Hierarchical / top-down** for fund-flow chain tracing
Navigation must support zoom (mouse scroll and pinch), pan (click-drag), fit-to-view, and full-screen mode. Large graphs must use progressive rendering and batched layout to maintain interactive response times (see Non-Functional Requirements).
### FR-G05 — Node and Edge Inspection
Clicking a node or edge must open a details panel without leaving the canvas, showing:[20]
Full entity attributes and risk history
Linked alerts and cases
Transaction list for the selected relationship (sorted by amount and date)
Option to "open in case" (create or link to a case from the node)
### FR-G06 — Graph Snapshot and Evidence Export
Analysts must be able to export the current visible graph as a PNG image or JSON elements file for inclusion in case evidence, SAR submissions, or regulatory reports.[11][20]
### Frontend Requirements (Module 3)

| Requirement | Detail |
| --- | --- |
| Technology | Cytoscape.js for graph rendering; React wrapper for event integration |
| Performance | Batch element addition via cy.batch(); cap default rendered elements at 1,000 (nodes + edges); use progressive expansion beyond that limit[23][24] |
| Layouts | fCoSE for force-directed; dagre for hierarchical; layout computed server-side for large subgraphs to shift CPU cost off the browser[23] |
| Edge aggregation | Multiple transactions between the same pair should render as one weighted edge with count and total amount, expandable on demand |
| Risk color coding | Node color encodes risk score: green (low), amber (medium), red (high), black (sanctioned/PEP) |
| Undo/redo | Canvas state changes (expand, collapse, filter) support undo/redo via an in-memory state stack |

### Backend Requirements (Module 3)

| Endpoint | Method | Description |
| --- | --- | --- |
| /graph/neighborhood/{entity_id} | GET | Returns 1–N hop subgraph centered on entity; ?depth=2 (max 3) |
| /graph/path | GET | Shortest path between from and to entity IDs within maxHops |
| /graph/case/{case_id} | GET | Full subgraph for all entities linked to a case |
| /graph/expand | POST | Expand from a set of seed nodes with time/amount/type filters |
| /graph/patterns/{entity_id} | GET | Returns detected AML patterns (structuring, layering, circular) for entity neighborhood |

All graph endpoints return Cytoscape-compatible elements JSON with nodes and edges arrays, plus a meta object with depth, truncation flag, pattern detections, and aggregate totals.
Apache AGE Cypher queries power path, neighborhood, and pattern endpoints. Regular PostgreSQL SQL handles aggregation, scoring, and filter pre-processing before graph traversal.[25][18][26]

## Module 4: ETL Pipeline (PostgreSQL Transaction DB + Apache AGE Graph Layer)
### Functional Requirements
### FR-E01 — Data Source Ingestion
The ETL pipeline must extract data from the following source types:[27][28][29]
**Real-time streaming**: Apache Kafka topics (core banking transaction events, payment authorizations, alert triggers)
**SWIFT and ISO 20022**: message parsing for MT/MX payment messages
**REST API polling**: KYC provider enrichment, sanctions/PEP list updates, adverse media feeds
**Batch file**: CSV, JSON, and XML files from core banking, ledger export, and historical migration
**CDC (Change Data Capture)**: incremental updates from source relational databases via Debezium or equivalent
### FR-E02 — Transformation and Enrichment
The transformation stage must:[28][30][27]
Normalize entity identifiers across sources (account number, IBAN, wallet address, national ID) into stable canonical entity IDs
Resolve duplicate and aliased entities using configurable match rules (exact, fuzzy, deterministic)
Enrich transactions with KYC/CDD risk scores, PEP status, sanctions flags, and jurisdiction codes
Parse and standardize date/time fields to UTC ISO 8601
Validate required fields against the AML data model schema (Party, AccountPartyLink, Transaction, Risk tables)[31][32]
Apply data quality checks with rejection and quarantine for records failing validation
Compute derived fields: transaction velocity indicators, peer-group deviation scores, running-balance snapshots
### FR-E03 — Load to PostgreSQL (Transaction Layer)
The load stage must write to PostgreSQL with the following guarantees:[1][33][34]
Idempotent upserts (no duplicate records on retry or redelivery)
Transactional writes per micro-batch with rollback on partial failure
Table partitioning by date on the Transaction table for query performance
Separate schemas for: core_banking, aml_staging, aml_clean, risk, case_management, audit
Retention policy hooks for regulatory data holds and GDPR erasure requests
### FR-E04 — Load to Apache AGE (Graph Exploration Layer)
After relational load, a graph projection job must mirror investigation-relevant entities and relationships into the aml_graph Apache AGE graph:[35][25][36]
**Upsert**** vertices** for: Account, Customer, Merchant, Device, Wallet, Case
**Upsert**** edges** for: SENT, RECEIVED, OWNS, CONTROLS, SHARES_DEVICE, LINKED_TO_CASE — with properties including amount, count, first_seen, last_seen, currency, risk_flag, transaction_ids
Incremental projection: only changed or new entities and relationships are projected per pipeline run, not full graph rebuild
Graph projection must run within the same PostgreSQL transaction as the relational load where atomicity is required, leveraging AGE's PostgreSQL-native transactional model[26]
### FR-E05 — Pipeline Orchestration
Pipeline orchestration must use Apache Airflow for DAG-based scheduling and dependency management, given its maturity for enterprise batch ETL and extensive community operator ecosystem. DAGs must be defined for:[37][38][39]
Real-time/micro-batch transaction ingestion (trigger: Kafka consumer)
Batch file processing (trigger: cron schedule or file arrival)
Sanctions/PEP list refresh (trigger: daily cron)
Graph projection job (trigger: completion of relational load DAG)
Data quality report generation (trigger: post-load)
Historical back-fill and reprocessing (trigger: manual or rule-change event)
### FR-E06 — Data Quality and Observability
The pipeline must:[30][28]
Report data quality metrics per pipeline run: record count, reject count, duplicate count, enrichment hit rate
Target ≥99% data quality accuracy per run, consistent with scalable ETL pipeline benchmarks in the literature[28]
Alert the data engineering team when quality falls below the 99% threshold or when a pipeline stage fails
Maintain pipeline lineage records mapping each output record to its source file, topic, and transformation version
Support on-demand reprocessing of specific time windows or message types via a Rerun Engine[27]
### FR-E07 — Schema and Graph Model
**Core Relational Tables (PostgreSQL)**

| Table | Key Columns | Partitioning |
| --- | --- | --- |
| party | party_id, name, type, risk_tier, kyc_status, jurisdiction | None |
| account | account_id, party_id, account_type, opened_date, status | None |
| account_party_link | account_id, party_id, role, start_date, end_date | None |
| transaction | tx_id, debit_account_id, credit_account_id, amount, currency, timestamp, channel, status | Range by month on timestamp |
| alert | alert_id, tx_id, rule_id, severity, score, status, created_at | None |
| case_entity | case_id, entity_id, entity_type, link_reason | None |
| audit_log | event_id, actor_id, action, entity_type, entity_id, before, after, timestamp | Range by month on timestamp |

#### Graph Schema (Apache AGE aml_graph)

### Frontend Requirements (Module 4)
The ETL module has a lightweight admin view inside the portal for operations staff:[1][27]
Pipeline run history table: status, run start/end, record counts, quality score, errors
Pipeline DAG viewer (read-only iframe or embedded Airflow UI link)
On-demand reprocessing trigger form
Data quality metric charts (quality score trend, reject count by source)
Alert configuration for quality threshold breaches
### Backend Requirements (Module 4)

| Endpoint | Method | Description |
| --- | --- | --- |
| /etl/runs | GET | List recent pipeline runs with status and quality metrics |
| /etl/runs/{id} | GET | Detail for a specific pipeline run |
| /etl/reprocess | POST | Trigger reprocessing of a time window or source |
| /etl/quality | GET | Current and historical quality metrics |
| /etl/graph/status | GET | Graph projection lag, last sync, vertex/edge counts |

## Non-Functional Requirements
### Performance

| Requirement | Target | Rationale |
| --- | --- | --- |
| Dashboard KPI load time | < 2 seconds for initial render | AML dashboards must support real-time risk monitoring without perceived lag[6][9] |
| API response time (p95) for read endpoints | < 500 ms | Consistent with sanctions screening API benchmarks[40] |
| Graph neighborhood query (2 hops, < 500 nodes) | < 1 second | Investigator productivity requires low-latency graph expansion[20] |
| Transaction ingestion throughput | ≥ 2.4 million records/hour | Benchmark from scalable ETL pipeline research on 850M-record datasets[28] |
| Streaming graph update lag | < 5 seconds from transaction arrival to AGE projection | Consistent with streaming ingestion latency targets in ETL literature[28] |
| Real-time scoring budget | ≤ 100 ms total per transaction, ML model ≤ 50 ms | Industry benchmark for payment authorization pipelines[41] |
| Cytoscape.js canvas render (1,000 elements) | < 3 seconds on average hardware | Cytoscape.js comfortably renders thousands of elements; complex styles and large viewports increase cost[22][23] |
| Case queue load (TanStack Table, 500 rows) | < 1 second | Dense investigator UI must not slow analyst throughput |

### Scalability
The system must scale horizontally to support a 10x increase in transaction volume without architectural changes to the core pipeline.[28][30]
The FastAPI backend must support stateless deployment with multiple replicas behind a load balancer.
The graph layer must support progressive subgraph expansion and server-side layout computation for graphs exceeding 1,000 elements to avoid browser-side performance degradation.[23][24]
Apache Airflow DAGs must support concurrent execution with configurable parallelism per DAG and task pool.
PostgreSQL must be deployed with read replicas for query-heavy analytics endpoints to isolate reporting load from transactional write paths.
### Availability and Reliability

| Requirement | Target |
| --- | --- |
| Core portal uptime | 99.95% (< 4.4 hours downtime annually) |
| Transaction ingestion pipeline | 99.9% (< 9 hours downtime annually) |
| Planned maintenance window | Maximum 2 hours per month, outside business hours |
| RTO (Recovery Time Objective) | < 1 hour for critical services |
| RPO (Recovery Point Objective) | < 15 minutes for transaction data |

Consistent with financial application uptime guidance requiring 99.99% for payment gateways and payment authorization pipelines.[42][41]
### Security

| Requirement | Detail |
| --- | --- |
| Transport encryption | TLS 1.2+ enforced for all API, UI, and database traffic[43][44] |
| Authentication | OAuth2 / OpenID Connect with JWT; MFA required for all users; managed via Keycloak[45][44] |
| Authorization | RBAC enforced at API layer before any database or graph operation; least-privilege database roles per service[46][3] |
| Session management | Token expiry ≤ 1 hour; refresh token rotation; revocation on logout[44] |
| Data at rest | AES-256 encryption for database volumes and file attachments[42] |
| Input validation | All API inputs validated with Pydantic at FastAPI layer; parameterized Cypher queries only (no string interpolation)[47][44] |
| Secret management | Credentials injected via environment variables or secrets manager (Vault / AWS Secrets Manager); no hardcoded credentials[48][44] |
| Rate limiting | Applied at API gateway level; per-IP and per-user limits to prevent brute force and API abuse[44] |
| CORS | Strict allowlist limited to portal frontend origin[44] |
| Security headers | HSTS, X-Content-Type-Options, X-Frame-Options, CSP enforced via FastAPI middleware[44] |
| Dependency scanning | Automated SBOM and vulnerability scanning in CI/CD pipeline |
| Penetration testing | Annual third-party penetration test; quarterly internal security review |

### Compliance and Data Governance
All audit log records must be immutable, append-only, and retained for a minimum of 7 years or as required by local regulation, whichever is longer.[11][3][15]
The system must support GDPR data subject access requests (DSAR) and the right to erasure for non-SAR-filed customer records, with legal hold overrides.[3]
Cross-border data transfer must comply with applicable data residency requirements; the system must support region-specific deployment configurations.[3]
The system must generate evidence sufficient to satisfy regulatory inspection under FATF Recommendation 20, AMLD5/6 Article 33, and the EBA AML/CFT risk-based supervision guidelines.[11][3]
Rule and model version metadata must be logged at the point of alert generation so historical dispositions remain explainable.[49][11]
### Maintainability and Observability
All services must emit structured JSON logs with correlation IDs spanning frontend request through backend service and database query.
Distributed tracing (OpenTelemetry) must be instrumented on all FastAPI routes and ETL pipeline stages.
Health check endpoints must be available on all services for load balancer and container orchestrator liveness and readiness probes.
Deployments must be automated via CI/CD with automated test gates; critical bug fixes must be deployable within 12 hours of identification.[42]
Graph query performance must be benchmarkable per endpoint, and slow-query logs (>500 ms) must be captured and alerted.
Cypher queries must be version-controlled and reviewed as part of the codebase rather than constructed at runtime.[47]
### Usability
The portal must support all modern browsers (Chrome, Edge, Firefox, Safari) at current and one prior major version.
The interface must follow WCAG 2.1 Level AA accessibility standards.
Analyst workflows (triage, investigate, note, close) must be completable without mouse-only interaction; full keyboard navigation must be supported.
The case management and dashboard modules must support responsive layout at tablet widths (768px+); graph investigation is desktop-only (1024px+) given the complexity of the canvas.
Investigators must be able to complete alert triage and disposition in under 3 minutes for straightforward alerts; the UX must support batch disposition for alert queues exceeding 100 items.

### Architecture Alignment Summary

| Module | Frontend Stack | Backend Stack | Database |
| --- | --- | --- | --- |
| KPI Dashboard | Next.js, TanStack Query, ECharts | FastAPI, Temporal (alert triggers), Redis (cache) | PostgreSQL (aggregated metrics), Redis |
| Case Management | Next.js, TanStack Table, React Hook Form + Zod | FastAPI, Temporal (workflow), Keycloak (RBAC) | PostgreSQL (cases, audit), OpenSearch (full-text) |
| Graph Visualization | Cytoscape.js, React, TanStack Query | FastAPI (graph routes), AGE query service | PostgreSQL + Apache AGE (aml_graph) |
| ETL Pipeline | Airflow admin view (portal iframe) | Apache Airflow DAGs, Python ETL services | PostgreSQL + Apache AGE (write targets) |

All modules share a common authentication boundary via Keycloak and a unified audit log service, ensuring that every user action across the portal is traceable, attributable, and regulatorily defensible.