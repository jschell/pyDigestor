"""Plugin manager for pyDigestor.

Manages plugin discovery, loading, and hook execution using pluggy.
Plugins are discovered via setuptools entry points.
"""

import pluggy
from rich.console import Console

from . import hookspecs

console = Console()

# Global plugin manager instance
pm = pluggy.PluginManager("pydigestor")


def load_plugins():
    """
    Discover and load all plugins from entry points.

    Plugins register themselves via setuptools entry points in the
    'pydigestor' group. This function should be called once during
    application initialization.

    Entry point format in plugin's pyproject.toml:
        [project.entry-points.pydigestor]
        plugin_name = "package.module"
    """
    # Register hook specifications
    pm.add_hookspecs(hookspecs)

    # Load plugins from entry points
    try:
        pm.load_setuptools_entrypoints("pydigestor")

        # Report loaded plugins
        plugin_count = len(pm.get_plugins())
        if plugin_count > 0:
            console.print(f"[dim]→ Loaded {plugin_count} plugin(s)[/dim]")
            for plugin in pm.get_plugins():
                plugin_name = getattr(plugin, "__name__", str(plugin))
                console.print(f"[dim]  • {plugin_name}[/dim]")
    except Exception as e:
        # Non-fatal: plugins are optional
        console.print(f"[yellow]⚠ Plugin loading warning: {e}[/yellow]")


def get_plugin_manager() -> pluggy.PluginManager:
    """
    Get the global plugin manager instance.

    Returns:
        PluginManager instance with loaded plugins
    """
    return pm
