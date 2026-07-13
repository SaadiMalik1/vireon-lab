import time
import threading
import numpy as np
from typing import Optional, List, Callable
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

from neuroshield.core.twin import DigitalTwin
from neuroshield.core.attack import SignalAttackEngine


class ReplayEngine:
    """
    Core simulation loop that drives data through the NeuroShield pipeline.

    Supports:
    - Deterministic seeding for reproducible experiments
    - Pause/resume control
    - Configurable playback speed multiplier
    - Dataset looping on exhaustion
    - Monotonic simulation clock (not wall-clock)
    """

    def __init__(self,
                 twin: DigitalTwin,
                 attack_engine: SignalAttackEngine,
                 device_wrapper=None,
                 dataset_reader=None,
                 seed: Optional[int] = None,
                 loop_dataset: bool = True,
                 ids=None,
                 ti=None,
                 red_team_engine=None):
        self.twin = twin
        self.attack_engine = attack_engine
        self.device_wrapper = device_wrapper
        self.dataset_reader = dataset_reader
        self.ids = ids
        self.ti = ti
        self.red_team_engine = red_team_engine

        self.last_anomaly_score = 0.0
        self.active_attack = "none"

        try:
            import neuroshield_runemate
            self.scribe = neuroshield_runemate.PyScribe()
            print("[ReplayEngine] Runemate Scribe VM successfully loaded.")
        except ImportError:
            self.scribe = None
            print("[ReplayEngine] Runemate Scribe VM not available (requires compilation with maturin).")

        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Callbacks that receive (mutated_data, eeg_channels, sample_rate)
        self.callbacks: List[Callable[[np.ndarray, List[int], int], None]] = []

        # Read position for dataset replay
        self.dataset_sample_position = 0

        # Deterministic RNG (None = use global numpy random state for backward compat)
        self._seed = seed
        self._rng: Optional[np.random.Generator] = None
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        # Pause/resume
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Start unpaused

        # Speed multiplier (1.0 = real-time, 2.0 = double speed, 0.5 = half speed)
        self._speed_multiplier = 1.0

        # Dataset looping
        self._loop_dataset = loop_dataset

        # Simulation clock (monotonic, incremented by interval each tick)
        self._sim_clock = 0.0

        # Executor for running callbacks without blocking the timing loop
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        
        self._buffer_lock = threading.Lock()

    @property
    def rng(self) -> np.random.Generator:
        """Return the deterministic RNG if seeded, or a default one."""
        if self._rng is None:
            self._rng = np.random.default_rng()
        return self._rng

    @property
    def sim_clock(self) -> float:
        """Current simulation time in seconds."""
        return self._sim_clock

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def speed(self) -> float:
        return self._speed_multiplier

    def add_callback(self, callback: Callable[[np.ndarray, List[int], int], None]):
        self.callbacks.append(callback)

    def set_speed(self, multiplier: float):
        """Set playback speed. 1.0 = real-time, 2.0 = double, 0.5 = half."""
        self._speed_multiplier = max(0.1, min(100.0, multiplier))

    def pause(self):
        """Pause the simulation loop."""
        self._paused = True
        self._pause_event.clear()

    def resume(self):
        """Resume a paused simulation loop."""
        self._paused = False
        self._pause_event.set()

    def start(self, interval_sec: float = 0.1):
        if self.running:
            return

        self.running = True
        self._sim_clock = 0.0
        self.twin.set_sim_clock(0.0)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.thread = threading.Thread(target=self._loop, args=(interval_sec,), daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        # Unblock pause if paused
        self._pause_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def _loop(self, interval_sec: float):
        # Determine sample rate and channels
        sr = self.twin.sample_rate
        num_channels = self.twin.num_channels

        # EEG channels indices (normally 0 to num_channels-1, or specified by device)
        if self.device_wrapper is not None:
            eeg_channels = self.device_wrapper.get_eeg_channels()
            board = self.device_wrapper.get_board()
            # Start streaming
            try:
                if hasattr(self.device_wrapper, "start_stream"):
                    self.device_wrapper.start_stream()
                else:
                    if board and not board.is_prepared():
                        board.prepare_session()
                    if board and board.is_prepared():
                        board.start_stream()
            except Exception as e:
                logger.error("Warning starting board stream", exc_info=True)
        else:
            eeg_channels = list(range(num_channels))
            board = None

        num_samples_per_chunk = int(sr * interval_sec)
        if num_samples_per_chunk <= 0:
            num_samples_per_chunk = 1

        last_time = time.time()

        while self.running:
            # Block if paused
            self._pause_event.wait()
            if not self.running:
                break

            now = time.time()
            elapsed = now - last_time

            # Rate limiting sleep adjusted by speed multiplier
            effective_interval = interval_sec / self._speed_multiplier
            sleep_time = effective_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
                now = time.time()

            last_time = now

            # Advance simulation clock (simulating 100 ppm oscillator clock drift & jitter)
            drift = self.rng.uniform(-1.0, 1.0) * (interval_sec * 0.0001)
            self._sim_clock += interval_sec + drift
            self.twin.set_sim_clock(self._sim_clock)

            # Fetch data chunk
            raw_data = None
            self._current_buffer = None

            if self.device_wrapper is not None and hasattr(self.device_wrapper, 'read_chunk'):
                try:
                    raw_data = self.device_wrapper.read_chunk(0, num_samples_per_chunk)
                except Exception as e:
                    logger.error("Device wrapper read error", exc_info=True)
                    raw_data = np.full((max(eeg_channels) + 1, num_samples_per_chunk), np.nan)
                    
            elif board is not None:
                try:
                    # Fetch from BrainFlow board
                    data_chunk = board.get_board_data()
                    if data_chunk.size > 0:
                        raw_data = data_chunk
                    else:
                        raw_data = np.full((max(eeg_channels) + 1, num_samples_per_chunk), np.nan)
                except Exception as e:
                    logger.error("Board read error", exc_info=True)
                    raw_data = np.full((max(eeg_channels) + 1, num_samples_per_chunk), np.nan)

            elif self.dataset_reader is not None:
                # Fetch from Dataset Reader
                try:
                    raw_data = self.dataset_reader.read_chunk(self.dataset_sample_position, num_samples_per_chunk)
                    self.dataset_sample_position += num_samples_per_chunk
                except Exception as e:
                    # End of file or read error
                    if self._loop_dataset:
                        self.dataset_sample_position = 0
                        try:
                            raw_data = self.dataset_reader.read_chunk(0, num_samples_per_chunk)
                            self.dataset_sample_position = num_samples_per_chunk
                        except Exception:
                            raw_data = np.full((num_channels, num_samples_per_chunk), np.nan)
                    else:
                        print(f"[ReplayEngine] Dataset exhausted, stopping.")
                        self.running = False
                        break

            else:
                # No source configured, propagate NaN to signify absence of data rather than fabricating noise
                raw_data = np.full((num_channels, num_samples_per_chunk), np.nan)

            # Ensure raw_data shape is correct (channels, samples)
            if raw_data is not None and len(raw_data.shape) == 2:
                # Apply attacks
                mutated_data = self.attack_engine.apply_attacks(raw_data, eeg_channels, sr)
                
                with self._buffer_lock:
                    self._current_buffer = mutated_data

                # Run IDS if present
                if self.ids and mutated_data.shape[1] > 0:
                    # Feed mean of the chunk to IDS for simplicity
                    features = np.mean(mutated_data[:8, :], axis=1)
                    if len(features) == 8:
                        self.last_anomaly_score = self.ids.detect(features)
                        
                        # Update twin clinical state based on anomaly score
                        if self.last_anomaly_score > self.ids.threshold:
                            self.twin.set_clinical_alert(True, "IDS Anomaly Detected")
                        else:
                            self.twin.set_clinical_alert(False, "Nominal")

                # Run Red Team feedback loop
                if self.red_team_engine:
                    self.red_team_engine.tick(self.last_anomaly_score, self.ids.threshold if self.ids else 1.0)

                # Check connection status in digital twin
                if self.twin.connected:
                    # Run scribe VM if available
                    if self.scribe:
                        flattened = mutated_data.flatten().tolist()
                        try:
                            # Step the VM with current data
                            # The VM can observe the data and possibly manipulate therapy parameters
                            _ = self.scribe.execute_step(flattened)
                        except Exception as e:
                            logger.error("Scribe VM execution error", exc_info=True)

                    # Invoke clinical simulation callbacks concurrently to avoid GIL starvation
                    for cb in self.callbacks:
                        if self._executor:
                            self._executor.submit(cb, mutated_data, eeg_channels, sr)
            else:
                print("[ReplayEngine] Received invalid shape or empty data.")

        # Cleanup loop resources
        if self.device_wrapper is not None and hasattr(self.device_wrapper, "stop_stream"):
            try:
                self.device_wrapper.stop_stream()
            except Exception as e:
                logger.error("Error stopping device stream", exc_info=True)
        elif board is not None:
            try:
                board.stop_stream()
                board.release_session()
            except Exception as e:
                logger.error("Error releasing board session", exc_info=True)

    def get_buffer(self) -> Optional[np.ndarray]:
        with self._buffer_lock:
            return getattr(self, "_current_buffer", None)

    def inject_attack(self, attack_name: str):
        """Used by the dashboard to inject attacks."""
        self.active_attack = attack_name
        # Clear existing
        with self.attack_engine.lock:
            self.attack_engine.modifiers.clear()
            
        if attack_name == "noise":
            from neuroshield.core.attack import NoiseInjectionAttack
            self.attack_engine.add_modifier(NoiseInjectionAttack(target_channels=[0, 1]))
        elif attack_name == "drift":
            from neuroshield.core.attack import SignalDriftAttack
            self.attack_engine.add_modifier(SignalDriftAttack(target_channels=[0, 1]))
        elif attack_name == "temporal_evasion":
            from neuroshield.core.attack import TemporalEvasionAttack
            self.attack_engine.add_modifier(TemporalEvasionAttack(target_channels=[0, 1]))
        elif attack_name == "session_replay":
            from neuroshield.core.attack import SessionReplayAttack
            self.attack_engine.add_modifier(SessionReplayAttack(target_channels=[0, 1]))
