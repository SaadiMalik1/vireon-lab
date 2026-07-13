"""
VIREON SBOM Generator — CycloneDX 1.5 Software Bill of Materials.

Generates a machine-readable SBOM from pyproject.toml and Cargo.lock,
as mandated by FDA Section 524B for cyber device premarket submissions.

Output format: CycloneDX 1.5 JSON
References:
  - https://cyclonedx.org/specification/overview/
  - FDA "Cybersecurity in Medical Devices" (Feb 2026)
  - NTIA SBOM minimum elements
"""

import json
import os
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


def _parse_pyproject_toml(project_root: str) -> Dict[str, Any]:
    """Parse pyproject.toml to extract project metadata and dependencies."""
    toml_path = os.path.join(project_root, "pyproject.toml")
    if not os.path.exists(toml_path):
        return {}

    # Use tomllib (3.11+) or tomli fallback
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            # Manual minimal parser for [project] section
            return _parse_toml_minimal(toml_path)

    with open(toml_path, "rb") as f:
        return tomllib.load(f)


def _parse_toml_minimal(toml_path: str) -> Dict[str, Any]:
    """Fallback TOML parser for environments without tomllib/tomli."""
    result: Dict[str, Any] = {"project": {"dependencies": [], "optional-dependencies": {}}}
    current_section = ""

    with open(toml_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Section headers
            section_match = re.match(r'^\[([^\]]+)\]$', line)
            if section_match:
                current_section = section_match.group(1)
                continue

            if current_section == "project":
                if line.startswith("name"):
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        result["project"]["name"] = m.group(1)
                elif line.startswith("version"):
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        result["project"]["version"] = m.group(1)
                elif line.startswith("description"):
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        result["project"]["description"] = m.group(1)
                elif line.startswith("requires-python"):
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        result["project"]["requires-python"] = m.group(1)

            if current_section == "project" and "dependencies" in current_section:
                pass

    # Second pass: extract dependency arrays
    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract main dependencies
    dep_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if dep_match:
        deps_str = dep_match.group(1)
        deps = re.findall(r'"([^"]+)"', deps_str)
        result["project"]["dependencies"] = deps

    # Extract optional dependencies
    opt_sections = re.finditer(
        r'\[project\.optional-dependencies\]\s*\n(.*?)(?=\n\[|\Z)',
        content, re.DOTALL
    )
    for section in opt_sections:
        for line in section.group(1).strip().split('\n'):
            m = re.match(r'(\w+)\s*=\s*\[(.*?)\]', line)
            if m:
                group_name = m.group(1)
                group_deps = re.findall(r'"([^"]+)"', m.group(2))
                result["project"].setdefault("optional-dependencies", {})[group_name] = group_deps

    return result


def _parse_cargo_lock(project_root: str) -> List[Dict[str, str]]:
    """Parse Cargo.lock to extract Rust crate dependencies."""
    lock_path = os.path.join(project_root, "runemate", "Cargo.lock")
    if not os.path.exists(lock_path):
        return []

    packages = []
    current_pkg: Dict[str, str] = {}

    with open(lock_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "[[package]]":
                if current_pkg:
                    packages.append(current_pkg)
                current_pkg = {}
            elif "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"')
                current_pkg[key] = value

    if current_pkg:
        packages.append(current_pkg)

    return packages


def _parse_pep508_dependency(dep_str: str) -> Dict[str, str]:
    """Parse a PEP 508 dependency string like 'numpy>=1.20.0' into name and version."""
    # Handle environment markers (e.g. 'tomli>=2.0.0;python_version<"3.11"')
    dep_str = dep_str.split(";")[0].strip()

    # Split on version specifier
    m = re.match(r'^([a-zA-Z0-9_-]+)\s*(.*)', dep_str)
    if m:
        name = m.group(1).lower().replace("-", "_")
        version_spec = m.group(2).strip()
        # Extract actual version number
        version = re.sub(r'^[><=!~]+', '', version_spec) if version_spec else "unspecified"
        return {"name": name, "version": version, "version_spec": version_spec}

    return {"name": dep_str.lower(), "version": "unspecified", "version_spec": ""}


def generate_sbom(project_root: str, output_format: str = "json") -> Dict[str, Any]:
    """
    Generate a CycloneDX 1.5 SBOM for the VIREON project.

    Args:
        project_root: Path to the project root directory.
        output_format: Output format (currently only "json" supported).

    Returns:
        CycloneDX 1.5 BOM dictionary.
    """
    toml_data = _parse_pyproject_toml(project_root)
    cargo_packages = _parse_cargo_lock(project_root)

    project = toml_data.get("project", {})
    project_name = project.get("name", "vireon")
    project_version = project.get("version", "0.0.0")
    project_description = project.get("description", "")

    # Generate deterministic serial number
    serial_seed = f"{project_name}:{project_version}:{datetime.now(timezone.utc).isoformat()}"
    serial_number = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, serial_seed)}"

    # --- Build component list ---
    components = []

    # 1. Python dependencies
    all_deps = list(project.get("dependencies", []))
    for group_name, group_deps in project.get("optional-dependencies", {}).items():
        for dep in group_deps:
            # Skip self-references like "vireon[...]"
            if dep.startswith(f"{project_name}["):
                continue
            all_deps.append(dep)

    seen_names = set()
    for dep_str in all_deps:
        parsed = _parse_pep508_dependency(dep_str)
        if parsed["name"] in seen_names:
            continue
        seen_names.add(parsed["name"])

        component = {
            "type": "library",
            "name": parsed["name"],
            "version": parsed["version"],
            "purl": f"pkg:pypi/{parsed['name']}@{parsed['version']}",
            "scope": "required",
            "properties": [
                {"name": "vireon:ecosystem", "value": "python"},
                {"name": "vireon:version_spec", "value": parsed["version_spec"]}
            ]
        }
        components.append(component)

    # 2. Rust crate dependencies
    for pkg in cargo_packages:
        name = pkg.get("name", "unknown")
        version = pkg.get("version", "0.0.0")
        source = pkg.get("source", "")

        component = {
            "type": "library",
            "name": name,
            "version": version,
            "scope": "required",
            "properties": [
                {"name": "vireon:ecosystem", "value": "rust"},
            ]
        }

        if source.startswith("registry+"):
            component["purl"] = f"pkg:cargo/{name}@{version}"
        else:
            component["purl"] = f"pkg:cargo/{name}@{version}?source=local"

        components.append(component)

    # 3. Build system dependency
    build_requires = toml_data.get("build-system", {}).get("requires", [])
    for req in build_requires:
        parsed = _parse_pep508_dependency(req)
        if parsed["name"] not in seen_names:
            seen_names.add(parsed["name"])
            components.append({
                "type": "library",
                "name": parsed["name"],
                "version": parsed["version"],
                "purl": f"pkg:pypi/{parsed['name']}@{parsed['version']}",
                "scope": "optional",
                "properties": [
                    {"name": "vireon:ecosystem", "value": "python"},
                    {"name": "vireon:role", "value": "build-system"}
                ]
            })

    # --- Assemble CycloneDX 1.5 BOM ---
    bom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": serial_number,
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "vireon-sbom-generator",
                        "version": project_version,
                        "description": "VIREON built-in SBOM generator for FDA 524B compliance"
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": project_name,
                "version": project_version,
                "description": project_description,
                "purl": f"pkg:pypi/{project_name}@{project_version}",
                "properties": [
                    {"name": "vireon:python_requires", "value": project.get("requires-python", ">=3.10")},
                    {"name": "vireon:license", "value": "MIT"},
                    {"name": "vireon:fda_device_class", "value": "cyber_device_524b"}
                ]
            },
            "lifecycles": [
                {"phase": "build"},
                {"phase": "operations"}
            ]
        },
        "components": components,
        "properties": [
            {"name": "vireon:sbom_purpose", "value": "FDA Section 524B premarket submission"},
            {"name": "vireon:component_count", "value": str(len(components))},
            {"name": "vireon:ecosystems", "value": "python,rust"}
        ]
    }

    return bom


