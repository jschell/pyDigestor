# Modular Components & Site Routing Plan

## Modular Functions (Beyond Playwright)

### High-Value Plugins

**1. Content Extractors**
- PDF handlers (pdfplumber, PyMuPDF, OCR variants)
- HTML parsers (trafilatura, newspaper3k, readability, goose3)
- Markdown converters
- Academic paper extractors (arXiv, PubMed, IEEE Xplore)
- Code repository handlers (GitHub, GitLab, Bitbucket)
- Document formats (DOCX, EPUB, LaTeX)

**2. Site-Specific Handlers**
- Medium (paywall bypass, canonical resolution)
- GitHub (README, issues, releases, PRs)
- Reddit (API + old.reddit.com fallback)
- Lemmy (API + HTML scraping)
- Hacker News, Lobsters (aggregator resolution)
- Stack Overflow (Q&A extraction)

**3. Summarization Algorithms**
- Statistical (LexRank, TextRank, LSA) ← *already modular*
- Extractive LLM-based
- Abstractive (GPT, Claude, local models)
- Domain-specific (scientific, news, technical)

**4. Search Backends**
- FTS5, TF-IDF, Embeddings ← *already modular*
- BM25, ColBERT, hybrid retrieval
- Vector databases (Chroma, Weaviate, Qdrant)

**5. Quality Filters**
- Reddit score/recency ← *exists*
- Sentiment analysis
- Content type classifiers (news vs. opinion vs. tutorial)
- Credibility scoring
- Language detection

**6. Output Destinations**
- SQLite, PostgreSQL ← *exists*
- JSON/CSV exporters
- Markdown/Obsidian vaults
- Vector stores
- RSS feed generation
- REST API endpoints

---

## Site→Extractor Routing Plan

### Current State
- Hardcoded `PatternRegistry` in `extraction.py`
- Manual priority ordering
- New sites require code changes

### Proposed: Configuration-Based Routing

#### **1. Config File Structure (`config.toml`)**

```toml
[extraction.routing]
# Site patterns → extractor preferences

[[extraction.routing.rules]]
pattern = "arxiv.org"
extractor = "pdf"
transform_url = "https://arxiv.org/pdf/{id}.pdf"  # Optional URL rewrite
priority = 10

[[extraction.routing.rules]]
pattern = "github.com"
extractor = "github"
priority = 5

[[extraction.routing.rules]]
pattern = "*.pdf"
extractor = "pdf"
match_type = "extension"
priority = 10

[[extraction.routing.rules]]
pattern = "medium.com"
extractor = "medium"
fallback = "trafilatura"  # If medium extractor fails

[[extraction.routing.rules]]
pattern = "*"
extractor = "trafilatura"
fallback = ["newspaper3k", "html2text"]
priority = 1
```

#### **2. Plugin Metadata (`pyproject.toml` for external plugins)**

```toml
# In pydigestor-playwright package
[project.entry-points.pydigestor]
playwright = "pydigestor_playwright"

[tool.pydigestor.routing]
# Patterns this plugin handles
patterns = [
    {pattern = "twitter.com", priority = 5},
    {pattern = "x.com", priority = 5},
    {pattern = "*.spa", match_type = "class", priority = 3}
]
```

#### **3. Registry Enhancement**

**File**: `sources/extractor_registry.py` (new)

```python
class ExtractorRouter:
    """Loads routing config + plugin metadata"""

    def __init__(self):
        self.rules = []
        self._load_config_rules()       # From config.toml
        self._load_plugin_rules()        # From installed plugins
        self._sort_by_priority()

    def match(self, url: str) -> ExtractorConfig:
        """Returns best matching extractor + config"""
        for rule in self.rules:
            if self._pattern_matches(url, rule):
                return ExtractorConfig(
                    name=rule.extractor,
                    handler=self._get_handler(rule.extractor),
                    transform=rule.get('transform_url'),
                    fallback=rule.get('fallback')
                )
        return self._default_extractor()

    def _pattern_matches(self, url: str, rule: dict) -> bool:
        """Supports: domain, glob, regex, extension"""
        match rule.match_type:
            case "domain": return rule.pattern in url
            case "extension": return url.endswith(rule.pattern)
            case "regex": return re.match(rule.pattern, url)
            case "glob": return fnmatch.fnmatch(url, rule.pattern)
```

#### **4. Usage**

```python
# Auto-routes based on config
router = ExtractorRouter()
config = router.match("https://arxiv.org/abs/2301.00001")
# Returns: ExtractorConfig(name="pdf", transform="https://arxiv.org/pdf/2301.00001.pdf")

content = config.handler(config.transform or url)
```

---

## Benefits

1. **Zero Code Changes**: Add new sites via config file
2. **Plugin Self-Description**: Plugins declare their patterns in metadata
3. **User Overrides**: Users customize routing without forking
4. **Testing**: Mock routing rules for testing
5. **Dynamic Discovery**: `pydigestor plugins list` shows routes

---

## Implementation Phases

**Phase 1**: Config file routing (keep existing handlers)
- Add `[extraction.routing]` to config.toml
- Create `ExtractorRouter` class
- Migrate hardcoded patterns to config

**Phase 2**: Plugin metadata support
- Read routing rules from `pyproject.toml` entry points
- Merge plugin rules with config rules
- Conflict resolution (config > plugins > defaults)

**Phase 3**: Advanced routing
- Regex patterns
- Content-type detection
- Conditional routing (if PDF extraction fails → try OCR)
- Route metrics (track success rates per rule)

---

## Example: Adding arXiv PDF Support

**Before** (code change required):
```python
# Edit extraction.py
def _handle_arxiv(url):
    # Custom logic here...
```

**After** (config only):
```toml
[[extraction.routing.rules]]
pattern = "arxiv.org"
extractor = "pdf"
transform_url = "https://arxiv.org/pdf/{arxiv_id}.pdf"
priority = 10
```

Done. No code changes needed.
