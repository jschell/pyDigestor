# Site-Specific Configuration Design

## Goal
Allow users to override default extraction behavior without modifying code.

---

## Configuration File

**Location**: `~/.config/pydigestor/extractors.toml` (or in project `config.toml`)

```toml
# Default extraction strategy
[extraction.default]
method = "trafilatura"
fallback = ["newspaper", "html2text"]
timeout = 30

# Site-specific overrides
[extraction.sites]

# Force specific extractor for domain
"arxiv.org" = "pdf"
"github.com" = "github"
"*.pdf" = "pdf"  # Pattern matching

# Full configuration for complex cases
[extraction.sites."wsj.com"]
method = "playwright"
fallback = ["newspaper"]
priority = 10
timeout = 60
options = { wait_for = "article", headless = true }

[extraction.sites."medium.com"]
method = "newspaper"
fallback = ["trafilatura"]
options = { browser_user_agent = "custom" }

[extraction.sites."twitter.com"]
method = "playwright"
enabled = false  # Disable extraction for this domain
```

---

## Implementation

### Configuration Schema

**File**: `src/pydigestor/config/extractor_config.py`

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ExtractorOverride:
    """Site-specific extraction configuration."""
    method: str  # Extractor name (matches pattern.name)
    fallback: list[str] = field(default_factory=list)
    priority: Optional[int] = None
    timeout: Optional[int] = None
    enabled: bool = True
    options: dict = field(default_factory=dict)

@dataclass
class ExtractionConfig:
    """Global extraction configuration."""
    default_method: str = "trafilatura"
    default_fallback: list[str] = field(default_factory=lambda: ["newspaper"])
    default_timeout: int = 30
    site_overrides: dict[str, ExtractorOverride] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[str] = None):
        """Load from TOML file."""
        if config_path and Path(config_path).exists():
            data = tomli.load(open(config_path, "rb"))
            return cls._from_dict(data.get("extraction", {}))
        return cls()  # Defaults
