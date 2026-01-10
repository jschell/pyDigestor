# Single File Configuration Implementation Plan

## Overview

Implement site-specific configuration using a single TOML file with minimal complexity.

**File**: `~/.config/pydigestor/extractors.toml` (or project `config.toml`)

**Total implementation**: ~200 LOC, 5-6 hours

---

## Phase 1: Configuration Schema (1 hour)

### 1.1 Data Classes

**File**: `src/pydigestor/config/extractor_config.py` (new)

```python
"""Configuration for content extraction."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import tomli


@dataclass
class SiteOverride:
    """Site-specific extraction configuration."""
    method: str  # Extractor name to use
    fallback: list[str] = field(default_factory=list)
    timeout: Optional[int] = None
    priority: Optional[int] = None
    enabled: bool = True
    options: dict = field(default_factory=dict)


@dataclass
class ExtractionConfig:
    """Global extraction configuration."""
    default_method: str = "trafilatura"
    default_fallback: list[str] = field(default_factory=lambda: ["newspaper"])
    default_timeout: int = 30
    min_content_length: int = 100
    site_overrides: dict[str, SiteOverride] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "ExtractionConfig":
        """Load configuration from TOML file.

        Args:
            config_path: Path to config file. If None, uses default locations:
                1. ./config.toml (project config)
                2. ~/.config/pydigestor/extractors.toml (user config)

        Returns:
            ExtractionConfig instance with loaded settings
        """
        config = cls()  # Start with defaults

        # Try default locations
        if config_path is None:
            paths = [
                Path("config.toml"),
                Path.home() / ".config/pydigestor/extractors.toml"
            ]
        else:
            paths = [config_path]

        for path in paths:
            if path.exists():
                config._load_from_file(path)
                break

        return config

    def _load_from_file(self, path: Path):
        """Load and merge config from file."""
        with open(path, "rb") as f:
            data = tomli.load(f)

        if "extraction" not in data:
            return

        ext_config = data["extraction"]

        # Load defaults
        if "default" in ext_config:
            defaults = ext_config["default"]
            self.default_method = defaults.get("method", self.default_method)
            self.default_fallback = defaults.get("fallback", self.default_fallback)
            self.default_timeout = defaults.get("timeout", self.default_timeout)
            self.min_content_length = defaults.get("min_content_length", self.min_content_length)

        # Load site overrides
        if "sites" in ext_config:
            for pattern, override_data in ext_config["sites"].items():
                # Handle simple string format: "arxiv.org" = "pdf"
                if isinstance(override_data, str):
                    override_data = {"method": override_data}

                self.site_overrides[pattern] = SiteOverride(
                    method=override_data["method"],
                    fallback=override_data.get("fallback", []),
                    timeout=override_data.get("timeout"),
                    priority=override_data.get("priority"),
                    enabled=override_data.get("enabled", True),
                    options=override_data.get("options", {})
                )

    def get_override(self, url: str) -> Optional[SiteOverride]:
        """Find site override for URL.

        Args:
            url: URL to check

        Returns:
            SiteOverride if match found, None otherwise
        """
        from urllib.parse import urlparse
        import fnmatch

        domain = urlparse(url).netloc.lower().replace("www.", "")
        url_lower = url.lower()

        for pattern, override in self.site_overrides.items():
            if not override.enabled:
                continue

            # Extension pattern: "*.pdf"
            if pattern.startswith("*."):
                if url_lower.endswith(pattern[1:]):
                    return override

            # Glob pattern: "*.github.io"
            elif "*" in pattern:
                if fnmatch.fnmatch(domain, pattern):
                    return override

            # Exact domain match: "arxiv.org"
            elif pattern in domain or pattern in url_lower:
                return override

        return None
```

**~100 LOC**

### 1.2 Configuration Template

**File**: `src/pydigestor/config/extractors.toml.template` (new)

