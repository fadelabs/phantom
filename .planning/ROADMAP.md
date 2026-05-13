# Roadmap: Phantom

## Milestones

- **v1.0 Core Engine** — Phases 1-11.1 (shipped 2026-04-26)
- **v1.1 Product Launch** — Phases 12-14 (shipped 2026-05-12)
- **v1.2 Hardening & Processing** — Phases 17.1-24 (shipped 2026-05-13)
- **v1.3 Performance & Testing** — Phases 21-22, 25 (planned)
- **v2.0 Growth & Monetization** — Phases 15-16 (planned)

## Phases

<details>
<summary>v1.0 Core Engine (Phases 1-11.1) — SHIPPED 2026-04-26</summary>

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 1. Foundation & Audio I/O | 2/2 | Complete | 2026-04-25 |
| 2. Spectral & Loudness Analysis | 3/3 | Complete | 2026-04-25 |
| 3. Dynamics, Stereo & Phase Analysis | 4/4 | Complete | 2026-04-25 |
| 4. Problem Detection | 2/2 | Complete | 2026-04-25 |
| 5. Frequency Masking | 2/2 | Complete | 2026-04-25 |
| 6. Reference Profiles | 2/2 | Complete | 2026-04-25 |
| 7. Reference Comparison | 2/2 | Complete | 2026-04-25 |
| 8. Source Separation | 1/1 | Complete | 2026-04-25 |
| 9. MCP Server Integration | 2/2 | Complete | 2026-04-25 |
| 10. Domain Expert Skills Plugin | 4/4 | Complete | 2026-04-26 |
| 10.1 Typed Response Models | 5/5 | Complete | 2026-04-26 |
| 10.2 Input Security Hardening | 2/2 | Complete | 2026-04-26 |
| 11. Reaper DAW Integration | 3/3 | Complete | 2026-04-26 |
| 11.1 Type Completeness & Hardening | 3/3 | Complete | 2026-04-26 |

14 phases, 44 plans. Full details: [v1.0 archive](milestones/) (not formally archived — work predates milestone tracking)

</details>

<details>
<summary>v1.1 Product Launch (Phases 12-14) — SHIPPED 2026-05-12</summary>

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 12. CLI Tools | 4/4 | Complete | 2026-04-26 |
| 12.1 Live Integration Testing | 3/3 | Complete | 2026-04-26 |
| 13. Release Prep | 5/5 | Complete | 2026-04-26 |
| 13.1 Installer & Onboarding UX | - | Complete | 2026-05-12 |
| 14. Landing Page & Waitlist | - | Complete | 2026-05-12 |

