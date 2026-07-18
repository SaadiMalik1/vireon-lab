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
import json
import re
from typing import Dict, Any, List, Optional
from vireon_lab.providers.datasets.edf_reader import EDFReader
from vireon_lab.providers.datasets.csv_reader import CSVReader
from vireon_lab.providers.datasets.fif_reader import FIFReader
from vireon_lab.providers.datasets.mne_reader import MNEReader


class DatasetIndexer:
    """
    Catalog and indexing manager for neural datasets.

    Scans directories for supported files (.edf, .bdf, .csv, .fif), parses
    BIDS metadata from folder structures and filenames, and caches the result
    in a JSON catalog for fast lookup.
    """

    SUPPORTED_EXTENSIONS = {".edf", ".bdf", ".csv", ".fif", ".vhdr", ".set"}

    def __init__(self, target_directory: str):
        self.target_directory = os.path.abspath(target_directory)
        self.index_file = os.path.join(self.target_directory, "dataset_index.json")
        self.catalog: Dict[str, Dict[str, Any]] = {}
        self.load_index()

    def load_index(self) -> None:
        """Load the catalog from the JSON file if it exists."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r") as f:
                    self.catalog = json.load(f)
            except Exception as e:
                print(f"[DatasetIndexer] Warning: Failed to load index file: {e}")
                self.catalog = {}
        else:
            self.catalog = {}

    def save_index(self) -> None:
        """Save the catalog to the JSON file."""
        os.makedirs(self.target_directory, exist_ok=True)
        try:
            with open(self.index_file, "w") as f:
                json.dump(self.catalog, f, indent=4)
        except Exception as e:
            print(f"[DatasetIndexer] Error saving index file: {e}")

    def scan(self, force: bool = False) -> List[Dict[str, Any]]:
        """
        Scan the target directory recursively, adding new files and updating existing ones.

        Args:
            force: If True, re-read metadata from all files even if already indexed.
        """
        if not os.path.exists(self.target_directory):
            return []

        updated = False
        scanned_files = set()

        for root, _, files in os.walk(self.target_directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.target_directory)
                scanned_files.add(rel_path)

                # Skip if already indexed unless force is True
                if rel_path in self.catalog and not force:
                    continue

                print(f"[DatasetIndexer] Indexing: {rel_path}")
                try:
                    metadata = self._extract_file_metadata(full_path, ext)
                    # Parse BIDS layout patterns
                    bids_info = self._parse_bids_structure(rel_path)
                    metadata.update(bids_info)

                    self.catalog[rel_path] = metadata
                    updated = True
                except Exception as e:
                    print(f"[DatasetIndexer] Failed to index {rel_path}: {e}")

        # Remove deleted files from catalog
        to_remove = [k for k in self.catalog if k not in scanned_files]
        if to_remove:
            for k in to_remove:
                del self.catalog[k]
            updated = True

        if updated:
            self.save_index()

        return self.list_datasets()

    def list_datasets(self) -> List[Dict[str, Any]]:
        """Return a list of all indexed datasets with their relative paths."""
        return [
            {"relative_path": k, **v}
            for k, v in self.catalog.items()
        ]

    def get_dataset(self, rel_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific dataset path."""
        return self.catalog.get(rel_path)

    def _extract_file_metadata(self, path: str, ext: str) -> Dict[str, Any]:
        """Load the file with the appropriate reader (no fallback) to fetch metadata."""
        reader: Any = None
        if ext in (".edf", ".bdf"):
            reader = EDFReader(path, fallback_on_error=False)
        elif ext == ".csv":
            reader = CSVReader(path, fallback_on_error=False)
        elif ext == ".fif":
            reader = FIFReader(path, fallback_on_error=False)
        elif ext in (".vhdr", ".set"):
            reader = MNEReader(path, fallback_on_error=False)
        else:
            raise ValueError(f"Unsupported extension: {ext}")

        # Keep metadata simple and serializable
        meta = dict(reader.metadata)
        meta["sample_rate"] = reader.sample_rate
        meta["num_channels"] = reader.num_channels
        meta["channel_names"] = reader.channel_names
        meta["file_size_bytes"] = os.path.getsize(path)
        return meta

    def _parse_bids_structure(self, rel_path: str) -> Dict[str, Any]:
        """Extract BIDS tokens (sub, ses, task, run) from directory path or filename."""
        bids: Dict[str, Any] = {
            "is_bids": False,
            "subject": None,
            "session": None,
            "task": None,
            "run": None
        }

        # Common BIDS tokens matching regex
        sub_match = re.search(r'sub-([a-zA-Z0-9]+)', rel_path)
        ses_match = re.search(r'ses-([a-zA-Z0-9]+)', rel_path)
        task_match = re.search(r'task-([a-zA-Z0-9]+)', rel_path)
        run_match = re.search(r'run-([0-9]+)', rel_path)

        if sub_match:
            bids["is_bids"] = True
            bids["subject"] = sub_match.group(1)
        if ses_match:
            bids["session"] = ses_match.group(1)
        if task_match:
            bids["task"] = task_match.group(1)
        if run_match:
            bids["run"] = int(run_match.group(1))

        return bids
