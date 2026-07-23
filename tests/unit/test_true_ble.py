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

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from vireon_lab.providers.protocols.ble.true_ble import TrueBLEClient

@pytest.mark.asyncio
async def test_true_ble_connect_success():
    with patch("vireon_lab.providers.protocols.ble.true_ble.BleakScanner.find_device_by_address", new_callable=AsyncMock) as mock_scanner:
        mock_device = MagicMock()
        mock_device.name = "TestDevice"
        mock_scanner.return_value = mock_device

        with patch("vireon_lab.providers.protocols.ble.true_ble.BleakClient", autospec=True) as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.connect = AsyncMock(return_value=True)
            mock_client_instance.is_connected = True

            client = TrueBLEClient("AA:BB:CC:DD:EE:FF")
            success = await client.connect()
            
            assert success is True
            assert client.is_connected is True
            mock_scanner.assert_called_once_with("AA:BB:CC:DD:EE:FF", timeout=10.0)
            mock_client_instance.connect.assert_called_once()

@pytest.mark.asyncio
async def test_true_ble_connect_failure():
    with patch("vireon_lab.providers.protocols.ble.true_ble.BleakScanner.find_device_by_address", new_callable=AsyncMock) as mock_scanner:
        mock_scanner.return_value = None

        client = TrueBLEClient("AA:BB:CC:DD:EE:FF")
        success = await client.connect()
        
        assert success is False
        assert client.is_connected is False
