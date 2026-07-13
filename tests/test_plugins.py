import unittest
import numpy as np
import tempfile
import os
from vireon.core.twin import DigitalTwin
from vireon.plugins.datasets.edf_reader import MockEEGReader, EDFReader
from vireon.plugins.datasets.csv_reader import CSVReader
from vireon.plugins.devices.synthetic import SyntheticBoardWrapper
from vireon.plugins.devices.pieeg import PiEEGBoardWrapper
from vireon.plugins.clinical.closed_loop import ClosedLoopSimulator

class TestDatasetPlugins(unittest.TestCase):
    def test_mock_eeg_reader(self):
        reader = MockEEGReader(sample_rate=250, num_channels=8)
        self.assertEqual(reader.sample_rate, 250)
        self.assertEqual(reader.num_channels, 8)
        
        chunk = reader.read_chunk(start_sample=0, num_samples=100)
        self.assertEqual(chunk.shape, (8, 100))
        # Ensure it contains signal (not flat zeros)
        self.assertGreater(np.var(chunk), 0.1)

    def test_csv_reader_fallback(self):
        # Should fall back to mock reader if file not found
        reader = CSVReader("non_existent_file.csv", sample_rate=250, fallback_on_error=True)
        self.assertEqual(reader.num_channels, 8)
        chunk = reader.read_chunk(0, 50)
        self.assertEqual(chunk.shape, (8, 50))

    def test_csv_reader_file(self):
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
            tmp.write("1.0,2.0,3.0\n4.0,5.0,6.0\n7.0,8.0,9.0\n10.0,11.0,12.0\n")
            tmp_path = tmp.name

        try:
            # CSV has 3 columns, 4 rows (transposed to 3 channels, 4 samples)
            reader = CSVReader(tmp_path, sample_rate=100, fallback_on_error=False)
            self.assertEqual(reader.num_channels, 3)
            chunk = reader.read_chunk(0, 2)
            self.assertEqual(chunk.shape, (3, 2))
            self.assertEqual(chunk[0, 0], 1.0)
            self.assertEqual(chunk[1, 0], 2.0)
        finally:
            os.remove(tmp_path)

class TestDevicePlugins(unittest.TestCase):
    def test_synthetic_wrapper(self):
        wrapper = SyntheticBoardWrapper()
        board = wrapper.get_board()
        self.assertIsNotNone(board)
        self.assertEqual(wrapper.get_eeg_channels(), [1, 2, 3, 4, 5, 6, 7, 8])

    def test_pieeg_wrapper(self):
        wrapper = PiEEGBoardWrapper()
        board = wrapper.get_board()
        self.assertIsNotNone(board)
        self.assertEqual(wrapper.get_eeg_channels(), [1, 2, 3, 4, 5, 6, 7, 8])

class TestClinicalPlugins(unittest.TestCase):
    def setUp(self):
        self.twin = DigitalTwin(num_channels=8)
        self.simulator = ClosedLoopSimulator(self.twin)
        self.eeg_channels = [0, 1, 2, 3, 4, 5, 6, 7]
        self.sample_rate = 250

    def test_clinical_nominal_flow(self):
        # Nominal signals (some clean oscillations)
        t = np.arange(100) / 250.0
        data = np.zeros((8, 100))
        for ch in range(8):
            data[ch, :] = 10.0 * np.sin(2 * np.pi * 10.0 * t)
            
        self.simulator.process_signal(data, self.eeg_channels, self.sample_rate)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["current_status"], "Nominal")
        self.assertFalse(summary["alert_active"])
        self.assertTrue(summary["therapy_enabled"])
        self.assertEqual(summary["stimulation_amplitude_ma"], 2.0)

    def test_clinical_link_outage(self):
        self.twin.set_connection(False)
        data = np.zeros((8, 100))
        self.simulator.process_signal(data, self.eeg_channels, self.sample_rate)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["current_status"], "Link Outage")
        self.assertTrue(summary["alert_active"])
        self.assertFalse(summary["therapy_enabled"])

    def test_clinical_high_impedance_cutoff(self):
        # Spike impedance to extreme value on channel 2
        self.twin.update_impedance(2, 60.0)
        data = np.zeros((8, 100))
        self.simulator.process_signal(data, self.eeg_channels, self.sample_rate)
        
        summary = self.simulator.get_clinical_summary()
        self.assertEqual(summary["current_status"], "High Impedance Alert")
        self.assertTrue(summary["alert_active"])
        self.assertFalse(summary["therapy_enabled"])
        self.assertEqual(summary["stimulation_amplitude_ma"], 0.0)

if __name__ == "__main__":
    unittest.main()
