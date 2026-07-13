import sys
from vireon.core.zta import ZTAPolicyEngine, TrustContext, AuthorizationDecision

def test_zta_allow():
    engine = ZTAPolicyEngine(thresholds={"ota_update": 0.9, "telemetry_read": 0.5})
    
    # High trust context
    context = TrustContext(
        biometric_confidence=1.0,  # +0.4
        firmware_healthy=True,     # +0.3
        e2ee_established=True,     # +0.2
        clinical_mode=True         # +0.1
    )
    # Total score = 1.0
    
    decision = engine.evaluate_request("ota_update", context)
    assert decision == AuthorizationDecision.ALLOW, f"Expected ALLOW, got {decision}"
    print("test_zta_allow passed")

def test_zta_deny_due_to_score():
    engine = ZTAPolicyEngine(thresholds={"ota_update": 0.9, "telemetry_read": 0.5})
    
    # Low trust context (no biometrics, no e2ee, not clinical)
    context = TrustContext(
        biometric_confidence=0.0,
        firmware_healthy=True,     # +0.3
        e2ee_established=False,
        clinical_mode=False
    )
    # Total score = 0.3
    
    decision = engine.evaluate_request("ota_update", context)
    assert decision == AuthorizationDecision.DENY, f"Expected DENY, got {decision}"
    
    # 0.3 should not be enough for telemetry (requires 0.5)
    decision2 = engine.evaluate_request("telemetry_read", context)
    assert decision2 == AuthorizationDecision.DENY, f"Expected DENY for telemetry, got {decision2}"
    print("test_zta_deny_due_to_score passed")

def test_zta_deny_due_to_crashed_firmware():
    engine = ZTAPolicyEngine(thresholds={"ota_update": 0.1, "telemetry_read": 0.1})
    
    # Firmware crashed -> hard stop
    context = TrustContext(
        biometric_confidence=1.0,
        firmware_healthy=False,
        e2ee_established=True,
        clinical_mode=True
    )
    
    decision = engine.evaluate_request("ota_update", context)
    assert decision == AuthorizationDecision.DENY, f"Expected DENY (hard stop), got {decision}"
    print("test_zta_deny_due_to_crashed_firmware passed")

if __name__ == '__main__':
    try:
        test_zta_allow()
        test_zta_deny_due_to_score()
        test_zta_deny_due_to_crashed_firmware()
        print("ALL ZTA TESTS PASSED")
    except AssertionError as e:
        print("TEST FAILED:", e)
        sys.exit(1)
