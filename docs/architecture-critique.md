# Architecture Critique: Recipe-Based Design

## Critical Issues

### 1. Recipe Registry = Configuration Hell
**Problem**: YAML recipes add a whole layer of complexity:
- Schema validation needed
- Parsing errors at runtime, not import time
- Two sources of truth (plugin metadata + user config)
- Merge semantics (default → plugin → user) get complicated fast
- Testing requires mocking config files

**Symptom of**: Trying to make routing "configurable" when simple code works fine.

**Cost**: ~200 LOC just for config loading, validation, merging. More for error handling.

---

### 2. Too Many Hooks
**Current proposal**: 4 hooks per request
```
discover_urls → can_handle → process_url → post_process
```

**Problems**:
- `can_handle` + recipes is redundant (recipes already encode routing)
- `post_process` as separate hook means state must be passed through
- `discover_urls` as plugin overkill (RSS is 50 lines with feedparser)

**Better**: 2 hooks
```
extract(url) → content
sources() → [urls]  # For RSS/Reddit/feeds
```

---

### 3. Over-Modularization
**Proposed**: 5 packages
```
pydigestor, -feed, -web, -pdf, -browser
```

**Reality check**:
- Managing 5 packages = 5 pyproject.toml, 5 release cycles, 5 test suites
- Dependency hell: which version of `-web` works with which `-pdf`?
- Users install piecemeal, hit version conflicts
- For a tool this size (~4K LOC), not justified

**Better**: 2 packages
```
pydigestor (core + lightweight extractors)
pydigestor-playwright (optional heavy dependency)
```

Everything else (PDF, RSS, newspaper) is light enough for core. Playwright is the *only* truly heavy dep.

---

### 4. Recipe Anti-Patterns

#### URL Transformation in Config
```yaml
url_transform: "https://arxiv.org/pdf/{arxiv_id}.pdf"
```
**Problem**: Business logic in configuration. Now you need a templating engine, variable extraction, error handling.

**Better**: Code in the arxiv extractor plugin.

#### Env Var Substitution
```yaml
token: ${GITHUB_TOKEN}
```
**Problem**: Now you're reinventing environment variable handling. What about escaping? Defaults? Validation?

**Better**: Extractors read env vars directly.

#### Fetcher Selection
```yaml
fetcher: playwright vs httpx vs api
```
**Problem**: The "web router" now needs to know about all possible fetchers. Tight coupling.

**Better**: Each extractor handles its own fetching strategy.

---

### 5. The "Intelligent Router" Is a God Object

**Pattern**: `pydigestor-web` loads recipes, matches domains, delegates to fetchers/parsers.

**Problem**: This plugin becomes the orchestrator. It needs to:
- Know about pdf, browser, newspaper parsers
- Import all fetchers
- Handle recipe matching edge cases
- Manage fallback chains

**Result**: Web plugin is as complex as the core. Defeats the purpose of modularization.

**Better**: Let extractors self-register their domains. Core does simple priority matching.

---

## Simpler Alternative

### One Hook Type: Extractors
```python
@hookimpl
def register_extractors(register):
    register(ArxivExtractor())
    register(GitHubExtractor())
```

### Extractor Interface
```python
class Extractor:
    domains: list[str]  # or patterns
    priority: int

    def can_handle(self, url: str) -> bool:
        return any(d in url for d in self.domains)

    def extract(self, url: str) -> Content:
        # Each extractor handles its own:
        # - Fetching (httpx, playwright, API)
        # - Parsing (pdf, html, json)
        # - Post-processing (LaTeX cleanup)
        ...
```

### Core Orchestration (50 LOC)
```python
extractors = pm.hook.register_extractors()
for url in urls:
    extractor = max(e for e in extractors if e.can_handle(url),
                    key=lambda x: x.priority)
    content = extractor.extract(url)
```

**No recipes. No router. No config files.**

---

## Keep Simple Config

**config.toml** (for user overrides only):
```toml
[extraction.overrides]
"arxiv.org" = "arxiv"  # Force this extractor
"*.pdf" = "pdf"

[extraction.fallback]
default = "newspaper"
```

**50 LOC to implement.** Optional. Defaults work without it.

---

## What Actually Needs Plugins

| Component | Plugin? | Why |
|-----------|---------|-----|
| **Playwright** | Yes | Heavy dependency, optional use case |
| **PDF** | No | pypdf is 2MB, always useful |
| **RSS** | No | feedparser is tiny, core feature |
| **Newspaper** | No | Already a dependency |
| **ArXiv/GitHub handlers** | Yes | Site-specific, users may not need |
| **Summarizers** | Yes | Different algorithms, LLM vs statistical |

**Package structure**:
```
pydigestor              # Core + PDF + RSS + basic HTML
pydigestor-playwright   # Browser rendering
pydigestor-sites        # GitHub, Medium, arXiv handlers (optional)
pydigestor-llm          # LLM-based summarization (optional)
```

---

## Migration Reality Check

**Current codebase**: 4K LOC, monolithic but working.

**Recipe proposal**: Add ~500 LOC for config loading, validation, merging, templating.

**Simpler approach**: Add ~200 LOC for pluggy hooks on existing extractors.

**Refactoring order**:
1. Extract existing handlers into classes (ArxivExtractor, etc.) - *no pluggy yet*
2. Add pluggy registration - *still works with existing code*
3. Move Playwright to optional plugin - *user-facing change*
4. Extract site-specific handlers to optional plugin - *optional improvement*

**Don't**: Start with 5 packages and YAML config.

---

## Bottom Line

**Over-engineered**:
- Recipe files
- Multi-stage pipelines
- 5+ packages
- URL templating in config

**Right-sized**:
- Pluggy for extractors (1 hook type)
- Simple priority matching in core
- 2-3 packages max
- Config only for user overrides

**Key principle**: *Add abstraction when you have 3+ implementations, not before.*

You have 1 Playwright POC. Don't architect for 10 plugins yet.