def save_sbom(bom: Dict[str, Any], output_path: str) -> None:
    """Save SBOM to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(bom, f, indent=2, ensure_ascii=False)


def print_sbom_summary(bom: Dict[str, Any]) -> None:
    """Print a human-readable summary of the SBOM."""
    metadata = bom.get("metadata", {})
    root = metadata.get("component", {})
    components = bom.get("components", [])

    python_deps = [c for c in components if any(
        p.get("value") == "python" for p in c.get("properties", [])
    )]
    rust_deps = [c for c in components if any(
        p.get("value") == "rust" for p in c.get("properties", [])
    )]

    print("=" * 60)
    print(" VIREON SBOM Summary (CycloneDX 1.5)")
    print("=" * 60)
    print(f"  Root Component: {root.get('name', '?')} v{root.get('version', '?')}")
    print(f"  Generated:      {metadata.get('timestamp', '?')}")
    print(f"  Serial:         {bom.get('serialNumber', '?')}")
    print()
    print(f"  Total Components: {len(components)}")
    print(f"    Python (PyPI):  {len(python_deps)}")
    print(f"    Rust (Cargo):   {len(rust_deps)}")
    print()

    if python_deps:
        print("  [Python Dependencies]")
        for c in sorted(python_deps, key=lambda x: x["name"]):
            print(f"    • {c['name']:20s} {c['version']}")
        print()

    if rust_deps:
        print("  [Rust Dependencies]")
        for c in sorted(rust_deps, key=lambda x: x["name"]):
            print(f"    • {c['name']:20s} {c['version']}")
        print()

    print("=" * 60)
