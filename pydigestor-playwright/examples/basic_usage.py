"""
Basic usage example for pydigestor-playwright plugin.

This example demonstrates how to use the Playwright plugin
to extract content from JavaScript-heavy websites.
"""

from pydigestor.sources.extraction import ContentExtractor


def main():
    """Extract content from various sites using the Playwright plugin."""

    # Initialize extractor (automatically loads plugins)
    extractor = ContentExtractor()

    # Test URLs that benefit from Playwright
    test_urls = [
        "https://example.com",  # Simple test site
        # Uncomment to test real sites (requires network):
        # "https://www.wsj.com/tech/cybersecurity/",
        # "https://medium.com/@username/article-slug",
    ]

    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"Extracting: {url}")
        print('='*80)

        # Extract content
        content, final_url = extractor.extract(url)

        if content:
            print(f"\n✓ Success!")
            print(f"Final URL: {final_url}")
            print(f"Content length: {len(content)} characters")
            print(f"\nFirst 500 characters:")
            print(content[:500])
            print("...")
        else:
            print(f"\n✗ Failed to extract content")

    # Print extraction metrics
    print(f"\n{'='*80}")
    print("Extraction Metrics")
    print('='*80)
    metrics = extractor.get_metrics()
    print(f"Total attempts: {metrics['total_attempts']}")
    print(f"Trafilatura successes: {metrics['trafilatura_success']}")
    print(f"Newspaper successes: {metrics['newspaper_success']}")
    print(f"Failures: {metrics['failures']}")
    print(f"Success rate: {metrics['success_rate']}%")

    if metrics.get('pattern_extractions'):
        print(f"\nPattern-based extractions:")
        for pattern, count in metrics['pattern_extractions'].items():
            print(f"  {pattern}: {count}")


if __name__ == "__main__":
    main()
