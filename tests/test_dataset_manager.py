import unittest
import os
import tempfile
import numpy as np

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vireon.plugins.datasets.mock_reader import MockEEGReader
from vireon.plugins.datasets.edf_reader import EDFReader
from vireon.plugins.datasets.csv_reader import CSVReader
from vireon.plugins.datasets.fif_reader import FIFReader
from vireon.plugins.datasets.dataset_index import DatasetIndexer


class TestDatasetManagement(unittest.TestCase):
    """Tests for dataset readers and the directory catalog indexer."""

    def test_mock_eeg_reader(self):
        reader = MockEEGReader(sample_rate=100, num_channels=4)
        self.assertEqual(reader.sample_rate, 100)
        self.assertEqual(reader.num_channels, 4)
        self.assertEqual(reader.total_samples, -1)
        self.assertEqual(reader.duration_sec, -1.0)
        self.assertEqual(len(reader.channel_names), 4)
        self.assertFalse(reader.metadata["subject_id"] == "")
        self.assertTrue(reader.supports_seeking)

        # Test chunk generation
        data = reader.read_chunk(start_sample=0, num_samples=50)
        self.assertEqual(data.shape, (4, 50))
        # Ensure non-trivial values
        self.assertNotEqual(np.sum(np.abs(data)), 0.0)

    def test_edf_reader_fallback(self):
        # Invalid file should fall back to mock reader
        reader = EDFReader("nonexistent_file.edf", fallback_on_error=True)
        self.assertIsNotNone(reader.mock_reader)
        self.assertEqual(reader.sample_rate, 250)
        self.assertEqual(reader.num_channels, 8)

        # Seek should execute on mock reader
        reader.seek(100)

    def test_csv_reader_wrapping(self):
        # Create a temp CSV file
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("1.0,2.0,3.0\n4.0,5.0,6.0\n7.0,8.0,9.0\n10.0,11.0,12.0\n")
            temp_name = f.name

        try:
            # CSV has 4 samples, 3 channels (since loadtxt reads rows as samples and we transpose)
            # Row 0: 1.0, 2.0, 3.0 -> Col 0: 1, 4, 7, 10; Col 1: 2, 5, 8, 11; Col 2: 3, 6, 9, 12
            reader = CSVReader(temp_name, sample_rate=200, fallback_on_error=False)
            self.assertEqual(reader.num_channels, 3)
            self.assertEqual(reader.total_samples, 4)
            self.assertEqual(reader.duration_sec, 4.0 / 200.0)

            # Test simple read
            chunk = reader.read_chunk(start_sample=0, num_samples=2)
            self.assertEqual(chunk.shape, (3, 2))
            np.testing.assert_array_almost_equal(chunk[:, 0], [1.0, 2.0, 3.0])
            np.testing.assert_array_almost_equal(chunk[:, 1], [4.0, 5.0, 6.0])

            # Test wrapping read (start=3, count=3 -> indices [3, 0, 1])
            chunk_wrap = reader.read_chunk(start_sample=3, num_samples=3)
            self.assertEqual(chunk_wrap.shape, (3, 3))
            np.testing.assert_array_almost_equal(chunk_wrap[:, 0], [10.0, 11.0, 12.0])
            np.testing.assert_array_almost_equal(chunk_wrap[:, 1], [1.0, 2.0, 3.0])
            np.testing.assert_array_almost_equal(chunk_wrap[:, 2], [4.0, 5.0, 6.0])
        finally:
            os.remove(temp_name)

    def test_fif_reader_fallback(self):
        # Invalid file should fall back to mock
        reader = FIFReader("nonexistent_file.fif", fallback_on_error=True)
        self.assertIsNotNone(reader.mock_reader)
        self.assertEqual(reader.sample_rate, 250)
        self.assertEqual(reader.num_channels, 8)

    def test_dataset_indexer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create a dummy CSV file matching BIDS naming convention
            # sub-01/ses-test/eeg/sub-01_ses-test_task-rest_run-1_eeg.csv
            bids_dir = os.path.join(tmpdir, "sub-01", "ses-test", "eeg")
            os.makedirs(bids_dir)
            csv_path = os.path.join(bids_dir, "sub-01_ses-test_task-rest_run-1_eeg.csv")
            
            with open(csv_path, "w") as f:
                f.write("1,2\n3,4\n5,6\n")

            # 2. Instantiate indexer
            indexer = DatasetIndexer(tmpdir)
            self.assertEqual(len(indexer.catalog), 0)

            # 3. Scan directory
            datasets = indexer.scan()
            self.assertEqual(len(datasets), 1)

            entry = datasets[0]
            self.assertEqual(entry["subject"], "01")
            self.assertEqual(entry["session"], "test")
            self.assertEqual(entry["task"], "rest")
            self.assertEqual(entry["run"], 1)
            self.assertTrue(entry["is_bids"])
            self.assertEqual(entry["num_channels"], 2)
            self.assertEqual(entry["total_samples"], 3)

            # 4. Verify index file was saved
            self.assertTrue(os.path.exists(indexer.index_file))

            # 5. Reload indexer and verify catalog loaded from cache
            indexer2 = DatasetIndexer(tmpdir)
            self.assertEqual(len(indexer2.catalog), 1)
            self.assertIn(entry["relative_path"], indexer2.catalog)


if __name__ == "__main__":
    unittest.main()