5 phases, 12 tracked plans. Full details: [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

<details>
<summary>v1.2 Hardening & Processing (Phases 17.1-24) — SHIPPED 2026-05-13</summary>

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 17.1 Repo Safety Gates | 2/2 | Complete | 2026-05-13 |
| 18. Bug Fixes & UX | 3/3 | Complete | 2026-05-13 |
| 19. Tech Debt Cleanup | 2/2 | Complete | 2026-05-13 |
| 20. Security Hardening | 3/3 | Complete | 2026-05-13 |
| 23. Audio Processing & Auto-Fix | 3/3 | Complete | 2026-05-13 |
| 24. Overengineering Audit & Simplification | 5/5 | Complete | 2026-05-13 |

6 phases, 18 plans. Full details: [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)

</details>

### v1.3 — Performance & Testing

*Carried from v1.2 — these phases were planned but not started.*

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 21. Performance Optimization | 5/5 | Complete    | 2026-05-13 |
| 22. Testing & CI | 5/5 | Complete    | 2026-05-13 |
| 25. Skill Quality Optimization | 0/TBD | Not started | - |

### Phase 21: Performance Optimization

**Goal:** Eliminate duplicate FFT work, add payload size controls, add caching, and provide audio resampling utility
**Depends on:** None
**Sources:** CONCERNS.md (Performance), Backlog 999.3, 999.12, 999.13, 999.14

Items:
- Pre-compute power spectrum once in `detect_problems` and pass to frequency-domain detectors (999.13 + duplicate FFT concern)
- Add `top_n` parameter to `multi_stem_masking` to limit JSON payload size
- Analysis result caching for `compare_to_reference` (999.12)
- Shorten GCC-PHAT analysis window from 30s to 10s (999.14)
- Audio resampling utility for cross-file comparison (999.3)

**Plans:** 5/5 plans complete
Plans:
**Wave 1**
- [x] 21-01-PLAN.md — TDD: AnalysisCache class (thread-safe LRU with content hashing)
- [x] 21-02-PLAN.md — TDD: resample_to_match utility (polyphase FIR resampling)
- [x] 21-03-PLAN.md — TDD: FFT spectrum sharing in detect_problems
- [x] 21-04-PLAN.md — Env var helpers + GCC-PHAT window + top_n payload control

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 21-05-PLAN.md — Integration: wire cache into comparison.py, resample into phase/masking

### Phase 22: Testing & CI

**Goal:** Add GitHub Actions CI, expand test coverage for optional dependencies, long audio, error schemas, and plugin validation
**Depends on:** Phase 18 (bug fixes should land before new tests lock in behavior)
**Sources:** CONCERNS.md (Test Coverage Gaps, Tech Debt), Backlog 999.5-999.9, 999.16

Items:
- Add GitHub Actions CI workflow (ruff lint + format + pytest on Python 3.10/3.12)
- Conditional integration tests for Matchering, Demucs, Pedalboard when installed (999.6, 999.7)
- Long audio test fixture — 60s synthetic for `detect_problems` and `full_diagnostic` (999.8)
- Expanded error schema consistency tests across all 19 MCP tools (999.9)
- Plugin skill content validation — verify MCP tool name references are valid (999.16)
- Dependabot configuration for automated dependency updates

**Plans:** 5/5 plans complete
Plans:
**Wave 1** *(parallel)*
- [x] 22-01-PLAN.md — Test infrastructure: pytest-timeout, slow marker, 60s fixture
- [x] 22-02-PLAN.md — TDD: Error schema consistency tests (all MCP tools + wrap_errors coverage)
- [x] 22-03-PLAN.md — TDD: Plugin skill content validation (frontmatter, tool refs, domain semantics)

**Wave 2** *(depends on 22-01)*
- [x] 22-04-PLAN.md — Long audio duration tests + optional dependency integration tests

**Wave 3** *(depends on all above)*
- [x] 22-05-PLAN.md — GitHub Actions CI workflow + Dependabot configuration

### Phase 25: Skill Quality Optimization

**Goal:** Optimize all 5 domain expert skills (mix-engineer, mastering-engineer, effects-engineer, session-architect, audio-diagnostician) using autoresearch with LLM-judge scoring rubrics. Each skill gets a baseline score, iterative improvement passes, and a verified final score. Target: all skills scoring 80+ across their evaluation dimensions.
**Depends on:** None
**Sources:** `.autoresearch/runs/2026-05-02-audio-diag-bf64/report.md` (audio-diagnostician baseline: 55 → 84), `plugin/eval-workspaces/` (eval infrastructure for all 5 skills)

**Prior work:**
- audio-diagnostician: DONE (55 → 84, 2026-05-02)

**Remaining:**
- mix-engineer: not started
- mastering-engineer: not started
- effects-engineer: not started
- session-architect: not started

**Plans:** 0 plans
Plans:
- [ ] TBD (run /gsd-plan-phase 25 to break down)

---

### v2.0 — Growth & Monetization

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 15. Phantom Studio (Web Interface) | 0/TBD | Not started | - |
| 16. Marketing & Growth | 0/TBD | Not started | - |

### Phase 15: Phantom Studio (Web Interface)

**Goal:** Free browser-based web interface for visualizing Phantom analysis results — spectral curves, stereo field plots, loudness timelines, problem heatmaps. Upload-and-analyze without local installation. Optional paid Claude API token packages for AI-powered features (mixing advice, auto-fix suggestions).
**Requirements**: TBD
**Depends on:** Phase 14 (landing page with waitlist as entry point)

**Strategy notes (for planning):**
- Free to use — all analysis features available without payment
- Target audience: bedroom producers who want to upload a WAV and get a full diagnostic back, not engineers who run CLI tools
- Hosted API variant: upload WAV → full diagnostic JSON response
- Users can optionally buy token packages to power Claude-based features (AI mixing advice, guided fix suggestions)
- Revenue covers infrastructure/compute costs only — not feature access

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 15 to break down)

### Phase 16: Marketing & Growth

**Goal:** Content marketing and community building to drive adoption of Phantom — tutorials, community management, showcase real mixing workflows
**Requirements**: TBD
**Depends on:** Phase 14 (landing page), Phase 15 (Phantom Studio)