```toml
# pyDigestor Extractor Configuration
# Copy to ~/.config/pydigestor/extractors.toml to customize

[extraction.default]
# Primary extraction method (matches extractor names)
method = "trafilatura"

# Fallback chain if primary fails
fallback = ["newspaper"]

# Default timeout in seconds
timeout = 30

# Minimum content length to consider extraction successful
min_content_length = 100


# Site-specific overrides
[extraction.sites]

# Simple format: domain = "extractor_name"
# "arxiv.org" = "pdf"
# "github.com" = "github"

# Full configuration format:
# [extraction.sites."wsj.com"]
# method = "playwright"
# fallback = ["newspaper"]
# timeout = 60
# priority = 10
# enabled = true
# options = { wait_for = "article", headless = true }

# Examples (uncomment to use):

# Force PDF extraction for arXiv
# "arxiv.org" = "pdf"

# Use Playwright for JS-heavy sites
# [extraction.sites."twitter.com"]
# method = "playwright"
# fallback = ["newspaper"]
# timeout = 60

# Match by extension
# "*.pdf" = "pdf"

# Match by glob pattern
# "*.github.io" = "static_site"

# Disable extraction for specific domains
# [extraction.sites."spam-site.com"]
# enabled = false
```

**~50 lines**

---

## Phase 2: Registry Integration (2 hours)

### 2.1 Enhanced PatternRegistry

**File**: `src/pydigestor/sources/extraction.py` (modify)

```python
# Add imports at top
from ..config.extractor_config import ExtractionConfig, SiteOverride

class PatternRegistry:
    """Registry with config override support."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.patterns: list[ExtractionPattern] = []
        self.config = config or ExtractionConfig()

    def register(self, pattern: ExtractionPattern):
        """Add pattern to registry."""
        self.patterns.append(pattern)
        self.patterns.sort(key=lambda p: p.priority, reverse=True)

    def get_handler(self, url: str) -> tuple[str, Callable, list[str]]:
        """Find handler with fallback chain.

        Returns:
            (method_name, handler_callable, fallback_list)
        """
        # 1. Check config overrides FIRST (highest priority)
        override = self.config.get_override(url)
        if override:
            handler = self._find_handler_by_name(override.method)
            if handler:
                fallback = override.fallback or self.config.default_fallback
                return (override.method, handler, fallback)

        # 2. Check registered patterns (from plugins and built-ins)
        for pattern in self.patterns:
            if pattern.matches(url):
                fallback = self.config.default_fallback
                return (pattern.name, pattern.handler, fallback)

        # 3. Use default method
        default_handler = self._find_handler_by_name(self.config.default_method)
        if default_handler:
            return (self.config.default_method, default_handler, self.config.default_fallback)

        raise ValueError(f"No handler found for URL: {url}")

    def _find_handler_by_name(self, name: str) -> Optional[Callable]:
        """Find handler callable by extractor name."""
        for pattern in self.patterns:
            if pattern.name == name:
                return pattern.handler
        return None
```

**~40 LOC of changes**

### 2.2 Fallback Chain Execution

**File**: `src/pydigestor/sources/extraction.py` (modify)

