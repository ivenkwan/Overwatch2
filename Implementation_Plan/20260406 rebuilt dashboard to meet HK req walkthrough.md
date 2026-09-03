# AML Dashboard Architecture (HKMA Compliance) - Walkthrough

The Overwatch AML platform's frontend has been fully restructured into a multi-module workspace supporting investigative workflows as mandated by the HKMA.

## What Was Changed

1. **SPA Unified Workspace Refactor**
   - We updated `src/app/page.tsx` with a dynamic **Left Sidebar Navigation** connecting to 6 separate HKMA-compliant investigation modules. 
   - The heavily graphical `GraphExplorer` widget now functions as a *persistent background layer*. Doing this prevents WebGL context loss or memory leaks that occur when unmounting complex `cytoscape.js` instances repeatedly, meaning users can seamlessly transition from text-heavy alert review screens to graph-based network visualisations instantly.

2. **Temporary Localized Data Models**
   - Defined robust, typed schemas in `src/types/models.ts` covering:
     - `Customer` (with CDD status, attributes, and source of wealth).
     - `Channel` (mapped SWIFT, Fiat, ERC-20, and general Wallet profiles).
     - `Payment` (typology tags and transaction timelines).
     - `Alert` / `Case` (investigator, timeline, explicitly documented rationale fields).
   - This checked off the requested To-Do item for localized components paving the way for eventual database API integration.

3. **Creation of HKMA Modules**
   - `MonitoringFeed.tsx`: Real-time transaction ingestion feed.
   - `AlertWorkbench.tsx`: Contextual screen comparing target entities and rule engine verdicts, featuring explicit disposition buttons to write explanations when closing alerts to satisfy regulatory oversight.
   - `CaseManagement.tsx`: Entity-centric workflow tracker grouping suspects and events, keeping track of maker-checker review status.
   - `STRPreparation.tsx`: JFIU-aligned template covering Digital Footprints and Transaction schedules for compliance reporting.
   - `ScreeningModule.tsx`: Side-by-side verification tool to resolve exact OFAC or internal hits.
   - `GovernanceMIS.tsx`: High-level metrics view aggregating Detection Quality, Efficiency, and False Positives.

## Testing & Validation

> [!TIP]
> The entire Next.js TypeScript compilation built completely cleanly with `0` warnings/errors, validating our new `src/types/models.ts` objects and routing paths!

The data forms the initial layout mapping matching the HKMA spec requested in `README.md`. As soon as the backend API endpoints for cases and alerts are stabilized, we can drop them into `models.ts` and fetch them through React Query.
