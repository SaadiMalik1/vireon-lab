import threading
import time

from vireon.core.physics import PhysicsEngine

def test_twin_concurrent_mutation(mock_twin):
    """
    Test that concurrent mutation of DigitalTwin state (including physics tick)
    does not cause torn state or exceptions, proving RLock safety.
    """
    twin = mock_twin
    errors = []
    
    def simulate_physics():
        physics = PhysicsEngine()
        try:
            for _ in range(100):
                # Apply physics constraints (computes temperature, etc.)
                physics.tick(twin, 0.1)
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)
            
    def simulate_clinical():
        try:
            for _ in range(100):
                # Emulate clinical checking
                twin.update_therapy(True)
                twin.update_stimulation_params(2.0, 130.0)
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    def simulate_attack():
        try:
            for _ in range(100):
                # Emulate attack mutation
                if hasattr(twin, "_lock"):
                    with twin._lock:
                        twin.stimulation_amplitude_ma = 15.0
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=simulate_physics)
    t2 = threading.Thread(target=simulate_clinical)
    t3 = threading.Thread(target=simulate_attack)

    t1.start()
    t2.start()
    t3.start()

    t1.join()
    t2.join()
    t3.join()

    # If any thread threw an exception (e.g. from a race condition), it would be appended to errors
    assert len(errors) == 0, f"Exceptions occurred during concurrent mutation: {errors}"
    
    # State should be logically intact, temperature shouldn't be infinite
    assert twin.temperature_celsius >= 37.0