```python
class ContentExtractor:
    def __init__(self, timeout: int = 10, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.failed_urls = set()

        # NEW: Load configuration
        self.config = ExtractionConfig.load()
        self.registry = PatternRegistry(config=self.config)

        # Register built-in patterns
        self._register_builtin_patterns()

        # NEW: Load plugins (will add in Phase 3)
        # from ..plugins import pm, load_plugins
        # load_plugins()
        # pm.hook.register_extractors(registry=self.registry)

    def _extract_content(self, url: str) -> tuple[str, dict]:
        """Extract content with fallback chain support."""
        try:
            method_name, handler, fallback_chain = self.registry.get_handler(url)
        except ValueError as e:
            return "", {"error": str(e)}

        # Try primary method
        content, meta = self._try_extraction(url, method_name, handler)
        if self._is_valid_content(content):
            return content, meta

        # Try fallback chain
        for fallback_name in fallback_chain:
            fallback_handler = self.registry._find_handler_by_name(fallback_name)
            if not fallback_handler:
                console.print(f"[yellow]Fallback '{fallback_name}' not found[/yellow]")
                continue

            content, meta = self._try_extraction(url, fallback_name, fallback_handler)
            if self._is_valid_content(content):
                meta["fallback_used"] = True
                meta["fallback_method"] = fallback_name
                return content, meta

        # All methods failed
        return "", {
            "error": "All extraction methods failed",
            "attempted_methods": [method_name] + fallback_chain
        }

    def _try_extraction(self, url: str, method_name: str, handler: Callable) -> tuple[str, dict]:
        """Try single extraction method."""
        try:
            # Get timeout from config override if exists
            timeout = self.config.default_timeout
            override = self.config.get_override(url)
            if override and override.timeout:
                timeout = override.timeout

            # Call handler (may need to pass options)
            content, meta = handler(url)
            meta["extraction_method"] = method_name
            return content, meta

        except Exception as e:
            console.print(f"[yellow]Method '{method_name}' failed: {e}[/yellow]")
            return "", {"error": str(e), "method": method_name}

    def _is_valid_content(self, content: str) -> bool:
        """Check if content meets minimum quality threshold."""
        min_length = self.config.min_content_length
        return len(content.strip()) > min_length
```

**~60 LOC of changes**

---

## Phase 3: CLI Integration (1 hour)

### 3.1 Config Initialization Command

**File**: `src/pydigestor/cli.py` (add command)

```python
@cli.command()
@click.option("--path", type=click.Path(), help="Custom config path")
def init_config(path: Optional[str]):
    """Initialize configuration file from template."""
    import shutil
    from pathlib import Path

    template = Path(__file__).parent / "config" / "extractors.toml.template"

    if path:
        dest = Path(path)
    else:
        dest = Path.home() / ".config/pydigestor/extractors.toml"

    # Create directory if needed
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        if not click.confirm(f"{dest} already exists. Overwrite?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    shutil.copy(template, dest)
    console.print(f"[green]Created config file: {dest}[/green]")
    console.print(f"Edit this file to customize extraction behavior.")
```

**~20 LOC**

### 3.2 Testing Command

**File**: `src/pydigestor/cli.py` (add command)

```python
@cli.command()
@click.argument("url")
@click.option("--extractor", help="Force specific extractor")
@click.option("--show-fallback/--no-fallback", default=True, help="Show fallback chain")
def test_extract(url: str, extractor: Optional[str], show_fallback: bool):
    """Test extraction methods for a URL."""
    from .sources.extraction import ContentExtractor

    console.print(f"[bold]Testing extraction for:[/bold] {url}")

    ext = ContentExtractor()

    # Show what would be used
    try:
        method, handler, fallback = ext.registry.get_handler(url)
        console.print(f"\n[bold]Primary method:[/bold] {method}")
        if show_fallback:
            console.print(f"[bold]Fallback chain:[/bold] {', '.join(fallback)}")
        console.print()
    except Exception as e:
        console.print(f"[red]Error finding handler: {e}[/red]")
        return

    # Try extraction
    content, meta = ext._extract_content(url)

    if content:
        console.print(f"[green]✓ Success[/green]")
        console.print(f"Method: {meta.get('extraction_method')}")
        console.print(f"Content length: {len(content)} chars")
        if meta.get("fallback_used"):
            console.print(f"[yellow]Used fallback: {meta['fallback_method']}[/yellow]")
    else:
        console.print(f"[red]✗ Failed[/red]")
        console.print(f"Error: {meta.get('error')}")
        console.print(f"Attempted: {meta.get('attempted_methods')}")
```

**~30 LOC**

### 3.3 Override Flags

**File**: `src/pydigestor/cli.py` (modify existing commands)

```python
@cli.command()
@click.option("--url", help="Single URL to ingest")
@click.option("--extractor", help="Force specific extractor (overrides config)")
@click.option("--timeout", type=int, help="Extraction timeout in seconds")
def ingest(url: Optional[str], extractor: Optional[str], timeout: Optional[int], ...):
    """Ingest content from feeds or URLs."""

    # Apply CLI overrides to config
    if extractor or timeout:
        from .sources.extraction import ContentExtractor
        ext = ContentExtractor()

        if url:
            # Create temporary override for this URL
            from urllib.parse import urlparse
            domain = urlparse(url).netloc

            if extractor:
                ext.config.site_overrides[domain] = SiteOverride(
                    method=extractor,
                    timeout=timeout
                )

    # ... rest of ingest logic
```

