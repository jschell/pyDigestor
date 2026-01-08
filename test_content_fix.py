"""Test content normalization fix."""
from pydigestor.sources.feeds import FeedEntry

# Test cases for content normalization
test_cases = [
    ("None", None),
    ("Empty string", ""),
    ("Whitespace only", "   \n\t  "),
    ("Valid content", "This is valid article content with sufficient length."),
    ("Short content", "Short"),
]

print("Content Normalization Test")
print("="*60)

for name, content in test_cases:
    # Simulate what happens in _store_article
    normalized_content = content if content and content.strip() else None

    print(f"\n{name}:")
    print(f"  Input: {repr(content)}")
    print(f"  Normalized: {repr(normalized_content)}")
    print(f"  Will be stored as: {'NULL' if normalized_content is None else f'STRING ({len(normalized_content)} chars)'}")

    # Simulate SQL query filter
    passes_filter = normalized_content is not None
    print(f"  Passes .is_not(None) filter: {passes_filter}")

print("\n" + "="*60)
print("\nExpected behavior:")
print("  - None, empty string, whitespace -> NULL in database")
print("  - Valid content -> stored as-is")
print("  - SQL query .is_not(None) -> only returns articles with actual content")
print("  - This should fix the 'without content' count issue")
