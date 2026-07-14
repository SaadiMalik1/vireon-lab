import os
import re

files_to_update = [
    'pyproject.toml',
    'neuro_dsl/python_ext/Cargo.toml',
    'neuro_dsl/python_ext/src/lib.rs',
    'vireon/__main__.py',
    'vireon/core/engine.py',
    'vireon/core/sbom.py',
    'vireon/mcp_server.py',
    'vireon/plugins/reports/web_server.py',
    'vireon/plugins/reports/web/app.js',
    'vireon/plugins/reports/web/index.html',
    'README.md',
    'docs/index.md',
    'docs/architecture.md',
    'docs/FAQ.md',
    'docs/threat-model/attack-surface.md',
    'knowledge/neuroscience/dbs.md',
    'CODEOWNERS',
    'Dockerfile',
    'CONTRIBUTING.md',
    'SECURITY.md',
    'INSTALL.md',
    'rename.py'
]

replacements = [
    (r'runemate', 'neuro_dsl'),
    (r'Runemate', 'NeuroDSL'),
    (r'RUNEMATE', 'NEURO_DSL')
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    for old, new in replacements:
        content = re.sub(old, new, content)
        
    with open(filepath, 'w') as f:
        f.write(content)
        print(f"Updated {filepath}")
