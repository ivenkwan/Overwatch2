<!-- converted from hk_aml_kpi_control_matrix.xlsx -->

## Sheet: Overview
|  | Hong Kong AML Monitoring KPI & Control Matrix |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  | Polished workbook for fiat and stablecoin AML operations aligned to HKMA monitoring/STR guidance and JFIU STREAMS 2 expectations. |  |  |  |  |  |  |
|  | Sheet | Description | Primary use | Link |  |  |  |
|  | Overview | Navigation and workbook context | Read me | Open |  |  |  |
|  | KPI_Matrix | KPI dictionary with formulas, thresholds and owners | Management MIS | Open |  |  |  |
|  | Control_Mapping | HKMA/JFIU control-to-screen matrix | Compliance traceability | Open |  |  |  |
|  | Wireframe | Dashboard wireframe and screen intent | Design blueprint | Open |  |  |  |
|  | Thresholds in this workbook are suggested internal management triggers, not regulatory numeric minima. HKMA expects institution-specific calibration based on risk profile, segmentation, product mix, and testing. |  |  |  |  |  |  |
|  | Sources: HKMA Guidance Paper on Transaction Monitoring, Screening and STR (2023); HKMA Insights on Optimisation of Transaction Monitoring Systems (2024); JFIU suspicion assessment and STREAMS 2 guidance. Generated: 2026-04-06 14:19 |  |  |  |  |  |  |
## Sheet: KPI_Matrix
|  | KPI Dictionary |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | KPI | Definition | Formula | Owner | Green | Amber | Red | Frequency | Source data | Rationale |
|  | Alert rate | Alerts per 1,000 active monitored relationships | (Alert Count / Active Relationships) x 1,000 | AML Monitoring | Baseline | >10% MoM variance | >20% MoM variance | Monthly | Alert count; active customers/accounts/wallets | Coverage and demand signal |
|  | Productive alert rate | Reviewed alerts escalated to case | Cases Opened / Reviewed Alerts | AML Monitoring Lead | >=10.0% | 5.0%-9.9% | <5.0% | Monthly | Case opens; reviewed alerts | Scenario usefulness |
|  | False positive rate | Reviewed alerts closed non-suspicious | Closed Non-Suspicious / Reviewed Alerts | TM Tuning Manager | <=90.0% | 90.1%-95.0% | >95.0% | Monthly | Alert dispositions | Efficiency and tuning |
|  | STR conversion rate | STRs filed over productive cases | STR Filed / Cases Closed Productive | MLRO | >=10.0% | 5.0%-9.9% | <5.0% | Monthly | STR count; productive cases | HKMA tuning KPI |
|  | First-review SLA | Alerts reviewed within internal SLA | Alerts Within SLA / Total Alerts | Operations Manager | >=95.0% | 90.0%-94.9% | <90.0% | Daily/Weekly | Workflow timestamps | Timeliness control |
|  | Backlog ageing | Open alerts past SLA | Open Alerts Over SLA / Open Alerts | Operations Manager | <=10.0% | 10.1%-20.0% | >20.0% | Daily/Weekly | Open queue ageing | Escalation trigger |
|  | Case cycle time | Average days from case open to disposition | Total Case Days / Cases Closed | Investigations Lead | <=10 | 11-20 | >20 | Monthly | Case timestamps | Investigation efficiency |
|  | STR timeliness | Days from suspicion formed to STR submission | Total STR Days / STR Filed | MLRO | <=3 | 4-5 | >5 | Weekly/Monthly | STR timestamps | As soon as practicable |
|  | STR completeness | STRs with all mandatory fields complete | Complete STRs / STR Filed | Quality Assurance | >=99.0% | 95.0%-98.9% | <95.0% | Monthly | QA checklist | Reporting quality |
|  | Digital footprint inclusion | Relevant STRs with cyber indicators included | Cyber STRs with Footprints / Relevant Cyber STRs | MLRO / FIU | >=90.0% | 80.0%-89.9% | <80.0% | Monthly | Case/STR fields | HKMA cyber context |
|  | Editable attachment rate | STRs with editable transaction annexures | Editable Annexures / STR Filed | FIU Manager | >=95.0% | 90.0%-94.9% | <90.0% | Monthly | STR package metadata | JFIU usability |
|  | Data quality exception rate | Failed critical data checks | Critical Data Failures / Critical Records | Data Governance | <=1.0% | 1.1%-3.0% | >3.0% | Daily/Weekly | Ingestion QC logs | Monitoring reliability |
|  | Scenario review coverage | Scenarios reviewed in period | Scenarios Reviewed / Active Scenarios | TM Tuning Manager | 100.0% annual | <100.0% annual | Material gap | Monthly/Quarterly | Scenario inventory | Periodic review |
|  | QA clearance defect rate | QA exceptions on alert closures | QA Exceptions / QA Sample | Quality Assurance | <=5.0% | 5.1%-10.0% | >10.0% | Monthly | QA review log | Decision quality |
|  | Screening false positive rate | Screening alerts cleared as false matches | False Screening Hits / Total Screening Hits | Screening Lead | Portfolio baseline | >10% above baseline | >20% above baseline | Monthly | Screening results | Name/wallet tuning |
## Sheet: Control_Mapping
|  | HKMA / JFIU Control-to-Screen Mapping |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
|  | Regulator | Regulatory expectation | Control objective | Screen / widget | Required fields or actions | Owner |
|  | HKMA | TM system should generate alerts or MIS reports | Detect suspicious patterns across fiat, stablecoin, and hybrid flows | Risk & Flow Overview; Alert Workbench | Scenario ID; timestamp; product/channel; fiat/stablecoin flag; score | AML Monitoring |
|  | HKMA | Alert review should assess background, purpose, profile, and rationale | Evidence-based closure or escalation | Alert Detail Panel | CDD profile; prior alerts; customer explanation; open-source checks; rationale | L1/L2 Investigations |
|  | HKMA | Segmentation, thresholds, and testing should be risk-based | Tune by product, segment, and typology | Governance & Tuning | Segment; threshold set; test result; approver; review date | TM Tuning Manager |
|  | HKMA | Data quality and lineage should be tested | Prevent bad-data-driven misses or false alerts | Data Issues Widget | Source system; failed field; exception volume; remediation owner | Data Governance |
|  | HKMA | Timelines, triage, and backlog escalation should be defined | Timely queue management | KPI Strip; Queue Ageing | Age bucket; owner; escalation status; committee flag | Operations Manager |
|  | HKMA | Independent QA of alert clearance | Validate analyst decision quality | Governance & Tuning | QA sample; exception type; analyst; remediation action | Quality Assurance |
|  | HKMA | Screening systems need current databases and handling logic | Manage sanctions/name/wallet list alerts | Screening & Exceptions | List source; update time; hit status; tuning notes | Screening Lead |
|  | HKMA | STRs should be accurate, complete, concise, and structured | Improve filing intelligence value | STR Drafting | Triggering factors; subject profile; transaction summary; conclusion | MLRO |
|  | HKMA | Digital footprints should be included where relevant and available | Capture cyber-enabled evidence | STR Drafting; Case Desk | IP; device ID; timestamp; geolocation; login channel | FIU / MLRO |
|  | HKMA | Attachments should supplement narrative and be editable where appropriate | Make annexures usable by JFIU | STR Drafting | Narrative text; editable CSV/XLS; attachment labels | FIU Manager |
|  | HKMA | Connected networks/common attributes should be reported where practicable | Show linked accounts, wallets, devices, counterparties | Case Desk Graph | Linked entities; common IP/device; prior STR refs | Investigations Lead |
|  | JFIU | SAFE approach: Screen, Ask, Find, Evaluate | Structured suspicion assessment | Alert Workflow | Indicator; customer question log; record review; evaluation | L1/L2 Investigations |
|  | JFIU | Report where knowledge or suspicion exists as soon as practicable | Avoid delayed STR filing | KPI Strip; STR Queue | Suspicion date; filing due clock; approval SLA | MLRO |
|  | JFIU | STREAMS 2 electronic submission for regulated entities | Submission readiness and control | STR Drafting | Submission channel; e-cert readiness; submission ref | MLRO / Compliance |
|  | JFIU | STR should include particulars, suspicious facts, reasons, and explanation if any | Base completeness of filing | STR Mandatory Fields Panel | Identity data; address; account/wallet; suspicious facts; explanation | FIU Analyst |
## Sheet: Wireframe
|  | Dashboard Wireframe |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
|  | Header: filters, legal entity, business line, segment, export MIS / committee pack |  |  |  |  |
|  | KPI strip: open alerts, alerts > SLA, open cases, pending STRs, STR conversion %, false positive %, data issues |  |  |  |  |
|  | Risk & Flow Overview: alert mix by fiat/stablecoin/hybrid, top typologies, corridor and stablecoin trend |  |  | Screening & Exceptions: sanctions/name hits, wallet blacklist hits, failed ingestion, model test exceptions |  |
|  | Alert Workbench: selected alert, customer profile, account + wallet activity, IP/device/geo, decision buttons |  |  | Case Desk: entity graph, linked accounts/wallets/devices, timeline, notes, approvals |  |
|  | STR Drafting: triggering factors, subject background, suspicious facts, digital footprints, editable annexure controls |  |  |  |  |
|  | Governance & Tuning: scenario effectiveness, threshold review due, backlog ageing, QA defect rate, committee log |  |  |  |  |