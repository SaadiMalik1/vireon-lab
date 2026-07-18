import os
import libcst as cst

class VireonImportTransformer(cst.CSTTransformer):
    """
    Transforms relative imports and legacy vireon imports 
    into absolute vireon.core / vireon.sdk imports.
    """
    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom:
        # Change `from ..core import X` -> `from vireon.core import X`
        if updated_node.module is None and len(updated_node.relative) >= 1:
            # We assume any relative import going up a level was trying to reach core or sdk
            new_module = cst.Attribute(
                value=cst.Name("vireon"),
                attr=cst.Name("core")
            )
            return updated_node.with_changes(
                module=new_module,
                relative=[]
            )
            
        # Change `from vireon.core.twin import DigitalTwin` -> `from vireon.core.state_store import StateStore`
        if updated_node.module and getattr(updated_node.module, "value", None):
            module_name = ""
            if isinstance(updated_node.module, cst.Attribute):
                if getattr(updated_node.module.value, "value", None) == "vireon" and getattr(updated_node.module.value, "attr", None) == "core":
                    if getattr(updated_node.module, "attr", None) == "twin":
                        # Rewrite to state_store
                        new_module = cst.Attribute(
                            value=cst.Attribute(value=cst.Name("vireon"), attr=cst.Name("core")),
                            attr=cst.Name("state_store")
                        )
                        # Also replace DigitalTwin with StateStore in the imported names
                        new_names = []
                        for name in updated_node.names:
                            if getattr(name.name, "value", None) == "DigitalTwin":
                                new_names.append(name.with_changes(name=cst.Name("StateStore")))
                            else:
                                new_names.append(name)
                                
                        return updated_node.with_changes(module=new_module, names=new_names)
        
        return updated_node

def refactor_file(file_path):
    with open(file_path, "r") as f:
        source = f.read()
    
    tree = cst.parse_module(source)
    transformer = VireonImportTransformer()
    modified_tree = tree.visit(transformer)
    
    with open(file_path, "w") as f:
        f.write(modified_tree.code)

def main():
    target_dirs = ["vireon_lab/dashboard", "vireon_lab/examples", "vireon_lab/scenarios"]
    for d in target_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py"):
                    refactor_file(os.path.join(root, file))
                    print(f"Refactored AST imports in {os.path.join(root, file)}")

if __name__ == "__main__":
    main()
