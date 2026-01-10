# Configuration File Organization: Cost/Complexity Analysis

## Option A: Single File (Proposed)

**Structure**:
```
~/.config/pydigestor/extractors.toml
```

```toml
[extraction.default]
method = "trafilatura"
fallback = ["newspaper"]

[extraction.sites]
"arxiv.org" = "pdf"
[extraction.sites."wsj.com"]
method = "playwright"
```

**Pros**:
- ✅ Single source of truth
- ✅ Easy to understand structure
- ✅ Standard TOML parsing (one call)
- ✅ Clear precedence (top to bottom)
- ✅ Simple to validate

**Cons**:
- ❌ Large file if many site configs (not realistic - most users have <10 overrides)
- ❌ Can't share individual site configs easily

**Implementation**:
```python
def load_config():
    config = tomli.load(open("extractors.toml", "rb"))
    return ExtractionConfig.from_dict(config["extraction"])
```
**~10 LOC**

---

## Option B: Multiple Files

**Structure**:
```
~/.config/pydigestor/
├── extractors.toml          # Default settings
└── sites/
    ├── arxiv.toml
    ├── wsj.toml
    └── twitter.toml
```

**Default file** (`extractors.toml`):
```toml
[extraction.default]
method = "trafilatura"
fallback = ["newspaper"]
timeout = 30
```

**Per-site file** (`sites/arxiv.toml`):
```toml
method = "pdf"
priority = 10
url_pattern = ["arxiv.org", "*.arxiv.org"]
```

**Pros**:
- ✅ Modular - one file per concern
- ✅ Shareable configs (copy arxiv.toml between machines)
- ✅ Plugin-distributed site configs (plugin installs site TOML)
- ✅ Clean git diffs (changing one site doesn't touch others)

**Cons**:
- ❌ More complex loading logic
- ❌ Directory management (create sites/, check existence)
- ❌ Merging multiple files
- ❌ Unclear precedence (which file wins?)
- ❌ Harder to see full picture

**Implementation**:
```python
def load_config():
    # Load default
    config = tomli.load(open("extractors.toml", "rb"))
    extraction_config = ExtractionConfig.from_dict(config["extraction"])

    # Load all site configs
    sites_dir = Path("~/.config/pydigestor/sites").expanduser()
    if sites_dir.exists():
        for site_file in sites_dir.glob("*.toml"):
            site_config = tomli.load(site_file.open("rb"))
            domain = site_file.stem  # filename = domain
            extraction_config.site_overrides[domain] = SiteConfig.from_dict(site_config)

    return extraction_config
```
**~30 LOC** (plus error handling, validation)

---

## Option C: Hybrid (Best of Both)

**Structure**:
```
~/.config/pydigestor/
├── extractors.toml          # User config (default + overrides)
└── sites/                   # Optional per-site configs
    ├── arxiv.toml           # Auto-loaded if present
    └── wsj.toml
```

**User workflow**:
- **Simple users**: Edit extractors.toml only
- **Power users**: Create sites/ for modular configs
- **Plugin authors**: Ship site configs in plugin that auto-install to sites/

**Loading precedence**:
```
1. CLI flags (--extractor)
2. sites/*.toml (per-site configs)
3. extractors.toml [extraction.sites]
4. extractors.toml [extraction.default]
5. Built-in defaults
```

**Implementation**:
```python
def load_config():
    config = ExtractionConfig()

    # Load base config
    if extractors_toml.exists():
        data = tomli.load(extractors_toml.open("rb"))
        config.update_from_dict(data.get("extraction", {}))

    # Load per-site configs (optional)
    sites_dir = config_dir / "sites"
    if sites_dir.exists():
        for site_file in sites_dir.glob("*.toml"):
            domain = site_file.stem
            site_data = tomli.load(site_file.open("rb"))
            config.site_overrides[domain] = SiteConfig.from_dict(site_data)

    return config
```
**~25 LOC** (manageable)

---

## Complexity Breakdown

| Aspect | Single File | Multiple Files | Hybrid |
|--------|-------------|----------------|--------|
| **Loading logic** | 10 LOC | 30 LOC | 25 LOC |
| **User mental model** | Simple | Moderate | Moderate |
| **Error handling** | 5 LOC | 15 LOC | 12 LOC |
| **Validation** | 10 LOC | 20 LOC | 15 LOC |
| **Merge conflicts** | None | Need merge strategy | Need merge strategy |
| **Testing** | 1 fixture | 3+ fixtures | 2 fixtures |
| **Documentation** | 1 page | 2 pages | 1.5 pages |
| **Total complexity** | **~25 LOC** | **~65 LOC** | **~50 LOC** |

---

## Real-World Usage Patterns

### Typical User (95%)
- Sets 0-3 site overrides
- Single file is perfect
- Never needs sites/ directory

### Power User (4%)
- Sets 10+ site overrides
- May benefit from modularity
- But single file still manageable (100 lines)

### Plugin Developer (1%)
- Wants to ship default site configs
- Multiple files enable this

---

## Plugin Distribution Use Case

**Problem**: pydigestor-playwright wants to ship default configs for WSJ, Twitter, etc.

### Single File Approach
Plugin can't easily inject into user's extractors.toml.

**Solution**: Plugin registers patterns via hookimpl (code, not config).
```python
@hookimpl
def register_extractors(registry):
    registry.register(ExtractionPattern(
        name="playwright",
        domains=["wsj.com", "twitter.com"],
        ...
    ))
```

**No config file needed.**

### Multiple Files Approach
Plugin installs site configs during install.

**pydigestor-playwright/setup.py**:
```python
data_files = [
    ("~/.config/pydigestor/sites", [
        "configs/wsj.toml",
        "configs/twitter.toml",
    ])
]
```

**Benefit**: Users can see/edit plugin defaults.

**Cost**: Installation complexity, file conflicts, user vs plugin config precedence.

---

## Recommendation

### Start with Single File (Option A)

**Why**:
- 15 LOC simpler (25 vs 50+)
- Matches user mental model
- Standard TOML best practices
- Sufficient for 95% of users

**When to add Multiple Files**:
- If users request it (YAGNI principle)
- If >20 site configs become common
- If plugin config distribution becomes important

**Migration path**:
- Start single file
- Add sites/ directory support later if needed
- Backward compatible (sites/ is optional)

---

## Alternative: Inline Site Configs in Plugins

**Instead of config files**, plugins provide defaults programmatically:

```python
# pydigestor_playwright/__init__.py
DEFAULT_SITES = {
    "wsj.com": {
        "timeout": 60,
        "wait_for": "article",
        "options": {"headless": True}
    },
    "twitter.com": {
        "timeout": 45,
        "wait_for": ".tweet"
    }
}

@hookimpl
def register_extractors(registry):
    for domain, opts in DEFAULT_SITES.items():
        registry.register(...)
```

**User overrides** in extractors.toml still work (config > plugin defaults).

**Benefit**: No file distribution. Defaults in code. Config for overrides only.

---

## Final Answer

**Complexity cost of multiple files**: +40 LOC, +1 hour implementation, +ongoing maintenance.

**Benefit**: Modularity, shareability, plugin distribution.

**Trade-off**: Not worth it initially. Add if needed.

**Best approach**:
1. Single file (extractors.toml)
2. Plugins register defaults via hookimpl
3. User config overrides plugin defaults
4. Add sites/ directory later if users demand it

**Keep it simple.**
