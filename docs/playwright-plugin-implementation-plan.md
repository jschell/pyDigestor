# Playwright Plugin Implementation Plan

## Goal
Extract Playwright functionality into optional plugin without breaking existing code.

---

## Current State
- `ContentExtractor` uses `PatternRegistry` for site-specific handlers
- Playwright POC exists (`poc/playwright_enhanced_poc.py`) with multiple strategies
- No pluggy infrastructure yet

---

## Phase 1: Core Plugin Infrastructure (2-3 hours)

### 1.1 Define Hook Specification
**File**: `src/pydigestor/hookspecs.py`

```python
from pluggy import HookspecMarker

hookspec = HookspecMarker("pydigestor")

@hookspec
def register_extractors(registry):
    """Register extraction patterns with the pattern registry.

    Args:
        registry: PatternRegistry instance to register patterns with
    """
```

**That's it.** One hook. Simple.

### 1.2 Create Plugin Manager
**File**: `src/pydigestor/plugins.py`

```python
import pluggy
from . import hookspecs

pm = pluggy.PluginManager("pydigestor")
pm.add_hookspecs(hookspecs)

def load_plugins():
    """Load plugins via entry points."""
    pm.load_setuptools_entrypoints("pydigestor")
```

**~20 LOC total.**

### 1.3 Integrate with Existing Code
**File**: `src/pydigestor/sources/extraction.py`

```python
# Add at ContentExtractor.__init__
from ..plugins import pm, load_plugins

def __init__(self, ...):
    # ... existing code ...
    self.registry = PatternRegistry()

    # Register built-in patterns (existing code)
    self._register_builtin_patterns()

    # NEW: Load plugins
    load_plugins()
    pm.hook.register_extractors(registry=self.registry)
```

**Zero breaking changes.** If no plugins installed, behaves identically.

---

## Phase 2: Playwright Plugin Package (3-4 hours)

### 2.1 Package Structure
```
pydigestor-playwright/
├── pyproject.toml
├── README.md
└── pydigestor_playwright/
    ├── __init__.py          # Plugin registration
    ├── extractor.py         # PlaywrightExtractor class
    └── strategies.py        # Adaptive strategies from POC
```

### 2.2 Plugin Implementation
**File**: `pydigestor_playwright/__init__.py`

```python
import pluggy
from pydigestor.sources.extraction import ExtractionPattern
from .extractor import PlaywrightExtractor

hookimpl = pluggy.HookimplMarker("pydigestor")

@hookimpl
def register_extractors(registry):
    """Register Playwright-powered extraction patterns."""
    extractor = PlaywrightExtractor()

    # Register JS-heavy sites
    registry.register(ExtractionPattern(
        name="playwright",
        domains=[
            "wsj.com", "ft.com",           # Paywalls
            "twitter.com", "x.com",         # SPA
            "medium.com",                   # Conditional rendering
            # Add more as needed
        ],
        handler=extractor.extract,
        priority=8  # Higher than default extractors
    ))
```

**File**: `pydigestor_playwright/extractor.py`

```python
from playwright.sync_api import sync_playwright

class PlaywrightExtractor:
    """Extract content from JS-heavy sites using Playwright."""

    def __init__(self):
        self.timeout = 30000
        self._browser = None

    def extract(self, url: str) -> tuple[str, dict]:
        """Extract content using adaptive strategies.

        Returns:
            (content_text, metadata_dict)
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # Try adaptive strategies (from POC)
                return self._extract_with_strategies(page, url)
            finally:
                browser.close()

    def _extract_with_strategies(self, page, url):
        """Port logic from playwright_enhanced_poc.py."""
        # 1. Try basic approach
        # 2. Handle cookie banners
        # 3. Wait for dynamic content
        # 4. Fallback to full HTML
        ...
```

**Port POC code into production-ready class.** ~150 LOC.

### 2.3 Entry Point Declaration
**File**: `pyproject.toml`

```toml
[project]
name = "pydigestor-playwright"
version = "0.1.0"
dependencies = [
    "pydigestor>=0.1.0",
    "playwright>=1.40.0",
]

[project.entry-points.pydigestor]
playwright = "pydigestor_playwright"
```

---

## Phase 3: User Experience (1 hour)

### 3.1 Installation
```bash
# Core only (no Playwright)
pip install pydigestor

# With Playwright support
pip install pydigestor pydigestor-playwright
playwright install chromium
```

### 3.2 Behavior
**Without plugin**:
- WSJ/Twitter URLs use trafilatura/newspaper fallback
- Works, but gets less content

**With plugin**:
- Playwright automatically handles JS-heavy domains
- Transparent to user - just better extraction

### 3.3 Documentation
**README.md** in plugin:
```markdown
# pydigestor-playwright

Browser automation for JS-heavy websites.

## Supported Sites
- Wall Street Journal, Financial Times (paywalls)
- Twitter/X (SPA)
- Medium (conditional rendering)

## Installation
pip install pydigestor-playwright
playwright install chromium

## Usage
No code changes needed. Install and pydigestor automatically uses it.
```

---

## Phase 4: Testing (2 hours)

### 4.1 Core Tests
**File**: `tests/test_plugins.py`

