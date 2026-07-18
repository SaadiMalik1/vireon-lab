import os
import shutil
from pathlib import Path

BASE_DIR = Path("/home/ronin/Documents/n2")
VIREON_DIR = BASE_DIR / "VIREON"
SUFFIX_DIR = BASE_DIR / "VIREON_SUFFIX"
OLD_VIREON_DIR = BASE_DIR / "vireon"

# Create directories for VIREON (Professional Framework)
for d in [
    "src/vireon/core",
    "src/vireon/security",
    "src/vireon/validation",
    "src/vireon/engine",
    "src/vireon/sdk",
]:
    (VIREON_DIR / d).mkdir(parents=True, exist_ok=True)

# Create directories for VIREON_SUFFIX (Educational Platform)
for d in [
    "dashboard",
    "scenarios/attacks",
    "scenarios/attack_framework",
    "examples/firmware",
    "examples/clinical",
    "examples/ble",
    "examples/ids",
    "examples/physics",
    "examples/decoders",
    "docs/reference",
]:
    (SUFFIX_DIR / d).mkdir(parents=True, exist_ok=True)

# Stage 1: Delete Legacy Monolithic Files
legacy_files = [
    "core/coordinator.py",
    "core/coordinator_builder.py",
    "core/coordinator_callbacks.py",
    "core/twin.py",
]
for f in legacy_files:
    file_path = OLD_VIREON_DIR / f
    if file_path.exists():
        file_path.unlink()
        print(f"Deleted legacy file: {f}")

# Stage 2: Extract Runtime
core_files = [
    "orchestrator.py", "event_bus.py", "state_store.py", 
    "plugin_registry.py", "capability_engine.py"
]
for f in core_files:
    src = OLD_VIREON_DIR / "core" / f
    dst = VIREON_DIR / "src" / "vireon" / "core" / f
    if src.exists():
        shutil.move(src, dst)
        print(f"Moved {f} to VIREON/core")

security_files = [
    "authentication.py", "e2ee.py", "guardrails.py", "zta.py"
]
for f in security_files:
    src = OLD_VIREON_DIR / "core" / f
    dst = VIREON_DIR / "src" / "vireon" / "security" / f
    if src.exists():
        shutil.move(src, dst)
        print(f"Moved {f} to VIREON/security")

validation_files = [
    "validation.py", "compliance.py", "fuzzer.py", "sbom.py", 
    "redteam.py", "threat_intel.py", "spdf_auditor.py"
]
for f in validation_files:
    src = OLD_VIREON_DIR / "core" / f
    dst = VIREON_DIR / "src" / "vireon" / "validation" / f
    if src.exists():
        shutil.move(src, dst)
        print(f"Moved {f} to VIREON/validation")

engine_file = OLD_VIREON_DIR / "core" / "engine.py"
if engine_file.exists():
    shutil.move(engine_file, VIREON_DIR / "src" / "vireon" / "engine" / "engine.py")
    print("Moved engine.py to VIREON/engine")

# Stage 3: Extract SDK
if (OLD_VIREON_DIR / "sdk").exists():
    for item in (OLD_VIREON_DIR / "sdk").iterdir():
        shutil.move(item, VIREON_DIR / "src" / "vireon" / "sdk" / item.name)
    print("Moved vireon/sdk contents to VIREON/sdk")

sdk_files = ["interfaces.py", "protocol.py", "data_provider.py"]
for f in sdk_files:
    src = OLD_VIREON_DIR / "core" / f
    dst = VIREON_DIR / "src" / "vireon" / "sdk" / f
    if src.exists():
        shutil.move(src, dst)
        print(f"Moved {f} to VIREON/sdk")

# Stage 4: Move Educational Content
moves = [
    (OLD_VIREON_DIR / "dashboard", SUFFIX_DIR / "dashboard"),
    (OLD_VIREON_DIR / "attacks", SUFFIX_DIR / "scenarios" / "attacks"),
    (OLD_VIREON_DIR / "core" / "attack", SUFFIX_DIR / "scenarios" / "attack_framework"),
    (OLD_VIREON_DIR / "plugins" / "firmware", SUFFIX_DIR / "examples" / "firmware"),
    (OLD_VIREON_DIR / "plugins" / "clinical", SUFFIX_DIR / "examples" / "clinical"),
    (OLD_VIREON_DIR / "plugins" / "ble", SUFFIX_DIR / "examples" / "ble"),
    (OLD_VIREON_DIR / "core" / "detection.py", SUFFIX_DIR / "examples" / "ids" / "detection.py"),
    (OLD_VIREON_DIR / "core" / "physics.py", SUFFIX_DIR / "examples" / "physics" / "physics.py"),
    (OLD_VIREON_DIR / "core" / "dynamics.py", SUFFIX_DIR / "examples" / "physics" / "dynamics.py"),
    (OLD_VIREON_DIR / "core" / "ml_decoder.py", SUFFIX_DIR / "examples" / "decoders" / "ml_decoder.py"),
    (OLD_VIREON_DIR / "core" / "reference_credits", SUFFIX_DIR / "docs" / "reference"),
]

for src, dst in moves:
    if src.exists():
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            shutil.rmtree(src)
        else:
            shutil.move(src, dst)
        print(f"Moved {src.name} to {dst}")

# Stage 5: Fix Imports
def rewrite_imports(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    content = f.read()
                
                # Replace relative imports that are now broken due to extraction
                # e.g., 'from ..core' -> 'from vireon.core'
                new_content = content.replace("from ..core", "from vireon.core")
                new_content = new_content.replace("from .core", "from vireon.core")
                new_content = new_content.replace("from vireon.core.twin", "from vireon.core.state_store")
                
                if new_content != content:
                    with open(file_path, "w") as f:
                        f.write(new_content)
                    print(f"Rewrote imports in {file_path}")

print("Rewriting imports in VIREON_SUFFIX...")
rewrite_imports(SUFFIX_DIR)

print("Migration layout generated successfully. To complete, verify paths and create the respective pyproject.toml files.")

