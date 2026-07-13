from abc import ABC, abstractmethod
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from neuroshield.core.twin import DigitalTwin
from neuroshield.core.event_bus import EventBus, Event


class ISignalModifier(ABC):
    @abstractmethod
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        """
        Mutates the incoming signal window and registers impacts
        on the DigitalTwin state (e.g. impedance changes, disconnection).
        """
        pass


class NoiseInjectionAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], noise_level_microvolts: float = 50.0):
        self.target_channels = target_channels
        self.noise_level = noise_level_microvolts

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels:
                # Add Gaussian noise
                noise = np.random.normal(0, self.noise_level, size=data.shape[1])
                mutated_data[ch, :] += noise
        return mutated_data


class SignalDriftAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], drift_rate_uv_per_sec: float = 20.0):
        self.target_channels = target_channels
        self.drift_rate = drift_rate_uv_per_sec
        # Maintain drift offsets across calls
        self.offsets: Dict[int, float] = {ch: 0.0 for ch in target_channels}

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        dt = num_samples / sample_rate

        for ch in self.target_channels:
            if ch in eeg_channels:
                start_offset = self.offsets.get(ch, 0.0)
                # Compute linear drift vector for this block
                drift_vector = np.linspace(start_offset, start_offset + self.drift_rate * dt, num_samples)
                mutated_data[ch, :] += drift_vector
                # Store final offset for the next chunk
                self.offsets[ch] = start_offset + self.drift_rate * dt
        return mutated_data


class ImpedanceSpikeAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], spike_value_kohm: float = 150.0, powerline_noise_amplitude: float = 100.0):
        self.target_channels = target_channels
        self.spike_value = spike_value_kohm
        self.powerline_noise_amplitude = powerline_noise_amplitude
        self.time_counter = 0.0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]

        # Create a powerline interference (50 Hz sine wave)
        t = self.time_counter + np.arange(num_samples) / sample_rate
        powerline_noise = self.powerline_noise_amplitude * np.sin(2 * np.pi * 50.0 * t)
        self.time_counter += num_samples / sample_rate

        for ch in self.target_channels:
            if ch in eeg_channels:
                # Update impedance in digital twin to spike value
                twin.update_impedance(ch, self.spike_value)

                # Zero out clean signal and inject powerline noise + high random noise
                high_noise = np.random.normal(0, 30.0, size=num_samples)
                mutated_data[ch, :] = powerline_noise + high_noise

        return mutated_data


class SignalSuppressionAttack(ISignalModifier):
    def __init__(self, target_channels: List[int], attenuation_factor: float = 0.05):
        self.target_channels = target_channels
        self.attenuation_factor = attenuation_factor

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        for ch in self.target_channels:
            if ch in eeg_channels:
                # Attenuate the signal
                mutated_data[ch, :] *= self.attenuation_factor
        return mutated_data


