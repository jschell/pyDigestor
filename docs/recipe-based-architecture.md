# Recipe-Based Plugin Architecture

## Core Insight
A **recipe registry** separates routing logic (data) from implementation (code). Sites are configured, not coded.

---

## Component Separation

| Package | Purpose | Heavy Deps | Hook Implementations |
|---------|---------|------------|---------------------|
| **pydigestor** | Core orchestration, CLI, pipeline | None | Defines hookspecs |
| **pydigestor-feed** | RSS/Atom → URL list | feedparser | `discover_urls` |
| **pydigestor-web** | Intelligent router + recipes | httpx, newspaper3k | `can_handle`, `process_url` |
| **pydigestor-pdf** | PDF text extraction | pypdf/pdfplumber | `process_url` |
| **pydigestor-browser** | JS-heavy sites | playwright | `process_url` |

**Key**: Core never imports heavy deps. Plugins lazy-load their own.

---

## Recipe Registry Structure

**File**: `pydigestor_web/recipes.yaml`

```yaml
# Fallback for unknown sites
default:
  fetcher: httpx
  parser: newspaper

# Site-specific overrides
sites:
  arxiv.org:
    fetcher: httpx
    parser: pdf
    url_transform: "https://arxiv.org/pdf/{arxiv_id}.pdf"
    options:
      extract_metadata: true
      clean_latex: true

  wsj.com:
    fetcher: playwright  # Paywall/JS-heavy
    parser: newspaper
    options:
      wait_for: "article"
      timeout: 30000

  github.com:
    fetcher: api
    parser: github_markdown
    options:
      token: ${GITHUB_TOKEN}  # Env var injection

  medium.com:
    fetcher: httpx
    parser: newspaper
    options:
      headers:
        Cookie: "key=value"
    url_transform: "https://medium.com/m/global-identity-2?redirectUrl={url}"
```

**Benefits**:
- Add new sites without code changes
- Users override via local `~/.config/pydigestor/recipes.yaml`
- Version-controlled defaults in plugin

---

## Multi-Stage Pipeline

### Hook Specifications

**File**: `pydigestor/hookspecs.py`

```python
@hookspec
def discover_urls(source_url: str) -> list[str]:
    """Convert feed URL → article URLs"""

@hookspec
def can_handle(url: str) -> bool:
    """Check if plugin handles this URL"""

@hookspec
def process_url(url: str) -> ProcessedContent:
    """Fetch + parse content"""

@hookspec
def post_process(content: str, metadata: dict) -> str:
    """Site-specific cleanup (LaTeX, formatting)"""
```

### Execution Flow

```
Input: https://arxiv.org/rss/cs.AI

┌─────────────────────────────────────────┐
│ Stage 1: Discovery                      │
│ pm.hook.discover_urls(source_url)       │
│ → pydigestor-feed returns 50 URLs       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Stage 2: Routing (per URL)              │
│ pm.hook.can_handle(url)                 │
│ → pydigestor-web: Yes (http://)         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Stage 3: Processing                     │
│ pm.hook.process_url(url)                │
│ → web plugin checks recipes.yaml        │
│ → arxiv.org → parser: pdf               │
│ → Delegates to pydigestor-pdf           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Stage 4: Post-Processing                │
│ pm.hook.post_process(content, metadata) │
│ → Clean LaTeX: $ → "", \mathbf → ""     │
└─────────────────────────────────────────┘
              ↓
         Store in DB
```

---

## Plugin Implementation Examples

### pydigestor-web (Router)

**File**: `pydigestor_web/plugin.py`

