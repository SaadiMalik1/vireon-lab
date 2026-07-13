from vireon.plugins.clinical.qif_atlas import QIFAtlas
from vireon.core.twin import DigitalTwin
from vireon.plugins.clinical.dbs_emulator import ClosedLoopDBSController
import numpy as np

def test_qif_atlas_lookup():
    result = QIFAtlas.evaluate_clinical_impact("phase_shift", duration_sec=120)
    assert result["dsm5_diagnosis"] == "F32_MAJOR_DEPRESSION"
    assert result["niss_score"] == 10.0
    assert result["iso14971_severity"] == "CATASTROPHIC"

def test_qif_twin_integration():
    twin = DigitalTwin()
    controller = ClosedLoopDBSController(twin)
    
    # Simulate attack active on feedback buffer
    data = np.zeros((8, 250))
    # Make beta power high
    t = np.arange(250) / 250.0
    data[0, :] = 100.0 * np.sin(2 * np.pi * 20.0 * t)
    
    controller.process_lfp(data, eeg_channels=[0], sample_rate=250, attack_active=True)
    
    state = twin.get_state()
    assert state["dsm5_diagnosis"] == "F32_MAJOR_DEPRESSION"
    assert state["hazard_state"] == "PATHOLOGICAL_SYNCHRONIZATION"
