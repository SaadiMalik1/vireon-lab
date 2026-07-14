import numpy as np
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from vireon.core.security import NeuroSignalAssuranceEngine
class MockTwin:
    def get_sim_clock(self): return 1.0
    stimulation_enabled = False
    stimulation_amplitude_ma = 0.0
    autonomic_pupil_dilation_mm = 3.0

ids = NeuroSignalAssuranceEngine(MockTwin(), None)
ids.rms_high_threshold = 100
ids.analyze_signal(np.random.normal(0, 500, (8, 256)))