**Strategy notes (for planning):**
- Landing page positions Phantom as a product, not a personal brand
- Community: Discord or GitHub Discussions for user support, feature requests, profile sharing
- Content marketing: "AI-assisted mixing" tutorials using Phantom, demonstrating full analysis → fix workflows
- Everything is free — growth is about adoption and community, not conversion funnels

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 16 to break down)

### Non-blocking — Owner Tooling

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 11.5 Pedalboard Audio Processing | - | Absorbed into Phase 23 | - |
| 17. Content Authoring & Evaluation Tooling | 0/TBD | Not started | - |

### Phase 11.5: Pedalboard Audio Processing (INSERTED) — ABSORBED INTO PHASE 23

**Status:** Absorbed into Phase 23 (Audio Processing & Auto-Fix) in v1.2 milestone. Phase 23 expands the scope to include CLI auto-fix workflow and MCP tool, not just the library integration.

### Phase 17: Content Authoring & Evaluation Tooling

**Goal**: Owner-only tooling to spin up new genres, profiles, Reaper recipes, and skills in a consistent, quality-controlled way — using skill-creator for skills, templates for profiles/recipes, and evaluation pipelines to measure and improve quality across all content types
**Depends on**: Phase 10 (skills exist), Phase 11 (recipes exist), Phase 6 (profiles exist)
**Requirements**: TBD
**Success Criteria** (what must be TRUE):

1. Owner can generate a new genre profile from a template with consistent structure and validated fields
2. Owner can generate a new Reaper recipe from a template with trigger, undo safety, timing, and verification fields
3. Owner can create a new skill using skill-creator with eval scaffolding included
4. Evaluation pipeline exists for profiles (accuracy against real reference tracks), recipes (step correctness in Reaper), and skills (via skill-creator eval)
5. Owner can author real-world eval cases from reference audio and document expected outcomes
6. Owner can run evals against all content types and get a quality scorecard

**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 17 to break down)

## Backlog

Parking lot for tracked ideas. Numbered 999.x — not scheduled, promoted to phases when prioritized.

| # | Item | Source | Category |
|---|------|--------|----------|
| ~~999.1~~ | ~~CLI tools directory~~ → Promoted to **Phase 12** | CONCERNS.md | Feature |
| ~~999.2~~ | ~~Proper README with quickstart, installation, feature overview~~ → Covered by **Phase 11** + **Phase 13** | CONCERNS.md | Docs |
| ~~999.3~~ | ~~Audio resampling utility for cross-file comparison~~ → Promoted to **Phase 21** | CONCERNS.md | Feature |
| ~~999.5~~ | ~~Real audio integration test script~~ → Covered by **Phase 12.1** (live integration tests) | CONCERNS.md | Testing |
| ~~999.6~~ | ~~Conditional integration tests for Matchering~~ → Promoted to **Phase 22** | CONCERNS.md | Testing |
| ~~999.7~~ | ~~Conditional integration tests for Demucs~~ → Promoted to **Phase 22** | CONCERNS.md | Testing |
| ~~999.8~~ | ~~Long audio test fixture (60s synthetic)~~ → Promoted to **Phase 22** | CONCERNS.md | Testing |
| ~~999.9~~ | ~~Expanded error schema consistency tests~~ → Promoted to **Phase 22** | CONCERNS.md | Testing |
| ~~999.10~~ | ~~Extract magic number thresholds to constants~~ → Promoted to **Phase 19** | CONCERNS.md | Tech debt |
| ~~999.12~~ | ~~Analysis result caching for `compare_to_reference`~~ → Promoted to **Phase 21** | CONCERNS.md | Performance |
| ~~999.13~~ | ~~Pre-compute band energies in single multi-band pass~~ → Promoted to **Phase 21** | CONCERNS.md | Performance |
| ~~999.14~~ | ~~Shorten GCC-PHAT analysis window~~ → Promoted to **Phase 21** | CONCERNS.md | Performance |
| ~~999.15~~ | ~~Round values before Pydantic construction~~ → Promoted to **Phase 19** | CONCERNS.md | Performance |
| ~~999.16~~ | ~~Plugin skill content validation~~ → Promoted to **Phase 22** | CONCERNS.md | Testing |
| 999.4 | MCP progress reporting for long-running operations | CONCERNS.md | Feature |
| 999.11 | MCP server auth/rate limiting when HTTP transport is added | CONCERNS.md | Security |
| 999.17 | Server-side skill delivery — move 5 domain expert skills from plugin dir into MCP server. Significant architecture change requiring own phase. | discuss-phase 13.1 | Architecture |
