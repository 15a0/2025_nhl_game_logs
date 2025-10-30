# NHL DFS Analytics - Development Backlog

**Last Updated**: October 28, 2025  
**Status**: Prototype Complete, Production Hardening In Progress

---

## Overview

This backlog tracks work items for moving from prototype to production-grade orchestrator. The prototype successfully validates the core data pipeline (assessment → fetch → aggregate → precalc), but needs robustness improvements before deployment.

---

## Backlog Items

### Phase 2: Error Handling & Reliability

#### P0 (Critical - Prevents Data Corruption)

**[P0-1] Transaction Wrapping for Aggregation**
- **Issue**: If aggregation crashes mid-process, team_game_stats has new data but team_aggregates is stale
- **Impact**: Precalc becomes unreliable; z-scores/TPI calculations use stale data
- **Solution**: Wrap aggregation in SQLite transaction; rollback on failure
- **File**: `src/orchestrator/fetcher_and_aggregator.py`
- **Effort**: 1-2 hours
- **Status**: Not Started

**[P0-2] Duplicate Prevention Before Fetch**
- **Issue**: Re-running script on same game_ids causes duplicate inserts (UNIQUE constraint prevents, but wastes API calls)
- **Impact**: Unnecessary API load; slower re-runs
- **Solution**: Query team_game_stats for existing game_ids before fetching
- **File**: `src/orchestrator/fetcher_and_aggregator.py`
- **Effort**: 30 minutes
- **Status**: Not Started

#### P1 (High - Improves Reliability)

**[P1-1] Retry Logic for API Failures**
- **Issue**: Single API failure (timeout, 500 error) crashes entire fetch job
- **Impact**: Must manually re-run; wastes time on partially completed work
- **Solution**: Retry with exponential backoff (3 attempts, 2s/5s/10s delays)
- **File**: `src/orchestrator/fetcher_and_aggregator.py`
- **Effort**: 2-3 hours
- **Status**: Not Started

**[P1-2] Comprehensive Error Logging**
- **Issue**: Current logging doesn't capture failure context (which game failed, why, what state is DB in)
- **Impact**: Hard to debug production issues
- **Solution**: Add structured logging (game_id, attempt, error type, DB state)
- **File**: `src/orchestrator/fetcher_and_aggregator.py`
- **Effort**: 1-2 hours
- **Status**: Not Started

#### P2 (Medium - Nice to Have)

**[P2-1] Resume/Checkpoint Mechanism**
- **Issue**: If script crashes on game 5 of 10, must re-fetch games 1-4 (wastes API calls)
- **Impact**: Inefficient for large batch runs (32 teams × 10+ games each)
- **Solution**: Track last successful game_id; allow resume from checkpoint
- **File**: `src/orchestrator/assessment.py`, `src/orchestrator/fetcher_and_aggregator.py`
- **Effort**: 3-4 hours
- **Status**: Not Started

**[P2-2] Partial Failure Reporting**
- **Issue**: If 8/10 games fetch successfully, unclear what happened to the 2 failures
- **Impact**: Operator doesn't know if precalc is complete or partial
- **Solution**: Summary report: "Fetched 8/10, failed: [game_ids], precalc updated with 8 games"
- **File**: `src/orchestrator/fetcher_and_aggregator.py`
- **Effort**: 1-2 hours
- **Status**: Not Started

---

### Phase 3: Orchestrator Expansion

#### P1 (High - Core Functionality)

**[P3-1] Multi-Team Orchestrator**
- **Issue**: Current prototype handles one team at a time; need to fetch all 32 teams in sequence
- **Impact**: Can't run nightly batch job for full season update
- **Solution**: Loop through all 32 teams, apply rate limiting between teams (not just games)
- **File**: New `src/orchestrator/orchestrator.py` (main entry point)
- **Effort**: 2-3 hours
- **Status**: Not Started

**[P3-2] Schedule Sync**
- **Issue**: `schedule.csv` is stale; need to fetch latest games from NHL API
- **Impact**: Assessment can't find new games if schedule isn't current
- **Solution**: Fetch schedule from NHL API before assessment (or cache with TTL)
- **File**: New `src/orchestrator/schedule_syncer.py`
- **Effort**: 2-3 hours
- **Status**: Not Started

#### P2 (Medium - Nice to Have)

**[P3-3] Configuration File Support**
- **Issue**: Hard-coded paths, delays, timeouts scattered in code
- **Impact**: Hard to adjust for different environments (test vs prod)
- **Solution**: Load from YAML config (db_path, rate_limit_delay, api_timeout, etc.)
- **File**: `config/orchestrator.yaml`, update all orchestrator modules
- **Effort**: 2-3 hours
- **Status**: Not Started

---

### Phase 4: Calculation Pipeline Integration

#### P1 (High - Completes Pipeline)

**[P4-1] Z-Score Calculation from Precalc**
- **Issue**: Precalc is built, but z-scores still use old manual Excel approach
- **Impact**: TPI/GOI calculations are manual; can't automate nightly runs
- **Solution**: Integrate `src/zscore_calculator.py` to read from team_aggregates
- **File**: `src/zscore_calculator.py`, `src/orchestrator/orchestrator.py`
- **Effort**: 2-3 hours
- **Status**: Not Started

