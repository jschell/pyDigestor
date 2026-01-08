# Fix: RSS Articles Not Being Summarized

## Issue

Users reported seeing "100% success rate" for content extraction, but most articles showed "without content" when attempting summarization:

```
✓ Content extraction: 100.0% success rate (21/21)
...
Checking 21 new article(s) for summarization...
✓ Auto-summarized 1 article(s)
  Skipped: 20 without content, 0 too short (< 200 chars)
```

## Root Cause

The issue was in how article content was being stored in the database:

1. **Inconsistent NULL vs empty string handling**:
   - Articles were stored with `content=entry.content or ""` (ingest.py:176)
   - This converted `None` to empty string `""`
   - But empty strings and whitespace-only content should be treated as "no content"

2. **SQL query behavior**:
   - Auto-summarization used `.where(Article.content.is_not(None))` to filter articles
   - Empty strings (`""`) would pass this filter
   - But they would fail the minimum length check later
   - However, the failure counting logic only counted articles filtered by SQL as "without content"

3. **Misleading extraction metrics**:
   - Extraction could succeed (return content)
   - But if that content was later stripped to nothing (e.g., HTML tags removed), it became empty
   - Or extraction could fail, leaving `entry.content` as None or empty from RSS feed
   - When stored with `or ""`, these became empty strings in the database
   - SQL query would include them, but they'd be skipped for being too short

## Solution

### 1. Content Normalization (ingest.py:173)

```python
# Normalize content: use None instead of empty string for consistency
# This ensures SQL queries work correctly
normalized_content = entry.content if entry.content and entry.content.strip() else None
```

**Effect**:
- `None`, empty strings, and whitespace-only content all become `NULL` in database
- SQL filter `.is_not(None)` now correctly identifies articles without usable content
- "without content" count is now accurate

### 2. Enhanced Extraction Logging (ingest.py:106-143)

```python
extraction_attempted = 0
extraction_succeeded = 0
extraction_failed = 0
extraction_skipped = 0

for entry in all_entries:
    if force_extraction or not entry.content or len(entry.content) < 200:
        extraction_attempted += 1
        content, resolved_url = extractor.extract(entry.url)
        if content:
            entry.content = content
            entry.url = resolved_url
            extraction_succeeded += 1
        else:
            extraction_failed += 1
            # entry.content remains as it was (possibly None or short content from feed)
    else:
        extraction_skipped += 1
```

**Effect**:
- Tracks extraction attempts vs successes vs failures separately
- Shows articles skipped because they already have content from feed
- Warns about extraction failures

### 3. Storage Debugging (ingest.py:196-200)

```python
if normalized_content:
    console.print(f"[green]✓[/green] Stored: {entry.title[:50]}... (content: {len(normalized_content)} chars)")
else:
    console.print(f"[green]✓[/green] Stored: {entry.title[:50]}... [dim](no content)[/dim]")
```

**Effect**:
- Shows content length for each stored article
- Makes it immediately obvious which articles have content

## Expected Behavior After Fix

### Normal RSS Ingestion

```
✓ Content extraction: 95.0% success rate (19/20 succeeded)
  Skipped 1 article(s) already having content >= 200 chars from feed
  ⚠ 1 article(s) failed extraction (no content will be stored)

✓ Stored: Article 1... (content: 4523 chars)
✓ Stored: Article 2... (content: 2891 chars)
✓ Stored: Article 3... (no content)
...

Checking 20 new article(s) for summarization...
✓ Auto-summarized 19 article(s)
  Skipped: 1 without content, 0 too short (< 200 chars)
```

### Expected Outcomes

1. **Accurate "without content" count**: Only counts articles with NULL content
2. **Clear extraction breakdown**: Shows succeeded/failed/skipped
3. **Storage transparency**: Shows content length when storing
4. **Correct summarization**: Only attempts to summarize articles with actual content

## Testing

Run test to verify content normalization:

```bash
uv run python test_content_fix.py
```

Expected output shows:
- `None`, `""`, and whitespace → normalized to `None`
- Valid content → preserved
- SQL filter `.is_not(None)` → correctly filters out empty content

## Files Modified

- `src/pydigestor/steps/ingest.py`: Content normalization, extraction tracking, enhanced logging
- `test_content_fix.py`: Test script to verify fix
- `FIX_RSS_SUMMARIZATION.md`: This documentation

## Impact

- ✅ Articles with failed extraction won't show misleading "success" counts
- ✅ "without content" count now accurately reflects articles that can't be summarized
- ✅ Better visibility into extraction pipeline
- ✅ No breaking changes to existing functionality
