"""Tests for plugin registration and integration."""

import pytest
from unittest.mock import MagicMock

import pydigestor_playwright


@pytest.mark.unit
class TestPluginRegistration:
    """Test plugin registration with pyDigestor."""

    def test_hookimpl_exists(self):
        """Test that hookimpl is properly decorated."""
        assert hasattr(pydigestor_playwright.register_extractors, '__self__')

    def test_register_extractors_signature(self):
        """Test register_extractors has correct signature."""
        import inspect

        sig = inspect.signature(pydigestor_playwright.register_extractors)
        assert 'registry' in sig.parameters

    def test_register_extractors_adds_patterns(self):
        """Test that register_extractors adds patterns to registry."""
        # Mock registry
        mock_registry = MagicMock()
        mock_registry.register = MagicMock()

        # Call the hook
        pydigestor_playwright.register_extractors(mock_registry)

        # Should register multiple patterns
        assert mock_registry.register.call_count >= 4

        # Verify pattern names
        registered_names = [
            call.args[0].name for call in mock_registry.register.call_args_list
        ]

        assert "playwright_wsj" in registered_names
        assert "playwright_twitter" in registered_names
        assert "playwright_medium" in registered_names
        assert "playwright" in registered_names

    def test_pattern_priorities(self):
        """Test that patterns have correct priorities."""
        mock_registry = MagicMock()

        pydigestor_playwright.register_extractors(mock_registry)

        # Check priorities
        for call in mock_registry.register.call_args_list:
            pattern = call.args[0]
            # Site-specific patterns should have priority 7
            if pattern.name in ["playwright_wsj", "playwright_twitter", "playwright_medium"]:
                assert pattern.priority == 7
            # Generic playwright should have priority 1
            elif pattern.name == "playwright":
                assert pattern.priority == 1

    def test_wsj_pattern_domains(self):
        """Test WSJ pattern has correct domain."""
        mock_registry = MagicMock()

        pydigestor_playwright.register_extractors(mock_registry)

        # Find WSJ pattern
        wsj_pattern = None
        for call in mock_registry.register.call_args_list:
            pattern = call.args[0]
            if pattern.name == "playwright_wsj":
                wsj_pattern = pattern
                break

        assert wsj_pattern is not None
        assert "wsj.com" in wsj_pattern.domains

    def test_twitter_pattern_domains(self):
        """Test Twitter pattern handles both twitter.com and x.com."""
        mock_registry = MagicMock()

        pydigestor_playwright.register_extractors(mock_registry)

        # Find Twitter pattern
        twitter_pattern = None
        for call in mock_registry.register.call_args_list:
            pattern = call.args[0]
            if pattern.name == "playwright_twitter":
                twitter_pattern = pattern
                break

        assert twitter_pattern is not None
        assert "twitter.com" in twitter_pattern.domains
        assert "x.com" in twitter_pattern.domains

    def test_generic_pattern_no_domains(self):
        """Test generic playwright pattern has no auto-match domains."""
        mock_registry = MagicMock()

        pydigestor_playwright.register_extractors(mock_registry)

        # Find generic pattern
        generic_pattern = None
        for call in mock_registry.register.call_args_list:
            pattern = call.args[0]
            if pattern.name == "playwright":
                generic_pattern = pattern
                break

        assert generic_pattern is not None
        assert len(generic_pattern.domains) == 0

    def test_all_patterns_have_handler(self):
        """Test all registered patterns have a valid handler."""
        mock_registry = MagicMock()

        pydigestor_playwright.register_extractors(mock_registry)

        for call in mock_registry.register.call_args_list:
            pattern = call.args[0]
            assert pattern.handler is not None
            assert callable(pattern.handler)


@pytest.mark.unit
class TestPluginMetadata:
    """Test plugin metadata and version info."""

    def test_version_exists(self):
        """Test plugin has version string."""
        assert hasattr(pydigestor_playwright, '__version__')
        assert isinstance(pydigestor_playwright.__version__, str)

    def test_version_format(self):
        """Test version follows semantic versioning."""
        version = pydigestor_playwright.__version__
        parts = version.split('.')
        assert len(parts) >= 2  # At least major.minor


@pytest.mark.integration
class TestPluginIntegration:
    """Integration tests for plugin with pyDigestor core."""

    def test_plugin_loadable_by_pluggy(self):
        """Test plugin can be loaded by pluggy."""
        import pluggy

        pm = pluggy.PluginManager("pydigestor")

        # Register hook specs (simplified)
        class HookSpecs:
            @pluggy.HookspecMarker("pydigestor")
            def register_extractors(self, registry):
                pass

        pm.add_hookspecs(HookSpecs)

        # Register plugin
        pm.register(pydigestor_playwright)

        # Verify plugin is registered
        assert pm.is_registered(pydigestor_playwright)

    def test_hook_execution(self):
        """Test hook can be executed."""
        import pluggy

        pm = pluggy.PluginManager("pydigestor")

        # Register hook specs
        class HookSpecs:
            @pluggy.HookspecMarker("pydigestor")
            def register_extractors(self, registry):
                pass

        pm.add_hookspecs(HookSpecs)
        pm.register(pydigestor_playwright)

        # Mock registry
        mock_registry = MagicMock()

        # Execute hook
        pm.hook.register_extractors(registry=mock_registry)

        # Verify registry.register was called
        assert mock_registry.register.called
