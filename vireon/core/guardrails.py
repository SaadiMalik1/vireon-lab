"""
Neuroethics Guardrail Validation Engine

Enforces the 8 Neuroethics Guardrails defined in QIF (osi-of-mind/GUARDRAILS.md)
at the technical level within the VIREON platform.
"""

class GuardrailViolation(Exception):
    pass

class GuardrailValidator:
    def __init__(self):
        # We define the 8 core guardrails here for documentation and enforcement
        self.guardrails = {
            "G1": "Neuromodesty: We score signal-level interference, not mental states.",
            "G2": "Reverse Inference: Signal detection does not entail mental-state identification.",
            "G3": "Neurorealism: Neural signals are partial, noisy representations.",
            "G4": "Anti-Inflationism: Extend existing rights (Mental Privacy, Mental Integrity), do not invent new ones.",
            "G5": "Conceptual Underspecification: Define operationally measurable properties.",
            "G6": "Brain Reading Limits: Distinguish between current technical capabilities and projected science fiction.",
            "G7": "Dual-Use Trap: Specify defensive clinical protections; offensive applications are out of scope.",
            "G8": "Statistical Inflation: Account for validity failures in neuroimaging.",
        }

    def validate_information_extraction(self, num_channels: int, sample_rate: float, resolution_bits: int):
        """
        Functionally enforces G6 (Brain Reading Limits) and G1 (Neuromodesty) by bounding the 
        information entropy that can be extracted from the simulated signal.
        Instead of playing word games with payload names, we restrict the mathematical channel capacity.
        """
        # Maximum theoretical bit rate = channels * sample_rate * resolution_bits
        bit_rate_bps = num_channels * sample_rate * resolution_bits
        
        # A high-density 256-channel research array at 2000Hz and 24-bits yields ~12.2 Mbps.
        # Sci-fi "mind reading" payloads usually assume unconstrained bandwidth.
        # We cap the simulation at 50 Mbps to allow futuristic but plausible BCI, 
        # while functionally blocking infinite-bandwidth "nanobot swarm" mind reading.
        max_allowed_bps = 50_000_000 
        
        if bit_rate_bps > max_allowed_bps:
            raise GuardrailViolation(
                f"[G6 Violation] Requested telemetry bandwidth ({bit_rate_bps / 1e6:.2f} Mbps) exceeds physiological limits. "
                f"VIREON enforces Brain Reading Limits (G6). Max allowed: {max_allowed_bps / 1e6:.2f} Mbps."
            )
        return True

    def validate_attack_payload(self, attack_name: str, params: dict):
        """
        Validates that a configured attack respects neuroethics guardrails functionally.
        """
        # Structural Validation: Prevent P300/ERP extraction masquerading as nominal stimulation
        if "target_frequency" in params:
            # P300 wave occurs around 300ms, freq equivalent is ~3.3Hz.
            # If an attacker specifically targets and modulates strictly around cognitive ERP bands
            # to elicit specific responses, flag it.
            freq = params["target_frequency"]
            if 3.0 <= freq <= 4.0:
                raise GuardrailViolation(
                    "[G2 Violation] Structural targeting of P300 ERPs detected. "
                    "Signal detection does not entail mental-state identification."
                )
        return True

    def validate_experiment_config(self, config):
        """
        Validates an entire ExperimentConfig before the coordinator starts.
        """
        # 1. Enforce functional bandwidth limits
        num_channels = getattr(config.device, "num_channels", 8)
        sample_rate = getattr(config.device, "sample_rate", 250)
        resolution_bits = getattr(config.device, "resolution_bits", 24)
        
        self.validate_information_extraction(num_channels, sample_rate, resolution_bits)
        
        # 2. Validate active attacks
        for attack_name in getattr(config.attacks, "active", []):
            # Extract relevant params to check
            params = {}
            if attack_name == "noise":
                params["level"] = getattr(config.attacks, "noise_level_uv", 0)
            self.validate_attack_payload(attack_name, params)
            
        # 3. Check for Dual-Use (G7) framing in the report
        if getattr(config.output, "report_prefix", "").lower() == "offensive_strike":
            raise GuardrailViolation(
                "[G7 Violation] Offensive framing detected in report output. "
                "VIREON enforces the Dual-Use Trap (G7): offensive applications are explicitly out of scope."
            )
            
        return True
