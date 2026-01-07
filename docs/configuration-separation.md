# Configuration Separation: Secrets vs Non-Secrets

## Overview

This guide explains how to separate secret configuration (API keys, credentials) from non-secret configuration (feed lists, application settings) in pyDigestor.

## Why Separate Configuration?

### Current Problem

Everything is in `.env`:
```bash
# Secrets mixed with settings
DATABASE_URL=sqlite:///./data/pydigestor.db
ANTHROPIC_API_KEY=sk-ant-secret-key
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]  # Not a secret!
REDDIT_SUBREDDITS=["netsec"]                     # Not a secret!
```

### Issues:
- ❌ Secrets accidentally committed to Git
- ❌ Hard to share configurations (must redact secrets)
- ❌ JSON arrays in environment variables (awkward)
- ❌ No comments or structure
- ❌ Hard to version control settings

### Solution

**Separate concerns:**
- `.env` → Secrets only (gitignored)
- `config.toml` / `config.yaml` / `config.py` → Non-secrets (version controlled)

---

## Categorizing Configuration

### **Secrets (`.env`)**

**Rule:** Would this cause a security issue if publicly visible?

- ✅ `DATABASE_URL` with credentials (e.g., postgres://user:password@...)
- ✅ `ANTHROPIC_API_KEY`
- ✅ Future: OAuth tokens, webhook secrets, encryption keys

### **Non-Secrets (`config.*`)**

**Rule:** Can this be safely version controlled and shared?

- ✅ Feed URLs (RSS feeds, Reddit subreddits)
- ✅ Application settings (timeouts, retries, log level)
- ✅ Feature flags (enable_triage, enable_extraction)
- ✅ Summarization settings (method, sentence counts)
- ✅ Content extraction settings
- ✅ Domain blocklists
- ✅ Model names (not API keys!)

---

## Approach Comparison

| Feature | TOML | YAML | Python Module | Keep .env |
|---------|------|------|---------------|-----------|
| **No dependencies** | ✅ (Python 3.11+) | ❌ (needs pyyaml) | ✅ | ✅ |
| **Human-friendly** | ✅ | ✅ | ⚠️ (for devs) | ⚠️ |
| **Comments** | ✅ | ✅ | ✅ | ✅ |
| **Type safety** | ⚠️ (via Pydantic) | ⚠️ (via Pydantic) | ✅ (native) | ❌ |
| **Nested structure** | ✅ | ✅ | ✅ | ❌ |
| **IDE support** | ✅ | ✅ | ✅✅ (autocomplete) | ⚠️ |
| **Lists/arrays** | ✅ Natural | ✅ Natural | ✅ Native Python | ⚠️ JSON strings |
| **Backward compat** | ✅ (.env override) | ✅ (.env override) | ✅ | ✅ |
| **Git-friendly** | ✅ | ✅ | ✅ | ❌ |
| **User-friendly** | ✅✅ | ✅✅ | ⚠️ | ⚠️ |

---

## Option 1: TOML (Recommended)

### Why TOML?

- ✅ **No dependencies** (built into Python 3.11+ via `tomllib`)
- ✅ **Human-friendly** syntax (like INI but better)
- ✅ **Native Python support** for parsing
- ✅ **Type-safe** with Pydantic validation
- ✅ **Comments** for documentation
- ✅ **Widely adopted** (Rust Cargo, Python pyproject.toml)

### File Structure

```
pyDigestor/
├── .env                    # Secrets (gitignored)
├── .env.example            # Template for secrets
├── config.toml            # Your configuration (gitignored)
├── config.example.toml    # Template (version controlled)
└── src/pydigestor/config.py
```

### Migration Steps

**1. Create `config.example.toml`** (already created above)

**2. Update `.gitignore`:**
```gitignore
# Secrets
.env

# User-specific configuration
config.toml
```

**3. Update `config.py`** (see `config-toml-example.py` above)

**4. Create user's `config.toml`:**
```bash
cp config.example.toml config.toml
# Edit config.toml with your settings
```

**5. Simplify `.env`:**
```bash
# Old .env (everything)
DATABASE_URL=sqlite:///./data/pydigestor.db
ANTHROPIC_API_KEY=sk-ant-...
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]
# ... 40+ more lines

# New .env (secrets only)
DATABASE_URL=sqlite:///./data/pydigestor.db
ANTHROPIC_API_KEY=sk-ant-...
```

**6. Backward compatibility:**

Environment variables **still override** TOML values:
```bash
# Override via environment
RSS_FEEDS='["https://custom.feed/rss"]' uv run pydigestor ingest
```

### Example `config.toml` Usage

```toml
[feeds]
rss_feeds = [
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/",
    "https://export.arxiv.org/rss/cs.CR",
]

reddit_subreddits = [
    "netsec",
    "blueteamsec",
    "purpleteamsec",
]

[reddit]
sort = "new"
limit = 100
max_age_hours = 24
min_score = 5  # Require at least 5 upvotes

[summarization]
auto_summarize = true
method = "lexrank"
min_sentences = 3
max_sentences = 8
```

**Benefits:**
- ✅ Comments explain each setting
- ✅ Natural syntax for lists (no JSON)
- ✅ Organized by category
- ✅ Version control friendly (can diff changes)
- ✅ Share configurations easily (no secrets to redact)

---

## Option 2: YAML

### Why YAML?

- ✅ **Very popular** (Kubernetes, Ansible, GitHub Actions)
- ✅ **Human-friendly** and concise
- ✅ **Great for nested structures**
- ⚠️ **Requires dependency** (`pip install pyyaml`)

### Setup

**1. Add dependency:**
```bash
uv add pyyaml
```

**2. Create `config.example.yaml`** (already created above)

**3. Update `config.py`:**

```python
import yaml
from pathlib import Path

class Settings(BaseSettings):
    def __init__(self, **kwargs):
        # Load from config.yaml if exists
        config_path = Path("config.yaml")
        yaml_data = {}

        if config_path.exists():
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f)
            yaml_data = self._flatten_yaml(yaml_config)

        merged_data = {**yaml_data, **kwargs}
        super().__init__(**merged_data)
```

### When to Use YAML

- ✅ You're already using YAML elsewhere (Docker Compose, CI/CD)
- ✅ You need very complex nested configurations
- ✅ Your team prefers YAML over TOML
- ❌ You want zero dependencies (use TOML instead)

---

## Option 3: Python Module

### Why Python Config?

- ✅ **Native Python** (no parsing)
- ✅ **Full type hints** (IDE autocomplete)
- ✅ **Can use logic** for derived values
- ✅ **Dataclasses** for structure
- ⚠️ **Less user-friendly** for non-developers

### Setup

**1. Create `config_defaults.py`** (see `config-python-example.py` above)

**2. Create `config_local.py` for user overrides:**
```python
"""User-specific configuration overrides."""

from config_defaults import Config, FeedsConfig

# Start with defaults
config = Config()

# Override specific settings
config.feeds = FeedsConfig(
    rss_feeds=[
        "https://krebsonsecurity.com/feed/",
        "https://www.schneier.com/feed/atom/",
        "https://export.arxiv.org/rss/cs.CR",
    ],
    reddit_subreddits=["netsec", "blueteamsec"],
)

config.summarization.method = "textrank"
config.reddit.min_score = 10
```

**3. Add to `.gitignore`:**
```gitignore
config_local.py
```

**4. Usage in code:**
```python
try:
    from config_local import config
except ImportError:
    from config_defaults import config

# Use config
print(config.feeds.rss_feeds)
```

### When to Use Python Config

- ✅ Developer-focused project (not for end users)
- ✅ Need complex logic in configuration
- ✅ Want IDE autocomplete and type checking
- ✅ Configuration is code (not data)
- ❌ Non-technical users need to configure (use TOML/YAML instead)

---

## Option 4: Keep Everything in .env (Not Recommended)

### When It's Acceptable

- ✅ Very small projects (< 10 settings)
- ✅ No team collaboration
- ✅ Short-lived prototypes
- ✅ You use Doppler/Vault for secret management

### Improvements if Staying with .env

**1. Better organization:**
```bash
# ========== SECRETS ==========
DATABASE_URL=sqlite:///./data/pydigestor.db
ANTHROPIC_API_KEY=sk-ant-...

# ========== FEED SOURCES ==========
RSS_FEEDS=["https://krebsonsecurity.com/feed/"]
REDDIT_SUBREDDITS=["netsec"]

# ========== REDDIT CONFIG ==========
REDDIT_SORT=new
REDDIT_LIMIT=100
# ...
```

**2. Use `.env.example` template:**
```bash
cp .env.example .env
# Add your secrets to .env
```

**3. Never commit `.env`:**
```gitignore
.env
.env.local
.env.*.local
```

---

## Migration Strategy

### Gradual Migration (Recommended)

**Phase 1: Dual support**
- Keep `.env` working (backward compatibility)
- Add `config.toml` support
- Document both approaches

**Phase 2: Encourage TOML**
- Update documentation to recommend TOML
- Provide migration script
- Keep `.env` as fallback

**Phase 3: Deprecate .env (optional)**
- Add warning when non-secrets in `.env`
- Eventually remove support for non-secrets in `.env`

### One-Time Migration Script

```python
#!/usr/bin/env python3
"""Migrate .env to config.toml + .env (secrets only)."""

import tomllib
from pathlib import Path

# Read current .env
env_path = Path(".env")
env_lines = env_path.read_text().splitlines()

secrets = []
config = {
    "feeds": {},
    "reddit": {},
    "summarization": {},
    "extraction": {},
    "features": {},
    "llm": {},
    "application": {},
}

for line in env_lines:
    if not line or line.startswith("#"):
        continue

    key, value = line.split("=", 1)

    # Secrets stay in .env
    if key in ["DATABASE_URL", "ANTHROPIC_API_KEY"]:
        secrets.append(line)
    # Everything else goes to config.toml
    else:
        # ... mapping logic ...
        pass

# Write new .env (secrets only)
env_path.write_text("\n".join(secrets))

# Write config.toml
# ... write TOML output ...
```

---

## Recommended Approach for pyDigestor

### **Use TOML** ✅

**Why:**
1. **No dependencies** (Python 3.11+ built-in)
2. **Human-friendly** for users
3. **Version control friendly**
4. **Natural list syntax** (no JSON in strings)
5. **Comments supported**
6. **Widely adopted** in Python ecosystem

### File Structure

```
pyDigestor/
├── .env                      # Secrets (DATABASE_URL, API keys)
├── .env.example              # Secret template
├── config.toml              # User configuration (gitignored)
├── config.example.toml      # Configuration template (version controlled)
├── src/pydigestor/config.py # Config loader
└── docs/
    └── configuration.md     # User guide
```

### `.gitignore` Updates

```gitignore
# Secrets
.env
.env.local
.env.*.local

# User-specific config
config.toml

# Keep templates
!.env.example
!config.example.toml
```

### User Experience

**Initial setup:**
```bash
# Copy templates
cp .env.example .env
cp config.example.toml config.toml

# Edit secrets
nano .env  # Add DATABASE_URL, API keys

# Edit configuration
nano config.toml  # Add feeds, adjust settings

# Run application
uv run pydigestor ingest
```

**Sharing configuration:**
```bash
# Share your config (no secrets!)
cp config.toml ~/my-pydigestor-config.toml

# Send to colleague
# They can use it directly (no redaction needed)
```

**Version control:**
```bash
# Commit configuration template
git add config.example.toml
git commit -m "Add arXiv feeds to config template"

# Your personal config.toml stays private (gitignored)
```

---

## Testing

Ensure both approaches work:

```python
# tests/test_config.py
def test_config_from_env():
    """Test loading from .env."""
    os.environ["RSS_FEEDS"] = '["https://test.com/feed"]'
    settings = Settings()
    assert settings.rss_feeds == ["https://test.com/feed"]

def test_config_from_toml():
    """Test loading from config.toml."""
    # Create temporary config.toml
    config_toml = Path("config.toml")
    config_toml.write_text("""
[feeds]
rss_feeds = ["https://toml.com/feed"]
    """)

    settings = Settings()
    assert settings.rss_feeds == ["https://toml.com/feed"]

    config_toml.unlink()

def test_env_overrides_toml():
    """Test that .env overrides config.toml."""
    # Create config.toml
    config_toml = Path("config.toml")
    config_toml.write_text('[feeds]\nrss_feeds = ["https://toml.com/feed"]')

    # Override with env
    os.environ["RSS_FEEDS"] = '["https://env.com/feed"]'

    settings = Settings()
    assert settings.rss_feeds == ["https://env.com/feed"]

    config_toml.unlink()
```

---

## Summary

### Quick Decision Guide

**Choose TOML if:**
- ✅ You want the best user experience
- ✅ You want no extra dependencies
- ✅ You're building for end users (not just developers)

**Choose YAML if:**
- ✅ You're already using YAML everywhere
- ✅ You need very complex nested configs
- ✅ Your team strongly prefers YAML

**Choose Python module if:**
- ✅ Configuration is complex and needs logic
- ✅ Only developers will configure it
- ✅ You want full IDE support and type checking

**Keep .env only if:**
- ✅ Project has < 10 settings
- ✅ You use secret management tools (Doppler, Vault)
- ✅ It's a prototype or personal project

---

## Implementation Checklist

- [ ] Choose format (TOML recommended)
- [ ] Create `config.example.toml` template
- [ ] Update `config.py` to load from TOML
- [ ] Update `.gitignore` to exclude `config.toml`
- [ ] Create `.env.example` (secrets only)
- [ ] Update documentation
- [ ] Add tests for config loading
- [ ] Provide migration script (optional)
- [ ] Announce to users (if open source)

---

## Related Documentation

- [Quick Start Guide](quick%20start.md)
- [Native vs Docker](native-vs-docker.md)
- [Feed Sources](feed%20sources.md)
