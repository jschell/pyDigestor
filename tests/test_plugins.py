"""Tests for plugin system integration."""

import pytest
from unittest.mock import MagicMock, patch

from pydigestor.plugins import pm, load_plugins, get_plugin_manager
from pydigestor.sources.extraction import ContentExtractor, PatternRegistry, ExtractionPattern


@pytest.mark.unit
class TestPluginManager:
    """Test plugin manager functionality."""

    def test_get_plugin_manager(self):
        """Test getting plugin manager instance."""
        manager = get_plugin_manager()
        assert manager is not None
        assert manager.project_name == "pydigestor"

    def test_plugin_manager_singleton(self):
        """Test plugin manager is a singleton."""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        assert manager1 is manager2


@pytest.mark.unit
class TestPluginLoading:
    """Test plugin loading mechanism."""

    def test_load_plugins_registers_hookspecs(self):
        """Test that load_plugins registers hook specifications."""
        # Reset plugin manager state
        if hasattr(pm, '_plugins_loaded'):
            delattr(pm, '_plugins_loaded')

        # Clear existing plugins and hookspecs
        pm._name2plugin.clear()
        pm.hook._hookexec = None
        pm.hook._nonwrappers.clear()
        pm.hook._wrappers.clear()

        # Load plugins
        load_plugins()

        # Verify hookspecs are registered
        assert hasattr(pm.hook, 'register_extractors')

    @patch('pydigestor.plugins.console')
    def test_load_plugins_handles_errors(self, mock_console):
        """Test that plugin loading errors are handled gracefully."""
        # This should not raise even if there are issues
        load_plugins()

        # No assertion needed - just verify it doesn't crash


@pytest.mark.unit
class TestContentExtractorPluginIntegration:
    """Test ContentExtractor integration with plugins."""

    def test_content_extractor_loads_plugins(self):
        """Test that ContentExtractor loads plugins on init."""
        # This should not raise
        extractor = ContentExtractor()

        # Verify registry exists
        assert extractor.registry is not None

    def test_plugin_patterns_registered(self):
        """Test that plugins can register patterns."""
        extractor = ContentExtractor()

        # Should have at least the built-in patterns (pdf, github)
        assert len(extractor.registry.patterns) >= 2

        # Verify built-in patterns exist
        pattern_names = [p.name for p in extractor.registry.patterns]
        assert "pdf" in pattern_names
        assert "github" in pattern_names


@pytest.mark.unit
class TestPatternRegistry:
    """Test PatternRegistry with plugin patterns."""

    def test_pattern_priority_sorting(self):
        """Test that patterns are sorted by priority."""
        registry = PatternRegistry()

        # Register patterns with different priorities
        def handler1(url):
            return "content1", {}

        def handler2(url):
            return "content2", {}

        def handler3(url):
            return "content3", {}

        registry.register(
            ExtractionPattern(name="low", domains=["test.com"], handler=handler1, priority=1)
        )
        registry.register(
            ExtractionPattern(name="high", domains=["test.com"], handler=handler2, priority=10)
        )
        registry.register(
            ExtractionPattern(name="medium", domains=["test.com"], handler=handler3, priority=5)
        )

        # Verify sorting (highest priority first)
        assert registry.patterns[0].priority == 10
        assert registry.patterns[1].priority == 5
        assert registry.patterns[2].priority == 1

    def test_get_handler_returns_highest_priority(self):
        """Test that get_handler returns highest priority match."""
        registry = PatternRegistry()

        def handler_low(url):
            return "low", {}

        def handler_high(url):
            return "high", {}

        registry.register(
            ExtractionPattern(
                name="low", domains=["example.com"], handler=handler_low, priority=1
            )
        )
        registry.register(
            ExtractionPattern(
                name="high", domains=["example.com"], handler=handler_high, priority=10
            )
        )

        # Should return highest priority handler
        name, handler = registry.get_handler("https://example.com/test")
        assert name == "high"
        assert handler is handler_high


@pytest.mark.integration
class TestMockPluginRegistration:
    """Test plugin registration with a mock plugin."""

    def test_mock_plugin_registers_pattern(self):
        """Test that a mock plugin can register a pattern."""

        class MockPlugin:
            """Mock plugin for testing."""

            @staticmethod
            def register_extractors(registry):
                """Register a test pattern."""

                def mock_handler(url):
                    return "mock content", {"method": "mock"}

                registry.register(
                    ExtractionPattern(
                        name="mock_extractor",
                        domains=["mock.com"],
                        handler=mock_handler,
                        priority=8,
                    )
                )

        # Create extractor and registry
        extractor = ContentExtractor()

        # Manually call the mock plugin's hook
        MockPlugin.register_extractors(extractor.registry)

        # Verify pattern was registered
        pattern_names = [p.name for p in extractor.registry.patterns]
        assert "mock_extractor" in pattern_names

        # Verify it can be retrieved
        name, handler = extractor.registry.get_handler("https://mock.com/test")
        assert name == "mock_extractor"

        # Verify handler works
        content, metadata = handler("https://mock.com/test")
        assert content == "mock content"
        assert metadata["method"] == "mock"


@pytest.mark.unit
class TestHookSpecification:
    """Test hook specification."""

    def test_hookspec_exists(self):
        """Test that hookspec module exists and has register_extractors."""
        from pydigestor import hookspecs

        assert hasattr(hookspecs, 'register_extractors')
        assert hasattr(hookspecs, 'hookspec')

    def test_hookspec_signature(self):
        """Test hookspec has correct signature."""
        from pydigestor import hookspecs
        import inspect

        sig = inspect.signature(hookspecs.register_extractors)
        assert 'registry' in sig.parameters