```

**~50 LOC total.**

---

## Integration with PatternRegistry

### Enhanced Registry

**File**: `src/pydigestor/sources/extraction.py`

```python
class PatternRegistry:
    """Registry with config override support."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.patterns: list[ExtractionPattern] = []
        self.config = config or ExtractionConfig()

    def get_handler(self, url: str) -> Optional[tuple[str, Callable, list[str]]]:
        """Find handler with fallback chain.

        Returns:
            (method_name, handler_func, fallback_list)
        """
        # 1. Check config overrides first
        override = self._check_config_override(url)
        if override:
            return override

        # 2. Fall back to registered patterns
        for pattern in self.patterns:
            if pattern.matches(url):
                fallback = self.config.default_fallback
                return (pattern.name, pattern.handler, fallback)

        # 3. Use default
        default = self._get_default_handler()
        return (self.config.default_method, default, self.config.default_fallback)

    def _check_config_override(self, url: str) -> Optional[tuple]:
        """Check site-specific overrides."""
        domain = self._extract_domain(url)

        for pattern, override in self.config.site_overrides.items():
            if not override.enabled:
                continue

            if self._matches_pattern(url, domain, pattern):
                handler = self._find_handler_by_name(override.method)
                if handler:
                    return (override.method, handler, override.fallback)

        return None

    def _matches_pattern(self, url: str, domain: str, pattern: str) -> bool:
        """Match domain or glob pattern."""
        if pattern.startswith("*."):  # Extension pattern
            return url.endswith(pattern[1:])
        elif "*" in pattern:  # Glob pattern
            return fnmatch.fnmatch(domain, pattern)
        else:  # Exact domain match
            return pattern in domain
```

**~80 LOC total.**

---

## Fallback Chain Execution

### ContentExtractor Enhancement

**File**: `src/pydigestor/sources/extraction.py`

```python
class ContentExtractor:
    def _extract_content(self, url: str) -> tuple[str, dict]:
        """Extract with fallback chain."""
        result = self.registry.get_handler(url)
        if not result:
            return self._default_extract(url)

        method_name, handler, fallback_chain = result

        # Try primary method
        try:
            content, meta = handler(url)
            if self._is_valid_content(content):
                meta["extraction_method"] = method_name
                return content, meta
        except Exception as e:
            console.print(f"[yellow]Primary method '{method_name}' failed: {e}[/yellow]")

        # Try fallback chain
        for fallback_name in fallback_chain:
            try:
                fallback_handler = self.registry._find_handler_by_name(fallback_name)
                if fallback_handler:
                    content, meta = fallback_handler(url)
                    if self._is_valid_content(content):
                        meta["extraction_method"] = fallback_name
                        meta["fallback_used"] = True
                        return content, meta
            except Exception as e:
                console.print(f"[yellow]Fallback '{fallback_name}' failed: {e}[/yellow]")

        # All methods failed
        return "", {"error": "All extraction methods failed"}

    def _is_valid_content(self, content: str) -> bool:
        """Check if content meets minimum quality."""
        return len(content.strip()) > 100
```

**~40 LOC total.**

---

## Pattern Matching Examples

### Simple Domain Override
```toml
[extraction.sites]
"arxiv.org" = "pdf"
```

**Result**: `https://arxiv.org/abs/2301.00001` → uses PDF extractor

---

### Extension Matching
```toml
[extraction.sites]
"*.pdf" = "pdf"
"*.doc" = "docx"
```

**Result**: Any PDF URL → pdf extractor

---

### Glob Patterns
```toml
[extraction.sites]
"*.github.io" = "static_site"
"docs.*.com" = "documentation"
```

**Result**: Flexible domain matching

---

### Full Configuration
```toml
[extraction.sites."wsj.com"]
method = "playwright"
fallback = ["newspaper", "trafilatura"]
priority = 10
timeout = 60
options = { wait_for = "article", screenshot = true }
```

**Result**: Complex behavior without code changes

---

### Disable Extraction
```toml
[extraction.sites."spam-site.com"]
enabled = false
```

**Result**: Skip URL entirely (for blocklists)

---

## Configuration Precedence

```
1. User config (~/.config/pydigestor/extractors.toml)
   ↓ (highest priority)
2. Project config (./config.toml [extraction.sites])
   ↓
3. Plugin-registered patterns (via hookimpl)
   ↓
4. Built-in patterns (GitHub, PDF, etc.)
   ↓
5. Default (trafilatura → newspaper)
   (lowest priority)
```

---

## Default Configuration Template

**File**: `src/pydigestor/config/extractors.toml.template`

```toml
# pyDigestor Extractor Configuration
# Copy to ~/.config/pydigestor/extractors.toml to customize

[extraction.default]
# Primary extraction method
method = "trafilatura"

# Fallback chain if primary fails
fallback = ["newspaper", "html2text"]

# Default timeout (seconds)
timeout = 30

# Minimum content length to consider valid
min_content_length = 100

# Site-specific overrides
[extraction.sites]

# Examples (uncomment to use):

# Force PDF extraction for arXiv
# "arxiv.org" = "pdf"

# Use Playwright for JS-heavy sites
# [extraction.sites."twitter.com"]
# method = "playwright"
# fallback = ["newspaper"]
# timeout = 60

# Disable problematic domains
# [extraction.sites."spam-site.com"]
# enabled = false
```

**Auto-copied on first run.**

---

## User Workflow

### 1. Discover Issue
```bash
$ pydigestor ingest --url https://example.com/article
Warning: Extraction failed for example.com (0 bytes)
```

### 2. Override in Config
```toml
[extraction.sites."example.com"]
method = "playwright"
fallback = ["newspaper"]
timeout = 60
```

### 3. Retry
```bash
$ pydigestor ingest --url https://example.com/article
Success: Extracted 2,456 bytes using playwright
```

**No code changes. No plugin development.**

---

## CLI Override Support

### Command-line Flags
```bash
# Force specific extractor
pydigestor ingest --url https://wsj.com/article --extractor playwright

# Override timeout
pydigestor ingest --url https://slow-site.com --timeout 120

# Disable fallback
pydigestor ingest --url https://example.com --no-fallback

# Test extraction methods
pydigestor test-extract https://example.com --try-all
```

**Useful for debugging.**

---

## Plugin Integration

### Plugins Register Defaults

**File**: `pydigestor_playwright/__init__.py`

```python
@hookimpl
def register_extractors(registry):
    """Register Playwright extractor with default domains."""
    extractor = PlaywrightExtractor()

    # These domains use playwright BY DEFAULT
    # Users can override in config
    default_domains = [
        "wsj.com", "ft.com",
        "twitter.com", "x.com",
        # ...
    ]

    registry.register(ExtractionPattern(
        name="playwright",
        domains=default_domains,
        handler=extractor.extract,
        priority=8
    ))
```

### Config Overrides Plugin Defaults

**User config**:
```toml
# Override playwright plugin default
[extraction.sites."twitter.com"]
method = "newspaper"  # Use newspaper instead of playwright
```

**Result**: User config wins. Plugin provides sensible defaults.

---

## Testing Configuration

### Config Fixture
```python
def test_site_override():
    config = ExtractionConfig(
        site_overrides={
            "example.com": ExtractorOverride(
                method="custom",
                fallback=["trafilatura"]
            )
        }
    )
    registry = PatternRegistry(config=config)
    method, handler, fallback = registry.get_handler("https://example.com/page")

    assert method == "custom"
    assert fallback == ["trafilatura"]
```

### Live Testing
```bash
# Test config without modifying production
pydigestor test-config --config ./test-extractors.toml
```

---

## Migration from Current Code

### Phase 1: Add Config Loading
```python
# ContentExtractor.__init__
config = ExtractionConfig.load()  # Load from default location
self.registry = PatternRegistry(config=config)
```

**No behavior change if no config file exists.**

### Phase 2: Add Fallback Chain
```python
# Replace single extraction with fallback chain
content, meta = self._extract_with_fallbacks(url)
```

**Graceful degradation.**

### Phase 3: Document Patterns
- User guide with examples
- Auto-generate config template
- CLI helper commands

---

## Implementation Effort

| Component | LOC | Time |
|-----------|-----|------|
| Config schema | ~50 | 1h |
| Registry enhancement | ~80 | 2h |
| Fallback chain logic | ~40 | 1h |
| Config loading | ~30 | 30m |
| CLI commands | ~40 | 1h |
| Tests | ~60 | 1h |
| Documentation | - | 1h |
| **Total** | **~300 LOC** | **7.5h** |

---

## What This Solves

✅ **User overrides without code**: Edit TOML file
✅ **Fallback chains**: Primary fails → try backup methods
✅ **Site-specific timeouts**: Some sites are slow
✅ **Pattern matching**: `*.pdf`, `*.github.io`, etc.
✅ **Disable extraction**: Blocklist spam domains
✅ **Debug extraction issues**: Try different methods via CLI
✅ **Plugin defaults + user overrides**: Best of both worlds

---

## What This Avoids

❌ **URL templating**: No `{arxiv_id}` parsing in config
❌ **Fetcher selection**: Each extractor handles its own fetching
❌ **Parser selection**: Each extractor handles its own parsing
❌ **Business logic in YAML**: Config is data, not code

**Keep config simple. Move complexity to extractor classes.**
