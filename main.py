"""
VIREON Legacy CLI Entry Point.

Delegates execution to the new Coordinator-based command-line interface
in vireon.__main__. Provides full backward compatibility for legacy
options by auto-routing to the 'run' subcommand.
"""

import sys
import os

# Ensure the root package is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from vireon.__main__ import main

if __name__ == "__main__":
    # If no subcommand is specified, default to the legacy 'run' subcommand
    if len(sys.argv) == 1:
        sys.argv.insert(1, "run")
    elif sys.argv[1] not in ("run", "web", "info", "-h", "--help"):
        sys.argv.insert(1, "run")

    main()
