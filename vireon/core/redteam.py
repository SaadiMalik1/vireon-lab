from vireon.core.attack import SignalAttackEngine, TemporalEvasionAttack, NoiseInjectionAttack, SignalDriftAttack

class FeedbackMutatorEngine:
    """
    Automated Red Team Engine.
    Monitors the IDS anomaly score in real-time. If the score approaches the detection threshold,
    it actively mutates the current attack payload (e.g. lowering amplitude, or switching to
    a stealthier temporal evasion attack) to drop back under the radar.
    """
    def __init__(self, attack_engine: SignalAttackEngine):
        self.attack_engine = attack_engine
        self.throttle_cooldown = 0
        
    def tick(self, anomaly_score: float, threshold: float):
        """Called every simulation tick with the latest IDS score."""
        if self.throttle_cooldown > 0:
            self.throttle_cooldown -= 1
            return
            
        # If the anomaly score exceeds 80% of the threshold, the Red Team gets nervous
        if anomaly_score > (threshold * 0.8):
            self._evade()
            self.throttle_cooldown = 10 # Wait 10 ticks before mutating again
            
    def _evade(self):
        with self.attack_engine.lock:
            active_modifiers = list(self.attack_engine.modifiers)
            for mod in active_modifiers:
                # Tactic 1: Throttle Amplitude
                if isinstance(mod, NoiseInjectionAttack):
                    if mod.noise_level > 5.0:
                        mod.noise_level *= 0.5
                    else:
                        # Switch to Temporal Evasion if noise is already very low
                        self.attack_engine.remove_modifier(mod)
                        self.attack_engine.add_modifier(TemporalEvasionAttack(
                            target_channels=mod.target_channels,
                            burst_duration_sec=0.05,
                            quiet_duration_sec=1.5,
                            amplitude=20.0
                        ))
                
                elif isinstance(mod, SignalDriftAttack):
                    if mod.drift_rate > 2.0:
                        mod.drift_rate *= 0.5
                        
                elif isinstance(mod, TemporalEvasionAttack):
                    # Increase the quiet period to hide better
                    mod.quiet_duration_sec *= 1.5
                    mod.amplitude *= 0.8
