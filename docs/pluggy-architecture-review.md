# Pluggy Architecture Review: simonw/llm

## How Pluggy Works

**Pluggy** is a plugin framework enabling decoupled, extensible Python applications through hooks.

### Core Concepts

1. **Hook Specifications (hookspec)**: Define extension points with expected signatures
2. **Hook Implementations (hookimpl)**: Plugin code that implements those extension points
3. **Plugin Manager**: Discovers and orchestrates plugin loading/execution
4. **Namespace**: Unique identifier tying hookspecs and hookimpls together

### Basic Flow

```
1. Application defines hookspecs (contracts for plugins)
2. Plugins implement hookimpls (fulfill contracts)
3. Plugin manager discovers plugins via entry points
4. Application calls pm.hook.hook_name() → all plugins execute
```

---

## simonw/llm Implementation

### Architecture

**6 Hook Points:**
- `register_models` - LLM model providers (GPT, Claude, etc.)
- `register_embedding_models` - Embedding model providers
- `register_commands` - CLI command extensions
- `register_tools` - Function calling tools
- `register_template_loaders` - Template sources
- `register_fragment_loaders` - Fragment sources

### Key Pattern: Callback Registration

```python
# Hookspec
@hookspec
def register_models(register):
    """Plugins call register(model) to add models"""

# Plugin
@hookimpl
def register_models(register):
    register(GPT4Model())
    register(ClaudeModel())
```

### Discovery

1. **Setuptools entry points** - `pyproject.toml` declares `[project.entry-points.llm]`
2. **Environment variable** - `LLM_LOAD_PLUGINS=package1,package2`
3. **Default plugins** - Hardcoded core plugins

---

## Application to pyDigestor

### Current Architecture Gap

pyDigestor currently has monolithic components for:
- Content extractors (PDF, HTML, etc.)
- Processors (chunking, metadata)
- Destinations (file, database)
- Document types

### Proposed Plugin Architecture

**Core Hook Points:**

1. **`register_extractors`** - Register content extraction strategies
   - PDF extractors, HTML parsers, image OCR, etc.
   - Each extractor declares supported MIME types/extensions

2. **`register_processors`** - Register processing pipelines
   - Chunking strategies, metadata enrichment, embeddings
   - Chain multiple processors

3. **`register_destinations`** - Register output targets
   - File writers, database connections, vector stores, APIs

4. **`register_document_types`** - Register custom document schemas
   - Define structure/fields for different document types

5. **`register_validators`** - Register content validation rules
   - Schema validation, content quality checks

### Benefits

- **Modularity**: Each extractor/processor becomes a standalone plugin
- **Extensibility**: Users add new formats without forking
- **Testing**: Test plugins in isolation
- **Distribution**: Share plugins via PyPI (e.g., `pydigestor-playwright`)
- **Configuration**: Enable/disable features via entry points

### Example Plugin Structure

```
pydigestor-playwright/           # Separate package
├── pyproject.toml              # Declares entry point
├── pydigestor_playwright/
│   └── __init__.py             # @hookimpl register_extractors
```

Users install: `pip install pydigestor-playwright` → automatically discovered

### Implementation Scope

**Phase 1**: Core hookspecs + migration of built-in extractors to default plugins
**Phase 2**: External plugin support via entry points
**Phase 3**: Plugin marketplace/discovery tooling

### Namespace

Use `"pydigestor"` as the pluggy namespace to match project identity.

---

## Key Takeaways

1. **Pluggy enables zero-coupling**: Core never imports plugins
2. **Callback pattern**: Plugins receive registration function, call it multiple times
3. **Entry points are standard**: Python packaging supports this natively
4. **Start simple**: Convert internal modules to plugins first, then open externally
5. **Document hookspecs thoroughly**: They're the contract for plugin developers
