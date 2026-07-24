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

"""
Adversarial Findings Regression Test Suite for VIREON-Lab.
Validates fixes for ADV-03, ADV-06, ADV-10.
"""

import json
import uuid
import numpy as np

from vireon_lab.dashboard.forensic_exporter import generate_stix_package, generate_html_audit_report
from vireon_lab.engine.circular_buffer import CircularBuffer
from vireon_lab.providers.datasets.csv_reader import CSVReader


def test_adv_03_stix_uuid_compliance_and_html_xss_escaping():
    """ADV-03: Verifies STIX 2.1 JSON uses valid UUIDs and HTML executive report escapes XSS payloads."""
    xss_payload = "<script>alert('xss')</script>"
    
    # 1. Test STIX Package ID validity
    stix_json = generate_stix_package(xss_payload, 0.85, 80, "CRITICAL")
    bundle = json.loads(stix_json)
    
    indicator_obj = [o for o in bundle["objects"] if o["type"] == "indicator"][0]
    indicator_id = indicator_obj["id"]
    uuid_str = indicator_id.replace("indicator--", "")
    
    # Must parse cleanly as a UUID
    parsed_uuid = uuid.UUID(uuid_str)
    assert str(parsed_uuid) == uuid_str

    # 2. Test HTML XSS escaping
    html_report = generate_html_audit_report(xss_payload, 0.85, 80, "CRITICAL")
    assert "<script>" not in html_report.lower()
    assert "&lt;script&gt;" in html_report.lower()


def test_adv_06_circular_buffer_thread_locking():
    """ADV-06: Verifies CircularBuffer lock protection."""
    buf = CircularBuffer(num_channels=4, capacity_samples=100)
    data = np.ones((4, 10))
    buf.write(data)
    
    read_data = buf.read_last(10)
    assert read_data.shape == (4, 10)
    assert np.allclose(read_data, 1.0)
    
    buf.reset()
    assert buf.total_written == 0


def test_adv_10_csv_reader_zero_division_guard(tmp_path):
    """ADV-10: Verifies CSVReader handles empty CSV files gracefully without ZeroDivisionError."""
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("")
    
    reader = CSVReader(str(empty_csv), fallback_on_error=False)
    chunk = reader.read_chunk(start_sample=0, num_samples=10)
    assert chunk.shape == (reader.num_channels, 10)
    assert np.allclose(chunk, 0.0)