**~15 LOC of changes**

---

## Phase 4: Testing (1.5 hours)

### 4.1 Config Loading Tests

**File**: `tests/test_extractor_config.py` (new)

```python
"""Tests for extractor configuration."""

import tempfile
from pathlib import Path
import pytest

from pydigestor.config.extractor_config import ExtractionConfig, SiteOverride


def test_default_config():
    """Test default configuration values."""
    config = ExtractionConfig()
    assert config.default_method == "trafilatura"
    assert config.default_fallback == ["newspaper"]
    assert config.default_timeout == 30


def test_load_simple_override():
    """Test simple site override format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[extraction.sites]
"arxiv.org" = "pdf"
""")
        f.flush()

        config = ExtractionConfig.load(Path(f.name))
        assert "arxiv.org" in config.site_overrides
        assert config.site_overrides["arxiv.org"].method == "pdf"


def test_load_full_override():
    """Test full site override configuration."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[extraction.sites."wsj.com"]
method = "playwright"
fallback = ["newspaper", "trafilatura"]
timeout = 60
priority = 10
""")
        f.flush()

        config = ExtractionConfig.load(Path(f.name))
        override = config.site_overrides["wsj.com"]
        assert override.method == "playwright"
        assert override.fallback == ["newspaper", "trafilatura"]
        assert override.timeout == 60


def test_pattern_matching():
    """Test URL pattern matching."""
    config = ExtractionConfig()
    config.site_overrides = {
        "arxiv.org": SiteOverride(method="pdf"),
        "*.pdf": SiteOverride(method="pdf"),
        "*.github.io": SiteOverride(method="static"),
    }

    # Domain match
    assert config.get_override("https://arxiv.org/abs/123").method == "pdf"

    # Extension match
    assert config.get_override("https://example.com/file.pdf").method == "pdf"

    # Glob match
    assert config.get_override("https://user.github.io").method == "static"

    # No match
    assert config.get_override("https://example.com") is None


def test_disabled_override():
    """Test disabled site override."""
    config = ExtractionConfig()
    config.site_overrides = {
        "spam.com": SiteOverride(method="custom", enabled=False)
    }

    assert config.get_override("https://spam.com/page") is None
```

**~60 LOC**

### 4.2 Registry Integration Tests

**File**: `tests/test_pattern_registry.py` (new)

```python
"""Tests for PatternRegistry with config."""

import pytest
from pydigestor.sources.extraction import PatternRegistry, ExtractionPattern
from pydigestor.config.extractor_config import ExtractionConfig, SiteOverride


def test_config_override_priority():
    """Test that config overrides take priority over patterns."""
    config = ExtractionConfig()
    config.site_overrides = {
        "example.com": SiteOverride(method="custom")
    }

    registry = PatternRegistry(config=config)

    # Register a pattern for same domain
    def handler(url): return "content", {}
    registry.register(ExtractionPattern(
        name="builtin",
        domains=["example.com"],
        handler=handler,
        priority=5
    ))

    # Config should win
    method, _, _ = registry.get_handler("https://example.com/page")
    assert method == "custom"


def test_fallback_chain():
    """Test fallback chain from config."""
    config = ExtractionConfig()
    config.site_overrides = {
        "example.com": SiteOverride(
            method="primary",
            fallback=["backup1", "backup2"]
        )
    }

    registry = PatternRegistry(config=config)

    # Register handlers
    def handler(url): return "content", {}
    for name in ["primary", "backup1", "backup2"]:
        registry.register(ExtractionPattern(
            name=name,
            domains=[],
            handler=handler
        ))

    method, _, fallback = registry.get_handler("https://example.com/page")
    assert method == "primary"
    assert fallback == ["backup1", "backup2"]
```

