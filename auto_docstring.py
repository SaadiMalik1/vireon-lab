import ast
import os
import glob
import astor

def camel_to_spaces(name):
    import re
    return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', name)

def get_default_docstring(name, is_class):
    if is_class:
        if name.startswith("I") and name[1].isupper():
            return f"Interface for {camel_to_spaces(name[1:])}."
        return f"{camel_to_spaces(name)}."
    else:
        if name.startswith("__"):
            return "Built-in method."
        if name.startswith("_"):
            return "Internal method."
        return f"{name.replace('_', ' ').capitalize()}."

def add_docstrings(directory):
    for filepath in glob.glob(os.path.join(directory, "**/*.py"), recursive=True):
        with open(filepath, "r") as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue
        modified = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    doc_text = get_default_docstring(node.name, isinstance(node, ast.ClassDef))
                    doc_node = ast.Expr(value=ast.Constant(value=doc_text))
                    node.body.insert(0, doc_node)
                    modified = True
        
        if modified:
            with open(filepath, "w") as f:
                f.write(astor.to_source(tree))
            print(f"Added docstrings to {filepath}")

if __name__ == "__main__":
    add_docstrings("/home/ronin/Documents/n2/vireon/core")
