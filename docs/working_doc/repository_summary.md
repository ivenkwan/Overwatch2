# Repository Statistical Summary - Overwatch Project

## Overview
This report provides a high-level statistical analysis of the **Overwatch** project, including codebase size, file distribution, and project composition.

---

## 📊 Core Statistics

| Metric | Value |
| :--- | :--- |
| **Total Files (Tracked)** | 87 |
| **Total Lines of Code (Source)** | ~4,968 lines |
| **Main Project Directory** | `aml_platform` |
| **Project Evolution** | Active refinement of AML typologies and graphs |

---

## 📂 File Extension Distribution
The repository primarily consists of Python (backend), TypeScript/React (frontend), and Markdown (documentation).

| Extension | Count | Description |
| :--- | :---: | :--- |
| `.py` | 19 | Python Backend, Services, and Utilities |
| `.md` | 18 | Documentation, Specs, Implementation Plans |
| `.tsx` | 10 | React Components with TypeScript |
| `.txt` | 9 | Logs, Dependency Requirements |
| `.svg` | 5 | Graphic Assets (UI) |
| `.sql` | 5 | Database Schemas and Initialization |
| `.json` | 3 | Project Configurations |
| `.ts` | 2 | Pure TypeScript Logic |
| `.dockerignore`| 2 | Deployment Configurations |
| (no ext) | 2 | Shell scripts/Config files |

---

## 📁 Directory Breakdown

### 🛠️ `aml_platform`
*The core of the application, encompassing both frontend and backend.*
- **Size:** ~586 MB
- **Est. Lines:** 11,391 (including data/logs)
- **Primary Tech:** React, FastAPI, PostgreSQL (Apache AGE), Cytoscape.js.

### 🔄 `etl`
*Data processing pipelines.*
- **Size:** 10.88 KB
- **Primary Tech:** Python, Docker, Dagster-like assets.

### 📄 `doc`
*System documentation and visuals.*
- **Size:** 168.17 KB
- **Content:** Architecture diagrams, system documentation, and walkthroughs.

---

## 📈 Key Insights
1. **Balanced Architecture:** Strong mix of backend logic (`.py`) and modern frontend components (`.tsx`).
2. **Dense Documentation:** 20% of files are Markdown, reflecting a well-documented system (Specs, Security scans, Implementation plans).
3. **Container-Ready:** Deployment is standardized via Docker and environment configurations.

> [!NOTE]
> The lines of code calculation focuses on source files (.py, .ts, .tsx, .sql, .md, .ps1, .yml). System logs and large binary files (Excel input data) are excluded from the LoC count but reflected in the disk size.