**~40 LOC**

---

## Phase 5: Documentation (30 min)

### 5.1 User Guide

**File**: `docs/configuration.md` (new)

```markdown
# Configuration Guide

## Quick Start

Initialize configuration file:
```bash
pydigestor init-config
```

Edit `~/.config/pydigestor/extractors.toml`:
```toml
[extraction.sites]
"arxiv.org" = "pdf"
```

## Configuration Reference

### Default Settings

[extraction.default]
method = "trafilatura"        # Primary extractor
fallback = ["newspaper"]      # Fallback chain
timeout = 30                  # Timeout in seconds
min_content_length = 100      # Minimum valid content

### Site Overrides

Simple format:
[extraction.sites]
"domain.com" = "extractor_name"

Full format:
[extraction.sites."domain.com"]
method = "extractor_name"
fallback = ["backup1", "backup2"]
timeout = 60
priority = 10
enabled = true
options = { key = "value" }

### Pattern Matching

- Domain: "arxiv.org" matches arxiv.org
- Extension: "*.pdf" matches any .pdf URL
- Glob: "*.github.io" matches all github.io subdomains

## Examples

### Force PDF Extraction
[extraction.sites]
"arxiv.org" = "pdf"

### JS-Heavy Site with Fallback
[extraction.sites."wsj.com"]
method = "playwright"
fallback = ["newspaper"]
timeout = 60

### Disable Domain
[extraction.sites."spam-site.com"]
enabled = false

## CLI Overrides

Test extraction:
pydigestor test-extract URL

Force extractor:
pydigestor ingest --url URL --extractor playwright

Custom timeout:
pydigestor ingest --url URL --timeout 120
```

---

## Implementation Checklist

### Phase 1: Schema
- [ ] Create `src/pydigestor/config/extractor_config.py`
- [ ] Add `SiteOverride` dataclass
- [ ] Add `ExtractionConfig` dataclass with `load()` method
- [ ] Create `src/pydigestor/config/extractors.toml.template`
- [ ] Add `tomli` to dependencies

### Phase 2: Integration
- [ ] Modify `PatternRegistry.__init__()` to accept config
- [ ] Implement `PatternRegistry.get_handler()` with config precedence
- [ ] Add `PatternRegistry._find_handler_by_name()`
- [ ] Modify `ContentExtractor.__init__()` to load config
- [ ] Implement `ContentExtractor._extract_with_fallbacks()`
- [ ] Add `ContentExtractor._try_extraction()`
- [ ] Add `ContentExtractor._is_valid_content()`

### Phase 3: CLI
- [ ] Add `init-config` command
- [ ] Add `test-extract` command
- [ ] Add `--extractor` flag to ingest
- [ ] Add `--timeout` flag to ingest

### Phase 4: Testing
- [ ] Create `tests/test_extractor_config.py`
- [ ] Create `tests/test_pattern_registry.py`
- [ ] Test config loading
- [ ] Test pattern matching
- [ ] Test fallback chain
- [ ] Test CLI overrides

### Phase 5: Documentation
- [ ] Create `docs/configuration.md`
- [ ] Add examples to README
- [ ] Update CLI help text

---

## Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "tomli>=2.0.0; python_version < '3.11'",  # TOML parsing
]
```

Python 3.11+ has `tomllib` built-in, so conditional dependency.

---

## Success Criteria

✅ Users can override extractors via config file
✅ Config takes precedence over plugin defaults
✅ Fallback chains work automatically
✅ Pattern matching (domain, extension, glob) works
✅ CLI can override config for testing
✅ Zero breaking changes to existing code
✅ ~200 LOC total implementation
✅ Backward compatible (works without config file)

---

## Timeline

- **Day 1**: Phase 1 + Phase 2 (schema + integration) - 3 hours
- **Day 2**: Phase 3 + Phase 4 (CLI + testing) - 2.5 hours
- **Day 3**: Phase 5 + polish (docs + cleanup) - 30 min

**Total: 6 hours over 3 days**
