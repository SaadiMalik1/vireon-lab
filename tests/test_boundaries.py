import os
import ast
from pathlib import Path
import pytest

def get_imports(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports

def get_python_files(directory: str):
    return list(Path(directory).rglob("*.py"))

def test_sdk_does_not_import_core_or_lab():
    """The SDK is the lowest level. It cannot depend on the runtime or the lab."""
    sdk_files = get_python_files("vireon/sdk")
    for file in sdk_files:
        imports = get_imports(file)
        for imp in imports:
            assert not imp.startswith("vireon.core"), f"{file} illegally imports {imp}"
            assert not imp.startswith("vireon_lab"), f"{file} illegally imports {imp}"

def test_core_does_not_import_lab():
    """The core runtime framework cannot depend on educational code or scenarios."""
    core_files = get_python_files("vireon/core")
    for file in core_files:
        imports = get_imports(file)
        for imp in imports:
            assert not imp.startswith("vireon_lab"), f"{file} illegally imports {imp}"

def test_lab_providers_only_import_sdk():
    """
    Lab providers are plugins. Plugins must ONLY import from vireon.sdk,
    not from vireon.core (which leaks runtime internals).
    """
    provider_files = get_python_files("vireon_lab/providers")
    for file in provider_files:
        imports = get_imports(file)
        for imp in imports:
            # We enforce that providers don't reach into core.
            assert not imp.startswith("vireon.core"), f"Boundary Violation: Provider {file} illegally imports runtime module {imp}. It must use vireon.sdk instead."
