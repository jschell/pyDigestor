# pyDigestor Documentation

> **📖 Main README**: This file has been replaced. Please see [../README.md](../README.md) for the complete and up-to-date project documentation.

## Quick Links

- **[Main README](../README.md)** - Complete project documentation
- **[Quick Start Guide](quick%20start.md)** - Installation and setup
- **[Architecture](architecture.md)** - Technical design and database schema
- **[Local Summarization](local%20summarization.md)** - Summarization guide
- **[Feed Sources](feed%20sources.md)** - Recommended RSS feeds
- **[Pattern Extraction](pattern%20extraction%20plan.md)** - Content extraction patterns
- **[Reddit Integration](reddit%20implementation%20plan%20updated.md)** - Reddit configuration

## Current Architecture

pyDigestor now uses:
- **SQLite** with FTS5 full-text search (porter stemming)
- **TF-IDF** ranked retrieval (scikit-learn)
- **Local summarization** (LexRank/TextRank/LSA via sumy)
- **Single-container** Docker deployment (808MB)
- **Zero cost** for Phase 1 (all processing is local)

See [../README.md](../README.md) for complete details.