**[P4-2] TPI Calculation from Z-Scores**
- **Issue**: TPI rankings still manual
- **Impact**: Can't generate automated GOI rankings
- **Solution**: Integrate `src/tpi_calculator.py` into orchestrator pipeline
- **File**: `src/tpi_calculator.py`, `src/orchestrator/orchestrator.py`
- **Effort**: 1-2 hours
- **Status**: Not Started

**[P4-3] Slate GOI Generation**
- **Issue**: GOI module exists but not integrated into orchestrator
- **Impact**: Can't generate daily slate recommendations automatically
- **Solution**: Add GOI calculation step to orchestrator pipeline
- **File**: `src/goi/slate_goi_calculator.py`, `src/orchestrator/orchestrator.py`
- **Effort**: 1-2 hours
- **Status**: Not Started

---

### Phase 5: Deployment & Monitoring

#### P1 (High - Production Ready)

**[P5-1] Nightly Scheduler**
- **Issue**: Orchestrator is manual; need to run automatically each night
- **Impact**: Can't deploy to production without automation
- **Solution**: Add cron job (Linux) or Task Scheduler (Windows) entry point
- **File**: New `scripts/run_orchestrator_nightly.sh` or `.bat`
- **Effort**: 1-2 hours
- **Status**: Not Started

**[P5-2] Monitoring & Alerting**
- **Issue**: No way to know if nightly run succeeded or failed
- **Impact**: Silent failures; stale precalc goes unnoticed
- **Solution**: Email/Slack alerts on success/failure; log to centralized system
- **File**: New `src/orchestrator/notifier.py`
- **Effort**: 2-3 hours
- **Status**: Not Started

#### P2 (Medium - Nice to Have)

**[P5-3] Health Check Dashboard**
- **Issue**: No visibility into pipeline health (last run time, data freshness, error rate)
- **Impact**: Operator doesn't know system status at a glance
- **Solution**: Simple HTML dashboard showing last run, precalc age, error count
- **File**: New `src/orchestrator/dashboard.py`
- **Effort**: 4-6 hours
- **Status**: Not Started

---

## Completed Items ✅

### Prototype (October 28, 2025)

**[DONE] Assessment Module**
- Query precalc for last_game_id
- Load schedule.csv
- Identify unfetched games
- File: `src/orchestrator/assessment.py`

**[DONE] Raw Extractor**
- Extract raw counts from boxscore
- Extract raw counts from play-by-play
- Combine both sources
- File: `src/orchestrator/raw_extractor.py`

**[DONE] Fetcher & Aggregator**
- Fetch games from NHL API
- Store raw stats in team_game_stats
- Aggregate to team_aggregates (precalc)
- Rate limiting (2s delay + jitter)
- Clear logging
- File: `src/orchestrator/fetcher_and_aggregator.py`

**[DONE] Schema Redesign**
- Aligned team_game_stats and team_aggregates columns
- Changed from `_avg` to `_sum` (raw counts)
- Added last_game_id tracking
- File: `Data/test_nhl_stats.db`

**[DONE] Independent Validation**
- Prototype tested against FLA (10 games)
- Results match NHL.com season stats
- Corsi For: 628 ✅
- xGF: 30.15 ✅

---

## Priority Summary

| Priority | Count | Status | Est. Effort |
|----------|-------|--------|-------------|
| P0 (Critical) | 2 | Not Started | 2-3 hours |
| P1 (High) | 6 | Not Started | 10-15 hours |
| P2 (Medium) | 3 | Not Started | 6-10 hours |
| **Total** | **11** | **Prototype Done** | **~20-30 hours** |

---

## Next Steps

1. **Immediate** (This week):
   - [P0-1] Add transaction wrapping
   - [P0-2] Add duplicate check
   - Validate on test DB

2. **Short-term** (Next week):
   - [P1-1] Add retry logic
   - [P1-2] Improve error logging
   - [P3-1] Build multi-team orchestrator

3. **Medium-term** (2-3 weeks):
   - [P4-1] Integrate z-scores
   - [P4-2] Integrate TPI
   - [P4-3] Integrate GOI

4. **Long-term** (1 month):
   - [P5-1] Add nightly scheduler
   - [P5-2] Add monitoring/alerts
   - Deploy to production

---

## Notes

- **Prototype validates core logic**: Assessment → Fetch → Aggregate → Precalc ✅
- **Independent validation passed**: FLA stats match NHL.com ✅
- **Rate limiting implemented**: Respectful API usage ✅
- **Production hardening needed**: Error handling, transactions, retry logic
- **User background (sysadmin/ops)**: Naturally thinks about reliability; this backlog reflects that

---

## Questions?

Refer to:
- `docs/architecture_design_decisions.md` - Design rationale
- `USAGE_GUIDE.md` - How to run the prototype
- `PROJECT_SUMMARY.md` - High-level overview
