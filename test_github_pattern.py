"""Test GitHub pattern extraction with real URLs."""
from pydigestor.sources.extraction import ContentExtractor

def test_github_extraction():
    extractor = ContentExtractor()

    # Test against a real GitHub repository
    url = 'https://github.com/anthropics/anthropic-sdk-python'
    print(f'Testing GitHub pattern extraction for: {url}')
    print('-' * 60)

    content, resolved_url = extractor.extract(url)

    if content:
        print(f'✓ Extraction succeeded!')
        print(f'  Resolved URL: {resolved_url}')
        print(f'  Content length: {len(content)} chars')
        print(f'  Content preview: {content[:300]}...')
        print()
        print(f'Metrics: {extractor.get_metrics()}')
    else:
        print('✗ Extraction failed')

if __name__ == '__main__':
    test_github_extraction()
