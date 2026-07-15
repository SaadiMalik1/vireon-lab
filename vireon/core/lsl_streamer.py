import json
import numpy as np

class LSLStreamer:
    """
    Lab Streaming Layer (LSL) backend for VIREON.
    Broadcasts synthetic LFP/EEG data and security telemetry to any
    LSL-compatible frontend (OpenBCI GUI, OpenViBE, BrainFlow, etc.)
    """
    def __init__(self, num_channels=4, srate=250.0):
        try:
            from pylsl import StreamInfo, StreamOutlet
        except ImportError:
            raise ImportError("pylsl is not installed. Run 'pip install pylsl' to use LSL Streaming.")

        self.num_channels = num_channels
        self.srate = srate
        
        # Outlet 1: The Raw EEG/LFP Signal (float32)
        info_eeg = StreamInfo(
            name='VIREON_EEG',
            type='EEG',
            channel_count=num_channels,
            nominal_srate=srate,
            channel_format='float32',
            source_id='vireon_engine_01'
        )
        self.outlet_eeg = StreamOutlet(info_eeg)
        
        # Outlet 2: The Security/Telemetry stream (String/JSON)
        info_telemetry = StreamInfo(
            name='VIREON_Telemetry',
            type='Markers',
            channel_count=1,
            nominal_srate=0, # Irregular rate
            channel_format='string',
            source_id='vireon_telemetry_01'
        )
        self.outlet_telemetry = StreamOutlet(info_telemetry)
        
        print(f"[LSL] Started VIREON_EEG ({num_channels}ch @ {srate}Hz)")
        print("[LSL] Started VIREON_Telemetry (Markers)")

    def push_eeg_chunk(self, chunk_data: np.ndarray):
        """
        Push a chunk of EEG data.
        chunk_data shape: (num_channels, num_samples)
        """
        # pylsl expects data as (num_samples, num_channels)
        if chunk_data.shape[0] == self.num_channels:
            data_T = chunk_data.T.tolist()
            self.outlet_eeg.push_chunk(data_T)
        else:
            self.outlet_eeg.push_chunk(chunk_data.tolist())

    def push_telemetry(self, telemetry_dict: dict):
        """
        Push security state, NISS scores, or hardware states as JSON string marker.
        """
        payload = json.dumps(telemetry_dict)
        self.outlet_telemetry.push_sample([payload])
