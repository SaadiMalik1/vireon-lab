#!/usr/bin/env python3
import os
import argparse
import difflib
import yaml
import libcst as cst
from typing import Dict, List, Tuple

class MigrationManifest:
    def __init__(self, path: str):
        with open(path, "r") as f:
            self.data = yaml.safe_load(f)
        
        self.import_mappings: Dict[str, str] = {}
        for entry in self.data.get("import_migrations", []):
            self.import_mappings[entry["old"]] = entry["new"]
            
        self.api_mappings: Dict[str, str] = {}
        for entry in self.data.get("api_migrations", []):
            self.api_mappings[entry["old"]] = entry["new"]


class VireonImportTransformer(cst.CSTTransformer):
    """
    Transforms imports declaratively based on the loaded manifest mappings.
    """
    def __init__(self, manifest: MigrationManifest):
        self.manifest = manifest
        self.unknown_imports: List[str] = []

    def _match_and_replace_attr(self, node: cst.Attribute, mapping: Dict[str, str]) -> cst.Attribute:
        """Helper to safely reconstruct an Attribute node if it matches our mappings."""
        # Extract full string path from CST Attribute
        parts = []
        current = node
        while isinstance(current, cst.Attribute):
            parts.insert(0, current.attr.value)
            current = current.value
        
        if isinstance(current, cst.Name):
            parts.insert(0, current.value)
        else:
            return node # Cannot process this type of node
            
        full_import = ".".join(parts)
        
        # Check against mappings
        if full_import in mapping:
            new_full_import = mapping[full_import]
            # Reconstruct cst.Attribute
            new_parts = new_full_import.split(".")
            new_node = cst.Name(new_parts[0])
            for part in new_parts[1:]:
                new_node = cst.Attribute(value=new_node, attr=cst.Name(part))
            return new_node
            
        return node

    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom:
        # We don't support automated relative import rewriting because of ambiguity.
        # Warn the user to fix these manually before running the script.
        if len(updated_node.relative) > 0:
            rel_str = "." * len(updated_node.relative)
            if updated_node.module:
                rel_str += cst.Module([]).code_for_node(updated_node.module)
            self.unknown_imports.append(f"Relative import detected: {rel_str}")
            return updated_node

        if updated_node.module and isinstance(updated_node.module, (cst.Attribute, cst.Name)):
            # 1. First Pass: Handle structural import migrations
            new_module = updated_node.module
            if isinstance(updated_node.module, cst.Attribute):
                new_module = self._match_and_replace_attr(updated_node.module, self.manifest.import_mappings)
            elif isinstance(updated_node.module, cst.Name):
                if updated_node.module.value in self.manifest.import_mappings:
                    new_val = self.manifest.import_mappings[updated_node.module.value]
                    new_module = cst.parse_expression(new_val)

            # 2. Second Pass: Handle API migrations (e.g., DigitalTwin -> StateStore)
            # Check if the combined module + imported name matches an API migration
            new_names = []
            module_str_path = cst.Module([]).code_for_node(new_module)
            
            for name in updated_node.names:
                imported_name_str = name.name.value
                full_api_path = f"{module_str_path}.{imported_name_str}"
                
                if full_api_path in self.manifest.api_mappings:
                    new_api_path = self.manifest.api_mappings[full_api_path]
                    new_module_str, new_class_str = new_api_path.rsplit(".", 1)
                    
                    # Update the module path to the new module
                    new_module = cst.parse_expression(new_module_str)
                    # Update the imported class name
                    new_names.append(name.with_changes(name=cst.Name(new_class_str)))
                else:
                    new_names.append(name)
                    
            return updated_node.with_changes(module=new_module, names=new_names)

        return updated_node

def generate_diff(file_path: str, old_source: str, new_source: str) -> str:
    diff = difflib.unified_diff(
        old_source.splitlines(keepends=True),
        new_source.splitlines(keepends=True),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    )
    return "".join(diff)

def process_file(file_path: str, manifest: MigrationManifest, dry_run: bool, backup: bool) -> Tuple[bool, List[str]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, []

    try:
        tree = cst.parse_module(source)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return False, []

    transformer = VireonImportTransformer(manifest)
    modified_tree = tree.visit(transformer)
    new_source = modified_tree.code
    
    warnings = transformer.unknown_imports

    if source != new_source:
        print(f"\n--- Modifications for {file_path} ---")
        print(generate_diff(file_path, source, new_source))
        
        if not dry_run:
            if backup:
                with open(file_path + ".bak", "w", encoding="utf-8") as f:
                    f.write(source)
                print(f"Created backup: {file_path}.bak")
                
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_source)
            print(f"Wrote changes to {file_path}")
            
        return True, warnings
        
    return False, warnings

def main():
    parser = argparse.ArgumentParser(description="Declarative AST Migration Tool for VIREON")
    parser.add_argument("target_dir", help="Directory to recursively migrate")
    parser.add_argument("--manifest", required=True, help="Path to MIGRATION_MANIFEST.yaml")
    parser.add_argument("--execute", action="store_true", help="Actually write changes to disk (default is Dry Run)")
    parser.add_argument("--backup", action="store_true", help="Create .bak files before writing")
    args = parser.parse_args()

    print(f"Loading manifest from {args.manifest}")
    manifest = MigrationManifest(args.manifest)
    
    dry_run = not args.execute
    if dry_run:
        print("\n==============================")
        print("!! DRY RUN MODE ACTIVE !!")
        print("No files will be modified.")
        print("==============================\n")

    files_modified = 0
    total_warnings = []

    for root, _, files in os.walk(args.target_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                modified, warnings = process_file(file_path, manifest, dry_run, args.backup)
                if modified:
                    files_modified += 1
                if warnings:
                    for w in warnings:
                        total_warnings.append(f"{file_path}: {w}")

    print("\n--- MIGRATION SUMMARY ---")
    print(f"Files needing changes: {files_modified}")
    print(f"Warnings / Manual Interventions Required: {len(total_warnings)}")
    for w in total_warnings:
        print(f"  ⚠ {w}")

    if not dry_run:
        print("\nMigration complete. PLEASE RUN VALIDATION:")
        print(f"  python -m compileall {args.target_dir}")
        print(f"  ruff check {args.target_dir}")
        print(f"  mypy {args.target_dir}")
        print(f"  pytest {args.target_dir}")

if __name__ == "__main__":
    main()
