# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

# Ensure VIREON can be imported if run from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vireon.runtime.config import load_config
from vireon.runtime.coordinator import Coordinator

def main():
    # 1. Load the experiment TOML configuration
    config_path = os.path.join(os.path.dirname(__file__), "basic_experiment.toml")
    print(f"Loading configuration from {config_path}...")
    config = load_config(config_path)

    # 2. Ensure report output directory exists
    os.makedirs(os.path.dirname(config.output.report_prefix), exist_ok=True)

    # 3. Initialize the Coordinator
    coordinator = Coordinator(config)
    
    # 4. Setup and Run the virtual laboratory
    coordinator.setup()
    try:
        coordinator.run()
    except KeyboardInterrupt:
        pass
    finally:
        # 5. Teardown compiles the reports automatically
        coordinator.teardown()

if __name__ == "__main__":
    main()