class AdversarialOptimizerAttack(ISignalModifier):
    """
    Uses a True Online Genetic Algorithm to optimize an injection waveform
    that maximizes power in the pathological beta band (13-30 Hz) on the Digital Twin.
    It evaluates one gene per simulation block, measuring real-world twin state,
    and persisting learning across the simulation timeline.
    """
    def __init__(self, target_channels: List[int], population_size: int = 10, target_rms_limit: float = 100.0):
        self.target_channels = target_channels
        self.population_size = population_size
        self.target_rms_limit = target_rms_limit
        # Genes: [amplitude, frequency (13-30)]
        self.population = np.random.rand(population_size, 2)
        self.population[:, 0] *= 50.0  # Amplitude up to 50
        self.population[:, 1] = 13.0 + self.population[:, 1] * 17.0  # Frequency 13-30 Hz
        
        self.fitness_scores = np.zeros(population_size)
        self.current_gene_idx = 0
        self.generation = 0
        self.historical_best_fitness = 0.0
        
        self.best_genes = self.population[0]
        self.time_counter = 0.0
        self.current_phase = 0.0 # Maintain continuous phase state across blocks
        self._last_injected = False

    def _evolve(self):
        # Select best half based on actual recorded fitness
        sorted_idx = np.argsort(self.fitness_scores)[::-1]
        best_fitness = self.fitness_scores[sorted_idx[0]]
        if best_fitness > self.historical_best_fitness:
            self.historical_best_fitness = best_fitness
            
        best_half = self.population[sorted_idx[:max(1, self.population_size // 2)]]
        self.best_genes = best_half[0]
        
        # Mutate to fill rest
        new_population = np.zeros_like(self.population)
        new_population[:len(best_half)] = best_half
        for i in range(len(best_half), self.population_size):
            parent = best_half[np.random.randint(0, len(best_half))]
            mutation = np.random.normal(0, 0.1, 2)
            mutation[0] *= 10.0 # Amplitude mutation
            mutation[1] *= 2.0  # Freq mutation
            new_population[i] = np.clip(parent + mutation, [0.0, 13.0], [self.target_rms_limit * 1.414, 30.0])
        self.population = new_population
        self.fitness_scores = np.zeros(self.population_size)
        self.current_gene_idx = 0
        self.generation += 1

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        num_samples = data.shape[1]
        
        # 1. Evaluate fitness of the PREVIOUS gene based on twin's current physical state
        if self._last_injected:
            current_state = twin.get_state()
            # Fitness is directly tied to the twin's real-world beta power, ensuring
            # the GA learns how to evade the IDS/IPS in the environment.
            beta_power = current_state.get("beta_power", 0.0)
            self.fitness_scores[self.current_gene_idx] = beta_power
            
            self.current_gene_idx += 1
            if self.current_gene_idx >= self.population_size:
                self._evolve()
                
        # 2. Inject Current gene to evaluate
        amp, freq = self.population[self.current_gene_idx]
        
        mutated_data = data.copy()
        t = np.arange(num_samples) / sample_rate
        attack_signal = amp * np.sin(2 * np.pi * freq * t + self.current_phase)
        
        # Advance continuous phase for the next block to ensure C0 continuity
        self.current_phase += 2 * np.pi * freq * (num_samples / sample_rate)
        self.current_phase %= 2 * np.pi
        
        self.time_counter += num_samples / sample_rate

        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated_data[ch, :] += attack_signal

        self._last_injected = True
        return mutated_data


class TraceReplayAttack(ISignalModifier):
    """
    Replays an external attack trace (e.g. from a CSV file of captured RF interference)
    over the target channels.
    """
    def __init__(self, target_channels: List[int], trace_file_path: str):
        self.target_channels = target_channels
        # Load external trace
        import os
        try:
            if os.path.exists(trace_file_path):
                self.trace_data = np.loadtxt(trace_file_path, delimiter=',')
                if len(self.trace_data.shape) > 1:
                    self.trace_data = self.trace_data[:, 0] # Take first column
            else:
                self.trace_data = np.zeros(1000) # Fallback
        except Exception:
            self.trace_data = np.zeros(1000) # Fallback
        self.trace_index = 0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        
        # Get chunk from trace, looping if necessary
        trace_chunk = np.zeros(num_samples)
        for i in range(num_samples):
            trace_chunk[i] = self.trace_data[self.trace_index % len(self.trace_data)]
            self.trace_index += 1

        for ch in self.target_channels:
            if ch in eeg_channels:
                mutated_data[ch, :] += trace_chunk
                
        return mutated_data

class RFJammingAttack(ISignalModifier):
    """
    Simulates physical-layer RF interference (Jamming) or BLE MTU overflow.
    Instead of mutating the EEG signals, this attack configures the DigitalTwin 
    with a packet drop rate which the OpenBCICytonEmulator uses to simulate 
    missing packets over the air.
    """
    def __init__(self, drop_rate: float = 0.5):
        self.drop_rate = drop_rate

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        # We don't mutate the raw analog signal; we just set the drop rate on the twin
        # so the Emulator drops packets during serialization.
        setattr(twin, "rf_packet_drop_rate", self.drop_rate)
        return data


class FramingDesynchronizationAttack(ISignalModifier):
    """
    Exploits parsers like OpenBCI_GUI's InterfaceSerial.pde which do not escape framing bytes.
    Injects specific microvolt values that exactly translate to 0xA0 (Start) and 0xC0 (End) bytes 
    in the 24-bit Cyton data payload. This causes out-of-bounds array exceptions or framing drops 
    in the client parser.
    """
    def __init__(self, target_channels: List[int], inject_start_byte: bool = True):
        self.target_channels = target_channels
        self.inject_start_byte = inject_start_byte

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        
        # Calculate dynamic scaling based on the DigitalTwin ADC params
        # VREF and Gain dictate the scale factor.
        scale_factor = (1000000.0 * twin.adc_vref) / (twin.adc_gain * ((2 ** (twin.adc_resolution_bits - 1)) - 1))
        
        # 0xA0A0A0 in 24-bit signed = 10526880 - 16777216 = -6250336
        # 0xC0C0C0 in 24-bit signed = 12632256 - 16777216 = -4144960
        if self.inject_start_byte:
            target_counts = -6250336
        else:
            target_counts = -4144960
            
        injection_uv = target_counts * scale_factor

        for ch in self.target_channels:
            if ch in eeg_channels:
                # Overwrite entire signal with the dynamically calculated framing bytes payload
                mutated_data[ch, :] = injection_uv
        return mutated_data

class SessionReplayAttack(ISignalModifier):
    """
    Captures a clean segment of EEG data for `capture_duration_sec` and then 
    continuously loops this recorded data over the target channels, effectively 
    masking any subsequent real brain activity.
    """
    def __init__(self, target_channels: List[int], capture_duration_sec: float = 5.0):
        self.target_channels = target_channels
        self.capture_duration_sec = capture_duration_sec
        self.captured_data = None
        self.capture_time = 0.0
        self.is_capturing = True
        self.replay_index = 0

    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        dt = num_samples / sample_rate

        if self.is_capturing:
            if self.captured_data is None:
                self.captured_data = data.copy()
            else:
                self.captured_data = np.hstack((self.captured_data, data.copy()))
            
            self.capture_time += dt
            if self.capture_time >= self.capture_duration_sec:
                self.is_capturing = False
            return mutated_data
            
        else:
            # Replay phase
            replay_chunk = np.zeros_like(data)
            cap_len = self.captured_data.shape[1]
            
            for i in range(num_samples):
                replay_chunk[:, i] = self.captured_data[:, self.replay_index % cap_len]
                self.replay_index += 1

            for ch in self.target_channels:
                if ch in eeg_channels:
                    mutated_data[ch, :] = replay_chunk[ch, :]
                    
            return mutated_data

class TemporalEvasionAttack(ISignalModifier):
    """
    A time-hopping attack that injects high-frequency malicious payloads in very short 
    bursts, separated by clean intervals. Designed to evade windowed average-based IDSs.
    """
    def __init__(self, target_channels: List[int], burst_duration_sec: float = 0.1, quiet_duration_sec: float = 1.0, amplitude: float = 50.0):
        self.target_channels = target_channels
        self.burst_duration_sec = burst_duration_sec
        self.quiet_duration_sec = quiet_duration_sec
        self.amplitude = amplitude
        self.time_counter = 0.0
        
    def apply(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int, twin: DigitalTwin) -> np.ndarray:
        mutated_data = data.copy()
        num_samples = data.shape[1]
        
        cycle_duration = self.burst_duration_sec + self.quiet_duration_sec
        
        t = self.time_counter + np.arange(num_samples) / sample_rate
        self.time_counter += num_samples / sample_rate
        
        # Calculate which samples fall into the "burst" phase of the cycle
        phase_in_cycle = t % cycle_duration
        burst_mask = phase_in_cycle < self.burst_duration_sec
        
        if np.any(burst_mask):
            payload = np.random.normal(0, self.amplitude, size=num_samples)
            for ch in self.target_channels:
                if ch in eeg_channels:
                    mutated_data[ch, burst_mask] += payload[burst_mask]
                    
        return mutated_data


class SignalAttackEngine:
    def __init__(self, twin: DigitalTwin, event_bus: Optional[EventBus] = None):
        self.twin = twin
        self.event_bus = event_bus
        self.modifiers: List[ISignalModifier] = []
        import threading
        self.lock = threading.RLock()

    def add_modifier(self, modifier: ISignalModifier):
        with self.lock:
            self.modifiers.append(modifier)

        if self.event_bus:
            # Extract parameters
            params = {}
            if hasattr(modifier, "noise_level"):
                params["noise_level_uv"] = modifier.noise_level
            elif hasattr(modifier, "drift_rate"):
                params["drift_rate_uv_per_sec"] = modifier.drift_rate
            elif hasattr(modifier, "spike_value"):
                params["spike_value_kohm"] = modifier.spike_value
            elif hasattr(modifier, "attenuation_factor"):
                params["attenuation_factor"] = modifier.attenuation_factor

            self.event_bus.publish(Event(
                topic="attack.modifier_added",
                data={
                    "type": modifier.__class__.__name__,
                    "target_channels": getattr(modifier, "target_channels", []),
                    "params": params,
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="attack_engine"
            ))

    def remove_modifier(self, modifier: ISignalModifier):
        removed = False
        with self.lock:
            if modifier in self.modifiers:
                self.modifiers.remove(modifier)
                removed = True

        if removed and self.event_bus:
            self.event_bus.publish(Event(
                topic="attack.modifier_removed",
                data={
                    "type": modifier.__class__.__name__,
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="attack_engine"
            ))

    def apply_attacks(self, data: np.ndarray, eeg_channels: List[int], sample_rate: int) -> np.ndarray:
        processed_data = data.copy()
        with self.lock:
            active_mods = list(self.modifiers)

        # Reset twin-level properties that might have been left over
        setattr(self.twin, "rf_packet_drop_rate", 0.0)

        for modifier in active_mods:
            processed_data = modifier.apply(processed_data, eeg_channels, sample_rate, self.twin)

        if active_mods and self.event_bus:
            self.event_bus.publish(Event(
                topic="attack.applied",
                data={
                    "active_modifiers_count": len(active_mods),
                    "sim_clock": self.twin.get_sim_clock()
                },
                source="attack_engine"
            ))

        return processed_data


@dataclass
class AttackStep:
    """A single step inside a scripted AttackScenario."""
    time_sec: float
    attack_type: str          # "noise", "drift", "impedance", "suppression"
    duration_sec: float
    target_channels: List[int]
    params: Dict[str, Any] = field(default_factory=dict)
    # Bookkeeping
    _modifier_instance: Optional[ISignalModifier] = None
    _started: bool = False
    _stopped: bool = False


class AttackScenario:
    """A collection of AttackSteps replayed deterministically over the simulation timeline."""

    def __init__(self, name: str, steps: List[AttackStep], event_bus: Optional[EventBus] = None):
        self.name = name
        self.steps = sorted(steps, key=lambda s: s.time_sec)
        self.event_bus = event_bus

    def update(self, sim_clock: float, attack_engine: SignalAttackEngine, registry: Any) -> None:
        """
        Check timeline and active/deactivate scenario steps based on simulation clock.
        """
        for step in self.steps:
            # 1. Trigger steps that should start
            if not step._started and sim_clock >= step.time_sec:
                step._started = True
                try:
                    # Resolve class/factory from PluginRegistry
                    info = registry.get("attacks", step.attack_type)
                    step._modifier_instance = registry.create(
                        "attacks", step.attack_type,
                        target_channels=step.target_channels,
                        **step.params
                    )
                    attack_engine.add_modifier(step._modifier_instance)

                    if self.event_bus:
                        self.event_bus.publish(Event(
                            topic="attack.scenario_step.started",
                            data={
                                "scenario_name": self.name,
                                "attack_type": step.attack_type,
                                "target_channels": step.target_channels,
                                "duration_sec": step.duration_sec,
                                "sim_clock": sim_clock
                            },
                            source="scenario_player"
                        ))
                except Exception as e:
                    import sys
                    print(f"[AttackScenario] Error starting step: {e}", file=sys.stderr)

            # 2. Reclaim steps that have expired
            if step._started and not step._stopped and sim_clock >= (step.time_sec + step.duration_sec):
                step._stopped = True
                if step._modifier_instance:
                    attack_engine.remove_modifier(step._modifier_instance)

                    if self.event_bus:
                        self.event_bus.publish(Event(
                            topic="attack.scenario_step.stopped",
                            data={
                                "scenario_name": self.name,
                                "attack_type": step.attack_type,
                                "sim_clock": sim_clock
                            },
                            source="scenario_player"
                        ))