```python
import pluggy
import yaml
from pathlib import Path

hookimpl = pluggy.HookimplMarker("pydigestor")

class WebPlugin:
    def __init__(self):
        self.recipes = self._load_recipes()

    @hookimpl
    def can_handle(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    @hookimpl
    def process_url(self, url: str):
        recipe = self._match_recipe(url)

        # 1. Fetch (lazy import based on recipe)
        html = self._fetch(url, recipe['fetcher'])

        # 2. Parse (lazy import based on recipe)
        return self._parse(html, recipe['parser'], recipe.get('options', {}))

    def _fetch(self, url, method):
        if method == "playwright":
            from .fetchers.playwright_fetcher import fetch
            return fetch(url)
        elif method == "httpx":
            from .fetchers.httpx_fetcher import fetch
            return fetch(url)
        # ... more fetchers

    def _match_recipe(self, url):
        domain = extract_domain(url)
        return self.recipes['sites'].get(domain, self.recipes['default'])
```

**Directory**:
```
pydigestor_web/
├── plugin.py
├── recipes.yaml
├── fetchers/
│   ├── httpx_fetcher.py
│   ├── playwright_fetcher.py
│   └── api_fetcher.py
└── parsers/
    ├── newspaper_parser.py
    ├── pdf_parser.py
    └── github_parser.py
```

### pydigestor-feed (Discovery)

**File**: `pydigestor_feed/plugin.py`

```python
import feedparser
import pluggy

hookimpl = pluggy.HookimplMarker("pydigestor")

@hookimpl
def discover_urls(source_url: str) -> list[str]:
    feed = feedparser.parse(source_url)
    if feed.entries:
        return [entry.link for entry in feed.entries]
    return []
```

### Post-Processing (Site-Specific Cleanup)

**File**: `pydigestor_web/post_processors.py`

```python
@hookimpl
def post_process(content: str, metadata: dict) -> str:
    url = metadata.get("url", "")

    # ArXiv LaTeX cleanup
    if "arxiv.org" in url:
        content = content.replace("$", "")
        content = re.sub(r"\\[a-z]+\{([^}]+)\}", r"\1", content)

    # Medium formatting cleanup
    if "medium.com" in url:
        content = content.replace("·", "-")

    return content
```

---

## Migration from Current pyDigestor

### Current State
- `extraction.py`: Monolithic with hardcoded patterns
- `PatternRegistry`: Priority-based handlers
- RSS/Reddit: Separate `sources/` modules

### Phase 1: Recipe Registry
1. Create `config/recipes.yaml` in core
2. Load recipes in `ExtractorRouter`
3. Keep existing handlers, route via recipes
4. **Result**: Config-driven without breaking changes

### Phase 2: Plugin Split
1. Extract `pydigestor_web` package
2. Move Playwright POC → `pydigestor_browser`
3. Move PDF handling → `pydigestor_pdf`
4. **Result**: Optional heavy dependencies

### Phase 3: Hookspecs
1. Define `discover_urls`, `can_handle`, `process_url`, `post_process`
2. Core orchestrates via `pm.hook.*`
3. **Result**: True plugin architecture

---

## User Experience Examples

### Basic RSS Processing
```bash
# Only needs pydigestor + pydigestor-feed
pip install pydigestor pydigestor-feed
pydigestor ingest --rss https://example.com/feed
```

### Add Browser Rendering
```bash
# Add playwright for JS-heavy sites
pip install pydigestor-browser
# Now WSJ, Twitter, SPAs work automatically
```

### Custom Site Recipe
```yaml
# ~/.config/pydigestor/recipes.yaml
sites:
  mycompany.com:
    fetcher: httpx
    parser: newspaper
    options:
      headers:
        Authorization: "Bearer ${API_TOKEN}"
```

---

## Key Advantages

1. **Lazy Loading**: Playwright only imported for sites that need it
2. **User Control**: Override any recipe locally
3. **Zero Code**: Add site support via YAML
4. **Testing**: Mock recipes for deterministic tests
5. **Composability**: Mix RSS (feed) + PDFs (arxiv) + JS (twitter) seamlessly

---

## Integration with Existing Code

**Current**: `ContentExtractor._extract_content()`
**Future**: `pm.hook.process_url(url)` → delegates to plugins via recipes

**Current**: `IngestStep.run()` loops over feeds
**Future**: `pm.hook.discover_urls()` → `pm.hook.process_url()` per result

**No Breaking Changes**: Keep existing API, add plugin layer underneath.
