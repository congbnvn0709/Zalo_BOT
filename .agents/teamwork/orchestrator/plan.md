# Orchestration Plan: Zalo Attendance Web App & Excel Integrator

## Objective
Deliver a complete, high-quality, fully tested local Web application that:
1. Parses raw Zalo attendance messages (R1).
2. Provides an interactive Web UI for paste, preview, edit, upload/select template, and execute (R2).
3. Accurately reads and writes to Excel attendance sheets preserving formulas, formatting, and layout (R3).

## Phases
1. **Phase 0: Survey & Spec Mining**:
   - Spawn 3 Explorers / Spec Miners to analyze requirements, message parsing edge cases, Excel integration nuances, and web architecture.
   - Synthesize survey findings into `PROJECT.md` Feature Inventory & Architecture.
2. **Phase 1: Dual Track Decomposition**:
   - E2E Testing Track: Design test harness, runner, and test cases (Tiers 1-4).
   - Implementation Track:
     - M1: Parser module (clean regex/grammar, Vietnamese normalization, time calculation, food detection, syntax validation).
     - M2: Excel Integrator module (openpyxl/xlsx engine, formula preservation, fuzzy name matching, row/col mapping, cell updates).
     - M3: Web Dashboard (FastAPI/Flask backend + modern responsive frontend UI, upload/download, preview grid with inline edit).
3. **Phase 2: Execution & Gating**:
   - For each milestone: Explorer -> Worker -> Reviewers -> Challengers -> Auditor gate loop.
4. **Phase 3: Final E2E Pass (100%)**:
   - Run complete E2E suite against full integrated application.
5. **Phase 4: Adversarial Hardening (Tier 5)**:
   - Challenger-led adversarial testing.
6. **Phase 5: Victory Report**:
   - Deliver audited solution to parent Sentinel.
