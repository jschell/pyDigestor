# Fix: RSS Articles Showing Misleading "Without Content" Message

## Issue

Users reported seeing misleading messages during auto-summarization:

```
✓ Content extraction: 100.0% success rate (21/21)
...
Checking 21 new article(s) for summarization...
✓ Auto-summarized 1 article(s)
  Skipped: 20 without content, 0 too short (< 200 chars)
```

The message "20 without content" was confusing because:
1. Extraction showed 100% success rate
2. All 21 articles actually HAD content
3. Database inspection confirmed all articles had content

## Root Cause

The issue was **NOT** that articles lacked content. The real problem was:

**RSS feeds provide their own summaries**, which are stored during ingestion. When auto-summarization runs, it skips articles that already have summaries (from the feed), but the skip message incorrectly reported them as "without content".

### The Real Flow

1. **RSS Feed Parsing** (feeds.py:59-70):
   ```python
   # Extract content (prefer content over summary)
   content = None
   if "content" in entry and entry.get("content"):
       content = entry.get("content")[0].get("value", "")
   elif "summary" in entry:
       content = entry.get("summary", "")

   # Extract summary (keep if we have separate content, otherwise None)
   summary = None
   if "content" in entry and entry.get("content") and "summary" in entry:
       summary = entry.get("summary", "")
   ```
   RSS feeds often provide BOTH content (full text) AND summary (feed description).

2. **Article Storage**:
   Articles are stored with both `content` AND `summary` from the RSS feed.

3. **Auto-summarization Filter**:
   ```python
   .where(Article.content.is_not(None))
   .where((Article.summary.is_(None)) | (Article.summary == ""))
   ```
   This correctly filters for articles that:
   - ✅ Have content
   - ❌ **Already have a summary** (from RSS feed)

4. **Misleading Skip Message**:
   The old code counted skipped articles as "without content" when they actually had content but already had summaries from the feed.

## Solution

### 1. Accurate Skip Reason Detection (ingest.py:259-280)

```python
if not articles:
    # Calculate why articles were skipped
    articles_with_existing_summary = 0
    articles_without_content = 0

    for article in all_articles:
        if article.content is None:
            articles_without_content += 1
        elif article.summary and article.summary.strip():
            articles_with_existing_summary += 1

    if articles_with_existing_summary > 0:
        console.print(
            f"[dim]All {articles_with_existing_summary} article(s) already have summaries from RSS feed.[/dim]"
        )
    elif articles_without_content > 0:
        console.print(
            f"[dim]No articles have content to summarize ({articles_without_content} without content).[/dim]"
        )
```

**Effect**:
- Accurately reports WHY articles were skipped
- Distinguishes between "no content" vs "already has summary from feed"
- Users understand RSS feeds don't need local summarization

### 2. Enhanced Debug Logging (ingest.py:244-248)

```python
for article in all_articles:
    content_status = "NULL" if article.content is None else f"{len(article.content)} chars"
    summary_status = "has summary from feed" if (article.summary and article.summary.strip()) else "no summary"
    console.print(f"[dim]  {article.title[:40]}... content: {content_status}, {summary_status}[/dim]")
```

**Effect**:
- Shows both content AND summary status for each article
- Makes it immediately obvious which articles have feed summaries
- Helps diagnose why articles aren't being auto-summarized

### 3. Content Normalization (ingest.py:171-173)

```python
# Normalize content: use None instead of empty string for consistency
normalized_content = entry.content if entry.content and entry.content.strip() else None
```

**Effect**:
- Empty strings and whitespace become `NULL` in database
- Prevents misleading "has content" when content is actually empty
- SQL queries work correctly

### 4. Enhanced Extraction Logging (ingest.py:106-143)

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

### RSS Feeds with Feed Summaries (Most Common)

```
✓ Content extraction: 100.0% success rate (21/21 succeeded)

✓ Stored: Article 1... (content: 4523 chars)
✓ Stored: Article 2... (content: 2891 chars)
...

Checking 21 new article(s) for summarization...
DEBUG: Found 21 articles by ID
  Article 1... content: 4523 chars, has summary from feed
  Article 2... content: 2891 chars, has summary from feed
  ...
DEBUG: After filtering, 0 articles need summarization
All 21 article(s) already have summaries from RSS feed.
```

**This is normal and correct!** RSS feeds typically include summaries, so auto-summarization isn't needed.

### Articles Without Feed Summaries (Less Common)

```
✓ Content extraction: 95.0% success rate (19/20 succeeded)
  ⚠ 1 article(s) failed extraction (no content will be stored)

✓ Stored: Article 1... (content: 4523 chars)
✓ Stored: Article 2... (content: 2891 chars)
✓ Stored: Article 3... (no content)
...

Checking 20 new article(s) for summarization...
DEBUG: Found 20 articles by ID
  Article 1... content: 4523 chars, no summary
  Article 2... content: 2891 chars, no summary
  Article 20... content: NULL, no summary
DEBUG: After filtering, 19 articles need summarization
✓ Auto-summarized 19 article(s)
```

### Expected Outcomes

1. **Accurate skip reasons**: "already have summaries from RSS feed" vs "without content"
2. **Debug visibility**: Shows both content and summary status for each article
3. **Clear extraction breakdown**: Shows succeeded/failed/skipped
4. **Storage transparency**: Shows content length when storing
5. **Correct behavior**: RSS feeds with summaries don't need local summarization

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

## Key Insights

### RSS Feeds Already Include Summaries

Most RSS feeds provide their own article summaries (the feed description). These are stored in the `summary` field during ingestion. **This is the expected behavior** - auto-summarization is designed to skip articles that already have summaries.

### When Auto-Summarization Runs

Auto-summarization only runs on articles that:
1. ✅ Have content extracted
2. ❌ Don't have an existing summary

For RSS feeds (which typically include summaries), auto-summarization will usually show:
```
All X article(s) already have summaries from RSS feed.
```

This is **correct and expected**, not a problem!

### When to Expect Auto-Summarization

Auto-summarization is most useful for:
- **Reddit posts**: Don't include summaries, only titles
- **Articles with failed extraction**: Need manual summarization command
- **Custom feeds**: That don't provide summary fields

## Impact

- ✅ Clear, accurate messaging about why articles weren't summarized
- ✅ Users understand RSS feeds don't need local summarization
- ✅ Debug output shows both content and summary status
- ✅ Better visibility into what's happening during ingestion
- ✅ No breaking changes to existing functionality
