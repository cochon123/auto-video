# Architecture Improvement Notes

## Summary of Completed Refactorizations (Phase 1 & 2)

### ✅ Phase 1: 0% Risk Changes (Completed)
- Moved `scripts/test_multi_agent.py` → `tests/test_multi_agent_integration.py`
- Removed duplicate `prompts/` directory at root
- Created `src/auto_video/domain/models.py` for shared domain models
- Updated `agents/contracts.py` as compatibility wrapper
- Updated `manifest/schema.py` to extend domain models
- **Status**: Committed - All tests passing

### ✅ Phase 2: Low Risk Changes (Completed)
- Created `core/providers/base.py` for StockProvider, VideoResult, ImageResult, Asset
- Moved base classes from `core/video.py` to `core/providers/base.py`
- Updated `core/video.py` to import and re-export for backwards compatibility
- Updated `providers/stock/` to use new imports
- **Status**: Committed - All tests passing

---

## Remaining Architecture Issues (Phase 3 & 4)

### 🔴 Critical Issues (High Priority)

#### 1. `core/video.py` Still Too Large (1155+ lines)
**Problem**: Contains `LocalAssetsManager` and `VideoComposer` with extensive FFmpeg logic

**Proposed Solution**:
```
core/
  video/
    __init__.py          # Re-exports
    local_manager.py      # LocalAssetsManager (move from video.py)
    composer.py           # VideoComposer (move from video.py)
  providers/
    base.py              # Already done
  ffmpeg/
    __init__.py
    effects.py           # FFmpeg effect utilities (Ken Burns, transitions, etc.)
```

**Risk**: 20-30% - Large refactoring, requires thorough testing
**Estimate**: 3-4 hours

#### 2. `providers/stock/__init__.py` Too Large (729+ lines)
**Problem**: `StockManager` does too much (search, download, conversion)

**Proposed Solution**:
```
providers/stock/
  __init__.py            # Thin wrapper, exports
  searcher.py           # StockSearcher (search logic)
  downloader.py         # StockDownloader (download logic)
  converter.py          # KenBurnsConverter (image to video conversion)
  manager.py            # StockManager (orchestrates above)
  base.py               # Already has MockStockProvider
```

**Risk**: 25-35% - Complex refactoring with state management
**Estimate**: 4-5 hours

#### 3. `core/pipeline.py` Too Large & Mixed Responsibilities
**Problem**: Orchestrates everything but mixes high-level and low-level logic

**Proposed Solution**:
```
core/
  pipeline.py            # High-level orchestration (200 lines)
  workflow/
    __init__.py
    script_generation.py # Script generation logic
    asset_resolution.py  # Asset planning and retrieval
    video_assembly.py    # Video assembly logic
```

**Risk**: 30-40% - Very complex, many dependencies
**Estimate**: 6-8 hours

### 🟡 Medium Priority Issues

#### 4. Duplicate Ken Burns Implementations
**Problem**: Ken Burns effect is implemented in 3 places:
- `core/video.py` (LocalAssetsManager)
- `core/video.py` (VideoComposer.create_ken_burns_effect)
- `providers/stock/__init__.py` (StockManager._create_ken_burns_video)

**Proposed Solution**:
Create `core/ffmpeg/effects.py` with `create_ken_burns_video()` utility function

**Risk**: 15-20% - Consolidation with API changes
**Estimate**: 2-3 hours

#### 5. Test Files Too Large
**Problem**:
- `tests/test_agents.py` (399+ lines)
- `tests/test_pipeline.py` (393+ lines)

**Proposed Solution**:
```
tests/
  agents/
    test_director.py
    test_scriptwriter.py
    test_visual_curator.py
    test_reviewer.py
    test_orchestrator.py
  core/
    test_pipeline_basic.py
    test_pipeline_workflow.py
    test_pipeline_assets.py
```

**Risk**: 0% - Just reorganizing existing tests
**Estimate**: 1-2 hours

### 🟢 Low Priority Issues

#### 6. AssetPlanner and StockManager Overlap
**Problem**: Both handle asset planning/retrieval with unclear boundaries

**Proposed Solution**: Clarify responsibilities:
- `AssetPlanner`: Plans what assets are needed (high-level)
- `StockManager`: Actually retrieves/downloads assets (low-level)

**Risk**: 10-15% - May require interface changes
**Estimate**: 2-3 hours

#### 7. Missing FFmpeg Abstraction Layer
**Problem**: FFmpeg commands scattered throughout codebase

**Proposed Solution**:
```
core/ffmpeg/
  __init__.py
  command.py            # FFmpeg command builder
  effects.py            # Effects (Ken Burns, transitions)
  utils.py              # Duration, dimensions, etc.
```

**Risk**: 20-25% - Large abstraction effort
**Estimate**: 5-6 hours

---

## Recommended Implementation Order

### Sprint 1 (Low hanging fruit):
1. Fix duplicate Ken Burns (#4) - 2-3 hours
2. Split test files (#5) - 1-2 hours

### Sprint 2 (Medium complexity):
3. Split `core/video.py` (#1) - 3-4 hours
4. Clarify AssetPlanner/StockManager (#6) - 2-3 hours

### Sprint 3 (High complexity):
5. Split `StockManager` (#2) - 4-5 hours
6. Add FFmpeg abstraction (#7) - 5-6 hours

### Sprint 4 (Most complex):
7. Split `core/pipeline.py` (#3) - 6-8 hours

**Total Estimated Time**: 23-31 hours

---

## Current State (Post Phase 2)

✅ **Completed**:
- Clean domain models in `domain/models.py`
- Base providers properly separated
- Backwards compatibility maintained
- All tests passing

⏸️ **Paused**:
- Large refactorizations (Phase 3) due to complexity/risk
- Test splitting (Phase 4) - low priority

📝 **Next Steps**:
1. Run full test suite to validate current state
2. Create detailed technical specs for Phase 3 items
3. Implement incrementally with proper testing at each step
4. Document deprecation warnings for major API changes

---

## Testing Strategy for Future Refactorizations

For each Phase 3 item:

1. **Before**: Write comprehensive tests for existing behavior
2. **During**: Refactor in small steps, running tests after each change
3. **After**: Add integration tests for new boundaries/interfaces
4. **Documentation**: Update all relevant docs and examples

---

## Notes

- Keep backwards compatibility wherever possible
- Use deprecation warnings for API changes
- Consider semantic versioning for breaking changes
- All refactorizations should maintain the existing public API
- Focus on improving internal architecture, not changing user-facing functionality
