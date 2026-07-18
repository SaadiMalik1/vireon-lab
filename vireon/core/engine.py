from vireon.core.interfaces import ITwin
from vireon.core.attack import SignalAttackEngine
import time
import threading
import numpy as np
from typing import Optional, List, Callable, Any
import concurrent.futures
import logging

"""
WARNING: This module is for simulation purposes only.
The NeuroDSL bytecode VM execution has no sandboxing. Arbitrary jumps (e.g., JUMP_IF) 
could theoretically manipulate host memory if misconfigured. Do not execute untrusted 
NeuroDSL code outside of this simulation lab.
"""

logger = logging.getLogger(__name__)



class ReplayEngine:
    """
    Core simulation loop that drives data through the VIREON pipeline.
    """

    def __init__(self,
                 state_store,
                 attack_engine,
                 provider=None,
                 seed: Optional[int] = None,
                 loop_dataset: bool = True):
        self.state_store = state_store
        self.attack_engine = attack_engine
        self.provider = provider

        self.last_anomaly_score = 0.0
        self.active_attack = "none"

        try:
            import vireon_neuro_dsl
            self.scribe = vireon_neuro_dsl.PyScribe()
            print("[ReplayEngine] NeuroDSL Scribe VM successfully loaded.")
        except ImportError:
            self.scribe = None
            print("[ReplayEngine] NeuroDSL Scribe VM not available.")

        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.callbacks: List[Callable[[np.ndarray, List[int], int], None]] = []

        self.dataset_sample_position = 0

        self._seed = seed
        self._rng: Optional[np.random.Generator] = None
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()

        self._speed_multiplier = 1.0
        self._loop_dataset = loop_dataset
        self._sim_clock = 0.0

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
        # Determine sample rate and channels from state store
        sr = self.state_store.get("sample_rate", 250)
        num_channels = self.state_store.get("num_channels", 8)

        # EEG channels indices (normally 0 to num_channels-1, or specified by device)
        if self.provider is not None:
            eeg_channels = self.provider.get_eeg_channels()
        else:
            eeg_channels = list(range(num_channels))

        accumulated_samples = 0.0
        pending_futures: set[Any] = set()
        MAX_PENDING_TASKS = 20

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

            # Advance simulation clock
            drift = self.rng.uniform(-1.0, 1.0) * (interval_sec * 0.0001)
            actual_dt = interval_sec + drift
            self._sim_clock += actual_dt
            
            # Update state store sim clock
            self.state_store.set("sim_clock", self._sim_clock, source="engine")

            # Publish tick event for providers to hook into (replaces hardcoded physics/dynamics)
            from vireon.core.event_bus import Event
            
            accumulated_samples += sr * actual_dt
            num_samples_per_chunk = int(accumulated_samples)

            if num_samples_per_chunk > 0:
                accumulated_samples -= num_samples_per_chunk
                # Fetch data chunk
                raw_data: Optional[np.ndarray] = self._fetch_data(num_samples_per_chunk, num_channels)
    
                # Ensure raw_data shape is correct (channels, samples)
                if raw_data is not None and len(raw_data.shape) == 2:
                    self._dispatch_update(raw_data, eeg_channels, sr, pending_futures, MAX_PENDING_TASKS)
                else:
                    print("[ReplayEngine] Received invalid shape or empty data.")

        # Cleanup loop resources
        if self.provider is not None:
            # If the provider wraps a device, try to stop it
            if hasattr(self.provider, 'device'):
                try:
                    if hasattr(self.provider.device, "stop_stream"):
                        self.provider.device.stop_stream()
                except Exception as e:
                    logger.warning(f"Error stopping stream: {e}")
            if hasattr(self.provider, 'board') and self.provider.board:
                try:
                    self.provider.board.stop_stream()
                    self.provider.board.release_session()
                except Exception as e:
                    logger.warning(f"Error releasing session: {e}")

    def get_buffer(self) -> Optional[np.ndarray]:
        with self._buffer_lock:
            return getattr(self, "_current_buffer", None)

    def _fetch_data(self, num_samples_per_chunk: int, num_channels: int) -> Optional[np.ndarray]:
        self._current_buffer: Optional[np.ndarray] = None
        if self.provider is not None:
            try:
                raw_data = self.provider.read_chunk(self.dataset_sample_position, num_samples_per_chunk)
                self.dataset_sample_position += num_samples_per_chunk
                if raw_data is None or (raw_data.shape[1] < num_samples_per_chunk and self._loop_dataset):
                    if hasattr(self.provider, 'reader') and self._loop_dataset:
                        self.dataset_sample_position = 0
                        raw_data = self.provider.read_chunk(0, num_samples_per_chunk)
                        self.dataset_sample_position = num_samples_per_chunk
                return raw_data
            except (OSError, ValueError, EOFError, IndexError) as e:
                logger.warning(f"Dataset read boundary reached or error: {e}")
                if self._loop_dataset:
                    self.dataset_sample_position = 0
                    try:
                        raw_data = self.provider.read_chunk(0, num_samples_per_chunk)
                        self.dataset_sample_position = num_samples_per_chunk
                        return raw_data
                    except (OSError, ValueError, EOFError, IndexError) as loop_e:
                        logger.error(f"Failed to restart dataset loop: {loop_e}")
                        self.twin.hazard_state = "FAULT"
                        return np.full((num_channels, num_samples_per_chunk), np.nan)
                else:
                    logger.info("[ReplayEngine] Dataset exhausted, stopping.")
                    self.running = False
                    return None
        return np.full((num_channels, num_samples_per_chunk), np.nan)

    def _dispatch_update(self, raw_data: np.ndarray, eeg_channels: List[int], sr: int, pending_futures: Optional[set] = None, max_pending: int = 20):
        mutated_data = self.attack_engine.apply_attacks(raw_data, eeg_channels, sr, self.rng)
        with self._buffer_lock:
            self._current_buffer = mutated_data

        if self.twin.connected:
            if self.scribe:
                try:
                    _ = self.scribe.execute_step(mutated_data.flatten().tolist())
                except RuntimeError:
                    logger.error("Scribe VM execution error", exc_info=True)
            for cb in self.callbacks:
                if self._executor:
                    if pending_futures is not None:
                        done = {f for f in pending_futures if f.done()}
                        pending_futures.difference_update(done)
                        if len(pending_futures) > max_pending:
                            logger.warning(f"Load shedding callback! Queue full ({len(pending_futures)} pending).")
                            continue
                    future = self._executor.submit(cb, mutated_data, eeg_channels, sr)
                    if pending_futures is not None:
                        pending_futures.add(future)

    def inject_attack(self, attack_name: str):
        """Used by the dashboard to inject attacks."""
        self.active_attack = attack_name
        
        # Remove previously injected attacks safely
        if not hasattr(self, '_injected_modifiers'):
            self._injected_modifiers: list[Any] = []
        
        with self.attack_engine.lock:
            for mod in self._injected_modifiers:
                if mod in self.attack_engine.modifiers:
                    self.attack_engine.remove_modifier(mod)
            self._injected_modifiers.clear()
            
        if attack_name == "none":
            return
            
        new_mod: Any = None
        if attack_name == "noise":
            from vireon.core.attack import NoiseInjectionAttack
            new_mod = NoiseInjectionAttack(target_channels=[0, 1])
        elif attack_name == "drift":
            from vireon.core.attack import SignalDriftAttack
            new_mod = SignalDriftAttack(target_channels=[0, 1])
        elif attack_name == "temporal_evasion":
            from vireon.core.attack import TemporalEvasionAttack
            new_mod = TemporalEvasionAttack(target_channels=[0, 1])
        elif attack_name == "session_replay":
            from vireon.core.attack import SessionReplayAttack
            new_mod = SessionReplayAttack(target_channels=[0, 1])
            
        if new_mod:
            self.attack_engine.add_modifier(new_mod)
            self._injected_modifiers.append(new_mod)
