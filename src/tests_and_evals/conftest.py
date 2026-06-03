"""Root hooks and shared fixture plugins for the whole ``tests_and_evals`` tree.

Subdirectories may add their own ``conftest.py`` (for example ``evals/conftest.py``
for eval-only session hooks). Those files complement this one; pytest merges them by
directory scope.

Shared fixtures live in ``common/`` and are registered here so tests do not need
side-effect imports (which Ruff would remove as unused). Add new plugin modules to
``pytest_plugins`` when you introduce more shared fixture files.
"""

pytest_plugins = ["src.tests_and_evals.common.fixtures"]
