"""Plugin hook specifications for pyDigestor.

This module defines the plugin interface using pluggy's hookspec decorator.
Plugins implement these hooks to extend pyDigestor's functionality.
"""

import pluggy

hookspec = pluggy.HookspecMarker("pydigestor")


@hookspec
def register_extractors(registry):
    """
    Register custom content extraction patterns.

    Plugins implement this hook to add new extraction methods to the PatternRegistry.
    This allows plugins to handle specific sites or content types.

    Args:
        registry: PatternRegistry instance to register patterns with

    Example:
        @hookimpl
        def register_extractors(registry):
            from pydigestor.sources.extraction import ExtractionPattern

            def my_handler(url):
                # Custom extraction logic
                return content, metadata

            registry.register(ExtractionPattern(
                name="my_extractor",
                domains=["example.com"],
                handler=my_handler,
                priority=5
            ))
    """
