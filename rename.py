import os
import re

directories = ['vireon', 'tests', 'examples', 'scripts', 'docs']
files_to_update = ['pyproject.toml', 'Dockerfile', 'mkdocs.yml', 'README.md', 'runemate/python_ext/Cargo.toml', 'runemate/python_ext/src/lib.rs', 'datasets/validation_report.json', 'vireon/__main__.py']

replacements = [
    (r'\bimport neuroshield\b', 'import vireon'),
    (r'\bfrom neuroshield\b', 'from vireon'),
    (r'\bneuroshield\.', 'vireon.'),
    (r'\bneuroshield\b', 'vireon'),
    (r'\bNeuroShield\b', 'VIREON'),
    (r'\bneuroshield_runemate\b', 'vireon_runemate')
]

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    new_content = content
    for pattern, repl in replacements:
        new_content = re.sub(pattern, repl, new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root_dir in directories:
    if os.path.exists(root_dir):
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.py', '.md', '.toml', '.yml', '.yaml', '.json')):
                    process_file(os.path.join(root, file))

for file in files_to_update:
    if os.path.exists(file):
        process_file(file)

print("Done.")
