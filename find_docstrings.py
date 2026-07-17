import ast
import os
import glob

def check_docstrings(directory):
    missing = []
    for filepath in glob.glob(os.path.join(directory, "**/*.py"), recursive=True):
        with open(filepath, "r") as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    missing.append(f"{filepath}:{node.lineno} {node.name}")
    return missing

missing = check_docstrings("/home/ronin/Documents/n2/vireon/core")
for m in missing:
    print(m)
