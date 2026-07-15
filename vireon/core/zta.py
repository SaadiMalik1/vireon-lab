from enum import Enum
from dataclasses import dataclass
from typing import Dict

class AuthorizationDecision(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"

@dataclass
class TrustContext:
    biometric_confidence: float  # 0.0 to 1.0 (1.0 = highly certain identity)
    firmware_healthy: bool       # True if implant has not crashed/faulted
    e2ee_established: bool       # True if session has E2EE active
    clinical_mode: bool          # True if in a verified clinical environment

class ZTAPolicyEngine:
    """
    Zero-Trust Architecture (ZTA) Policy Engine.
    Continuously evaluates the contextual trust score of the environment
    against predefined thresholds before authorizing sensitive commands.
    """
    def __init__(self, thresholds: Dict[str, float]):
        """
        :param thresholds: Mapping of action names to minimum required trust scores (0.0 to 1.0)
        """
        self.thresholds = thresholds
        
    def calculate_trust_score(self, context: TrustContext) -> float:
        """Calculate an aggregate trust score based on the current context."""
        score = 0.0
        
        # Base identity (up to 0.4)
        score += context.biometric_confidence * 0.4
        
        # System health (up to 0.3)
        if context.firmware_healthy:
            score += 0.3
            
        # Secure channel (up to 0.2)
        if context.e2ee_established:
            score += 0.2
            
        # Physical presence / clinical setting (up to 0.1)
        if context.clinical_mode:
            score += 0.1
            
        # Mandatory E2EE Gating
        if not context.e2ee_established:
            # Clamp the maximum possible score below critical thresholds (e.g., 0.5)
            score = min(score, 0.5)
            
        return score
        
    def evaluate_request(self, action: str, context: TrustContext) -> AuthorizationDecision:
        """
        Evaluate if the given action is permitted in the current context.
        """
        if not context.firmware_healthy and action != "emergency_halt":
            # Hard stop: if firmware is compromised, deny almost everything
            return AuthorizationDecision.DENY
            
        required_score = self.thresholds.get(action, 1.0) # Default to max restriction if unknown
        actual_score = self.calculate_trust_score(context)
        
        if actual_score >= required_score:
            return AuthorizationDecision.ALLOW
        else:
            import logging
            logging.warning(f"[ZTA Engine] DENY action '{action}' | Actual Score: {actual_score:.2f} | Required: {required_score:.2f}")
            return AuthorizationDecision.DENY