```python
def test_plugin_loading():
    """Plugins load without errors."""
    load_plugins()
    assert pm.is_registered(...)

def test_no_plugins_fallback():
    """Works without plugins installed."""
    extractor = ContentExtractor()
    # Should still extract with built-in methods
```

### 4.2 Plugin Tests
**File**: `pydigestor-playwright/tests/test_extractor.py`

```python
def test_playwright_extraction():
    """Extracts JS-rendered content."""
    extractor = PlaywrightExtractor()
    content, meta = extractor.extract("https://example-spa.com")
    assert len(content) > 100

def test_cookie_consent_handling():
    """Handles cookie banners."""
    ...
```

---

## Phase 5: Migration Path (ongoing)

### 5.1 Built-in → Plugins
Move site-specific handlers to optional plugins later:

```
pydigestor-sites/
├── pydigestor_sites/
│   ├── github.py      # GitHub extractor
│   ├── arxiv.py       # arXiv PDF handling
│   └── medium.py      # Medium-specific logic
```

**Not needed immediately.** Only if these become heavy/complex.

### 5.2 Future Plugins
Users can create their own:

```python
# my_custom_extractor.py
@hookimpl
def register_extractors(registry):
    registry.register(ExtractionPattern(
        name="corporate_blog",
        domains=["company.com"],
        handler=my_handler,
        priority=10
    ))
```

```toml
# pyproject.toml
[project.entry-points.pydigestor]
custom = "my_custom_extractor"
```

---

## What We're NOT Doing

❌ Recipe YAML files
❌ Multiple hook types
❌ 5 separate packages
❌ URL templating in config
❌ "Intelligent router" god object
❌ Discovery/can_handle/process/post_process pipeline

**Keep it simple.**

---

## Configuration Integration

This plugin implementation works alongside the **single-file configuration system** documented in [`single-file-config-implementation.md`](./single-file-config-implementation.md).

### How They Work Together

**Plugin registers defaults**:
```python
# pydigestor_playwright/__init__.py
@hookimpl
def register_extractors(registry):
    registry.register(ExtractionPattern(
        name="playwright",
        domains=["wsj.com", "twitter.com"],  # Default domains
        handler=extractor.extract,
        priority=8
    ))
```

**User can override in config**:
```toml
# ~/.config/pydigestor/extractors.toml
[extraction.sites."twitter.com"]
method = "newspaper"  # Override plugin default
```

### Implementation Coordination

**Recommended order**:
1. **First**: Implement plugin infrastructure (this plan) - enables plugin ecosystem
2. **Then**: Implement configuration system (parallel track, see linked doc)
3. **Result**: Plugins provide defaults, config allows user overrides

**Dependencies**:
- Plugin system works **without** config (uses registered patterns)
- Config system works **without** plugins (uses built-in extractors)
- Together: Maximum flexibility

**See**: [`single-file-config-implementation.md`](./single-file-config-implementation.md) for complete configuration implementation details.

---

## Implementation Order

**Week 1**:
1. Add hookspecs (1 file, 20 LOC)
2. Add plugin manager (1 file, 30 LOC)
3. Integrate with ContentExtractor (5 LOC)
4. Test with no plugins installed

**Week 2**:
1. Create pydigestor-playwright package
2. Port POC code to extractor class
3. Add entry point
4. Test with plugin installed

**Week 3**:
1. Write tests
2. Documentation
3. Example in main README

---

## Success Criteria

✅ Core works without any plugins
✅ Installing playwright plugin adds capability transparently
✅ No breaking changes to existing API
✅ Simple for users (`pip install pydigestor-playwright`)
✅ Simple for plugin authors (20 LOC to register patterns)
✅ Total core changes: <100 LOC

---

## File Checklist

### Core Changes
- [ ] `src/pydigestor/hookspecs.py` (new, ~20 LOC)
- [ ] `src/pydigestor/plugins.py` (new, ~30 LOC)
- [ ] `src/pydigestor/sources/extraction.py` (modify, +5 LOC)
- [ ] `pyproject.toml` (add pluggy dependency)

### Plugin Package
- [ ] `pydigestor-playwright/pyproject.toml` (new)
- [ ] `pydigestor-playwright/pydigestor_playwright/__init__.py` (new, ~30 LOC)
- [ ] `pydigestor-playwright/pydigestor_playwright/extractor.py` (new, ~150 LOC)
- [ ] `pydigestor-playwright/pydigestor_playwright/strategies.py` (port from POC, ~100 LOC)
- [ ] `pydigestor-playwright/README.md` (new)
- [ ] `pydigestor-playwright/tests/` (new)

**Total new code: ~350 LOC across 2 packages.**

---

## Risk Mitigation

**Risk**: Plugin not found
**Mitigation**: Core works without it. Graceful degradation.

**Risk**: Playwright install complex
**Mitigation**: Clear docs. `playwright install` is standard.

**Risk**: Version conflicts
**Mitigation**: Use `pydigestor>=0.1.0` constraint. Semantic versioning.

**Risk**: Performance
**Mitigation**: Playwright only used for registered domains. Most URLs use fast path.

**Risk**: Breaking changes
**Mitigation**: Zero changes to public API. Internal refactor only.
