# Plugin System

pyDigestor uses [pluggy](https://pluggy.readthedocs.io/) for a flexible plugin architecture that allows extending extraction capabilities without modifying core code.

## Overview

The plugin system enables:

- **Extensibility**: Add new extraction methods via plugins
- **Modularity**: Keep optional dependencies (like Playwright) separate
- **Zero Coupling**: Core works without any plugins installed
- **Easy Installation**: `pip install pydigestor-playwright`

## Architecture

### Hook Specifications

Hooks are defined in `src/pydigestor/hookspecs.py`:

```python
@hookspec
def register_extractors(registry):
    """Register custom content extraction patterns."""
```

### Plugin Discovery

Plugins register via setuptools entry points in `pyproject.toml`:

```toml
[project.entry-points.pydigestor]
plugin_name = "package.module"
```

### Plugin Loading

Plugins are automatically loaded when `ContentExtractor` is initialized:

```python
extractor = ContentExtractor()  # Loads all plugins automatically
```

## Available Hooks

### `register_extractors(registry)`

Register custom extraction patterns with the `PatternRegistry`.

**Parameters:**
- `registry` (PatternRegistry): Registry to add patterns to

**Example:**
```python
@hookimpl
def register_extractors(registry):
    from pydigestor.sources.extraction import ExtractionPattern

    def my_handler(url):
        content = extract_content(url)
        metadata = {"method": "my_extractor"}
        return content, metadata

    registry.register(ExtractionPattern(
        name="my_extractor",
        domains=["example.com"],
        handler=my_handler,
        priority=7
    ))
```

## Creating a Plugin

### 1. Package Structure

```
my-plugin/
├── pyproject.toml
├── README.md
└── my_plugin/
    ├── __init__.py
    └── extractor.py
```

### 2. Implement Hook

`my_plugin/__init__.py`:

```python
import pluggy
from .extractor import MyExtractor

hookimpl = pluggy.HookimplMarker("pydigestor")

@hookimpl
def register_extractors(registry):
    from pydigestor.sources.extraction import ExtractionPattern

    extractor = MyExtractor()

    registry.register(ExtractionPattern(
        name="my_extractor",
        domains=["example.com"],
        handler=extractor.extract,
        priority=7
    ))
```

### 3. Register Entry Point

`pyproject.toml`:

```toml
[project]
name = "pydigestor-my-plugin"
version = "0.1.0"
dependencies = ["pydigestor>=0.1.0"]

[project.entry-points.pydigestor]
my_plugin = "my_plugin"
```

### 4. Implement Extractor

`my_plugin/extractor.py`:

```python
class MyExtractor:
    def extract(self, url):
        """
        Extract content from URL.

        Args:
            url: URL to extract from

        Returns:
            Tuple of (content, metadata)
        """
        # Your extraction logic
        content = "extracted content"
        metadata = {
            "extraction_method": "my_extractor",
            "title": "Page Title",
            "error": None
        }
        return content, metadata
```

## Pattern Priority System

Patterns are matched in priority order (highest first):

| Priority | Usage | Examples |
|----------|-------|----------|
| 10 | File types | PDF extraction |
| 7 | Site-specific (plugins) | WSJ, Twitter, Medium |
| 5 | Site-specific (built-in) | GitHub, arXiv |
| 1 | Generic (config-driven) | Generic Playwright |
| 0 | Default fallback | trafilatura → newspaper3k |

**Rule**: Config overrides take precedence over all patterns.

## Official Plugins

### pydigestor-playwright

Enables JavaScript-heavy site extraction using browser automation.

**Installation:**
```bash
pip install pydigestor-playwright
playwright install chromium
```

**Supported Sites:**
- Wall Street Journal
- Twitter/X
- Medium
- Any JS-rendered site (via config)

**See:** [pydigestor-playwright/README.md](../pydigestor-playwright/README.md)

## Plugin Development Best Practices

### 1. Handler Signature

Always return `(content, metadata)`:

```python
def handler(url: str) -> Tuple[Optional[str], dict]:
    content = extract(url)
    metadata = {
        "extraction_method": "my_method",
        "title": None,
        "error": None
    }
    return content, metadata
```

### 2. Error Handling

Plugins should handle errors gracefully:

```python
def extract(self, url):
    try:
        content = self._extract(url)
        return content, {"error": None}
    except Exception as e:
        return None, {"error": str(e)}
```

### 3. Metadata Fields

Standard metadata fields:

```python
{
    "extraction_method": "plugin_name",  # Required
    "title": "Page Title",               # Optional
    "error": None,                       # None or error message
    "strategy": "strategy_name",         # Optional: which strategy used
    # Add custom fields as needed
}
```

### 4. Priority Selection

- **10**: File type detection (extensions, MIME types)
- **7-9**: High-confidence site-specific extraction
- **3-6**: Medium-confidence site patterns
- **1-2**: Generic/fallback extractors
- **0**: Reserved for core defaults

### 5. Testing

Include comprehensive tests:

```python
# Unit tests
def test_extractor_initialization():
    extractor = MyExtractor()
    assert extractor is not None

# Integration tests
def test_extract_real_content():
    extractor = MyExtractor()
    content, meta = extractor.extract("https://example.com")
    assert content is not None
    assert meta["error"] is None
```

### 6. Documentation

Include in your plugin README:

- Installation instructions
- Supported sites/use cases
- Configuration options
- Troubleshooting guide
- Performance characteristics

## Debugging Plugins

### List Loaded Plugins

```python
from pydigestor.plugins import get_plugin_manager

pm = get_plugin_manager()
plugins = pm.get_plugins()
print(f"Loaded {len(plugins)} plugins:")
for plugin in plugins:
    print(f"  - {plugin}")
```

### Test Pattern Matching

```python
from pydigestor.sources.extraction import ContentExtractor

extractor = ContentExtractor()

# Check what handler would be used
url = "https://example.com/article"
match = extractor.registry.get_handler(url)
if match:
    name, handler = match
    print(f"Handler: {name}")
else:
    print("No handler found")
```

### Verbose Plugin Loading

Plugin loading warnings are printed to console automatically.

## Configuration Integration

Plugins work seamlessly with site-specific configuration:

`~/.config/pydigestor/extractors.toml`:

```toml
# Override plugin defaults
[extraction.sites."wsj.com"]
method = "playwright_wsj"
timeout = 60

# Use plugin for additional sites
[extraction.sites."example.com"]
method = "playwright"  # Use generic Playwright handler
```

## Performance Considerations

### Plugin Overhead

- Plugin discovery: ~50ms (one-time on startup)
- Pattern matching: <1ms per URL
- Extraction time: Varies by plugin

### Optimization Tips

1. **Lazy Loading**: Only load heavy dependencies when needed
2. **Caching**: Cache browsers, sessions, or extracted data
3. **Async**: Use async for I/O-bound operations
4. **Fallback**: Implement fast-path fallbacks

## Troubleshooting

### Plugin Not Loading

**Check entry point:**
```bash
python -c "from importlib.metadata import entry_points; print([ep for ep in entry_points()['pydigestor']])"
```

**Verify installation:**
```bash
pip list | grep pydigestor
```

### Pattern Not Matching

**Check registry:**
```python
extractor = ContentExtractor()
patterns = extractor.registry.patterns
for p in patterns:
    print(f"{p.name}: {p.domains} (priority {p.priority})")
```

### Hook Not Called

**Verify hookimpl decorator:**
```python
import pydigestor_playwright
print(hasattr(pydigestor_playwright.register_extractors, '__self__'))
```

## Future Hooks (Planned)

Additional hooks under consideration:

- `configure_extractors(config)` - Plugin configuration
- `post_process_content(content, metadata)` - Content filtering
- `pre_extract(url)` - URL preprocessing
- `summarize_content(content)` - Custom summarization
- `classify_content(content, metadata)` - Custom classification

## Contributing

Want to add a new hook? See [CONTRIBUTING.md](../CONTRIBUTING.md).

## See Also

- [Playwright Plugin README](../pydigestor-playwright/README.md)
- [Configuration Guide](configuration.md)
- [Architecture Overview](architecture.md)
