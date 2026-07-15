"""
Tests for the VIREON core infrastructure: EventBus, Config, PluginRegistry,
and experiment reproducibility.
"""
import unittest
import os

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vireon.core.event_bus import EventBus, Event
from vireon.core.config import ExperimentConfig, load_config, config_from_cli_args
from vireon.core.plugin_registry import PluginRegistry, PluginInfo, register_builtin_plugins
from vireon.core.twin import DigitalTwin
from vireon.core.engine import ReplayEngine
from vireon.core.attack import SignalAttackEngine


class TestEventBus(unittest.TestCase):
    """Tests for the publish-subscribe event bus."""

    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        received = []
        self.bus.subscribe("test.topic", lambda e: received.append(e.data))
        self.bus.publish(Event(topic="test.topic", data={"value": 42}))
        self.bus.flush()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["value"], 42)

    def test_unsubscribe(self):
        received = []
        sub_id = self.bus.subscribe("test.topic", lambda e: received.append(e))
        self.bus.publish(Event(topic="test.topic"))
        self.assertEqual(len(received), 1)

        self.assertTrue(self.bus.unsubscribe(sub_id))
        self.bus.publish(Event(topic="test.topic"))
        self.bus.flush()
        self.assertEqual(len(received), 1)  # No new events

    def test_unsubscribe_nonexistent(self):
        self.assertFalse(self.bus.unsubscribe("nonexistent-id"))

    def test_wildcard_subscription(self):
        received = []
        self.bus.subscribe("*", lambda e: received.append(e.topic))
        self.bus.publish(Event(topic="a.event"))
        self.bus.publish(Event(topic="b.event"))
        self.bus.flush()
        self.assertEqual(sorted(received), ["a.event", "b.event"])

    def test_priority_ordering(self):
        order = []
        self.bus.subscribe("test", lambda e: order.append("B"), priority=200)
        self.bus.subscribe("test", lambda e: order.append("A"), priority=50)
        self.bus.subscribe("test", lambda e: order.append("C"), priority=300)
        self.bus.publish(Event(topic="test"))
        self.bus.flush()
        self.assertEqual(sorted(order), ["A", "B", "C"])

    def test_handler_error_does_not_crash_bus(self):
        received = []

        def bad_handler(e):
            raise RuntimeError("intentional crash")

        self.bus.subscribe("test", bad_handler, priority=10)
        self.bus.subscribe("test", lambda e: received.append("ok"), priority=20)

        # Should not raise — bad handler is caught
        self.bus.publish(Event(topic="test"))
        self.bus.flush()
        self.assertEqual(received, ["ok"])

    def test_event_logging(self):
        self.bus.enable_logging(True, max_size=5)
        for i in range(10):
            self.bus.publish(Event(topic="test", data={"i": i}))
        
        self.bus.flush()

        log = self.bus.get_event_log()
        self.assertEqual(len(log), 5)  # Capped at max_size
        self.assertEqual(log[0].data["i"], 5)  # Oldest retained

    def test_subscriber_count(self):
        self.bus.subscribe("a", lambda e: None)
        self.bus.subscribe("a", lambda e: None)
        self.bus.subscribe("b", lambda e: None)
        self.assertEqual(self.bus.get_subscriber_count("a"), 2)
        self.assertEqual(self.bus.get_subscriber_count("b"), 1)
        self.assertEqual(self.bus.get_subscriber_count(), 3)

    def test_clear(self):
        self.bus.subscribe("test", lambda e: None)
        self.bus.enable_logging(True)
        self.bus.publish(Event(topic="test"))
        self.bus.clear()
        self.assertEqual(self.bus.get_subscriber_count(), 0)
        self.assertEqual(len(self.bus.get_event_log()), 0)

    def test_no_subscribers_does_not_crash(self):
        # Publishing to a topic with no subscribers should be a no-op
        self.bus.publish(Event(topic="empty.topic", data={"x": 1}))


class TestConfig(unittest.TestCase):
    """Tests for the experiment configuration system."""

    def test_default_config(self):
        config = ExperimentConfig()
        self.assertEqual(config.name, "default")
        self.assertIsNone(config.seed)
        self.assertEqual(config.duration_sec, 10.0)
        self.assertEqual(config.device.type, "synthetic")
        self.assertEqual(config.device.sample_rate, 250)



    def test_load_config_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path.toml")

    def test_config_from_cli_args(self):
        class MockArgs:
            duration = 20.0
            interval = 0.2
            board = "pieeg"
            dataset = "test.edf"
            attack = "noise,drift"
            noise_val = 80.0
            drift_val = 30.0
            spike_val = 200.0
            attenuation_val = 0.1
            secure_mode = True
            report_prefix = "test_run"
            no_report = False
            web_ui = False
            emulate_openbci = False
            emulate_ble = False
            ble_attack = ""
            dbs_mode = True
            dbs_attack = "phase_shift"
            hardware_loopback = False

        config = config_from_cli_args(MockArgs())
        self.assertEqual(config.duration_sec, 20.0)
        self.assertEqual(config.device.type, "pieeg")
        self.assertEqual(config.attacks.active, ["noise", "drift"])
        self.assertTrue(config.security.enabled)
        self.assertTrue(config.emulation.dbs_mode)


class TestPluginRegistry(unittest.TestCase):
    """Tests for the plugin registry."""

    def setUp(self):
        self.registry = PluginRegistry()

    def test_register_and_get(self):
        info = PluginInfo(name="test_plugin", category="test", description="A test")
        self.registry.register(info)
        result = self.registry.get("test", "test_plugin")
        self.assertEqual(result.name, "test_plugin")

    def test_duplicate_registration_raises(self):
        info = PluginInfo(name="test", category="cat")
        self.registry.register(info)
        with self.assertRaises(ValueError):
            self.registry.register(info)

    def test_get_nonexistent_raises(self):
        with self.assertRaises(KeyError):
            self.registry.get("nonexistent", "nothing")

    def test_create_with_class(self):
        class MyPlugin:
            def __init__(self, value=10):
                self.value = value

        self.registry.register(PluginInfo(
            name="my_plugin", category="test", plugin_class=MyPlugin
        ))
        instance = self.registry.create("test", "my_plugin", value=42)
        self.assertEqual(instance.value, 42)

    def test_create_with_factory(self):
        self.registry.register(PluginInfo(
            name="factory_plugin", category="test",
            factory=lambda x=1: {"result": x * 2}
        ))
        result = self.registry.create("test", "factory_plugin", x=5)
        self.assertEqual(result["result"], 10)

    def test_list_categories(self):
        self.registry.register(PluginInfo(name="a", category="cat1"))
        self.registry.register(PluginInfo(name="b", category="cat2"))
        cats = self.registry.list_categories()
        self.assertIn("cat1", cats)
        self.assertIn("cat2", cats)

    def test_has(self):
        self.registry.register(PluginInfo(name="exists", category="test"))
        self.assertTrue(self.registry.has("test", "exists"))
        self.assertFalse(self.registry.has("test", "nope"))

    def test_unregister(self):
        self.registry.register(PluginInfo(name="temp", category="test"))
        self.assertTrue(self.registry.unregister("test", "temp"))
        self.assertFalse(self.registry.has("test", "temp"))

    def test_register_builtin_plugins(self):
        """Ensure all built-in plugins register without errors."""
        registry = PluginRegistry()
        register_builtin_plugins(registry)

        # Should have entries in multiple categories
        self.assertTrue(len(registry.list_categories()) >= 3)
        self.assertTrue(registry.has("datasets", "edf_reader"))
        self.assertTrue(registry.has("devices", "synthetic"))
        self.assertTrue(registry.has("attacks", "noise"))
        self.assertTrue(registry.has("clinical", "closed_loop"))


class TestDigitalTwinSnapshot(unittest.TestCase):
    """Tests for Digital Twin snapshot/restore."""

    def test_snapshot_and_restore(self):
        twin = DigitalTwin()
        twin.update_battery(75.0)
        twin.update_decoder_confidence(0.85)
        twin.update_temperature(38.5)
        twin.update_ble_pairing_state("PAIRED")

        snap = twin.snapshot()

        # Create a fresh twin and restore
        twin2 = DigitalTwin()
        twin2.restore(snap)

        self.assertAlmostEqual(twin2.battery_level, 75.0, places=1)
        self.assertAlmostEqual(twin2.decoder_confidence, 0.85, places=2)
        self.assertAlmostEqual(twin2.temperature_celsius, 38.5, places=1)
        self.assertEqual(twin2.ble_pairing_state, "PAIRED")

    def test_simulation_clock(self):
        twin = DigitalTwin()
        self.assertEqual(twin.get_sim_clock(), 0.0)
        twin.set_sim_clock(5.5)
        self.assertEqual(twin.get_sim_clock(), 5.5)

    def test_extended_state_in_get_state(self):
        twin = DigitalTwin()
        state = twin.get_state()
        self.assertIn("temperature_celsius", state)
        self.assertIn("flash_utilization_pct", state)
        self.assertIn("memory_usage_pct", state)
        self.assertIn("ble_pairing_state", state)
        self.assertIn("amplifier_gain", state)
        self.assertIn("sim_clock", state)


class TestReplayEngineFeatures(unittest.TestCase):
    """Tests for ReplayEngine pause/resume, speed, and seeding."""

    def test_pause_resume(self):
        twin = DigitalTwin()
        engine = ReplayEngine(twin, SignalAttackEngine(twin))

        self.assertFalse(engine.is_paused)
        engine.pause()
        self.assertTrue(engine.is_paused)
        engine.resume()
        self.assertFalse(engine.is_paused)

    def test_speed_multiplier(self):
        twin = DigitalTwin()
        engine = ReplayEngine(twin, SignalAttackEngine(twin))

        engine.set_speed(2.0)
        self.assertEqual(engine.speed, 2.0)
        engine.set_speed(0.5)
        self.assertEqual(engine.speed, 0.5)

        # Clamped to reasonable bounds
        engine.set_speed(0.01)
        self.assertEqual(engine.speed, 0.1)
        engine.set_speed(999.0)
        self.assertEqual(engine.speed, 100.0)

    def test_deterministic_rng(self):
        twin = DigitalTwin()
        engine = ReplayEngine(twin, SignalAttackEngine(twin), seed=42)

        # Same seed should produce same sequence
        val1 = engine.rng.random()
        engine2 = ReplayEngine(twin, SignalAttackEngine(twin), seed=42)
        val2 = engine2.rng.random()
        self.assertEqual(val1, val2)

    def test_simulation_clock_advances(self):
        twin = DigitalTwin()
        engine = ReplayEngine(twin, SignalAttackEngine(twin))

        # Start engine briefly
        engine.start(interval_sec=0.05)
        import time
        time.sleep(0.2)
        engine.stop()

        # Clock should have advanced
        self.assertGreater(engine.sim_clock, 0.0)
        self.assertGreater(twin.get_sim_clock(), 0.0)


class TestReproducibility(unittest.TestCase):
    """
    Critical test: running the same experiment twice with the same seed
    must produce identical Digital Twin history.
    """

    def _run_short_experiment(self, seed):
        """Run a minimal seeded experiment and return the twin state history."""
        twin = DigitalTwin(device_id="repro_test")
        attack_engine = SignalAttackEngine(twin)
        engine = ReplayEngine(twin, attack_engine, seed=seed)

        from vireon.plugins.clinical.closed_loop import ClosedLoopSimulator
        clinical = ClosedLoopSimulator(twin)

        engine.add_callback(
            lambda data, ch, sr: clinical.process_signal(data, ch, sr)
        )

        engine.start(interval_sec=0.05)
        import time
        time.sleep(0.3)
        engine.stop()

        return twin.get_state()

    def test_same_seed_produces_same_state(self):
        state1 = self._run_short_experiment(seed=99999)
        state2 = self._run_short_experiment(seed=99999)

        # Core fields should be identical
        self.assertEqual(state1["clinical_status"], state2["clinical_status"])
        self.assertEqual(state1["hazard_state"], state2["hazard_state"])
        self.assertAlmostEqual(
            state1["decoder_confidence"],
            state2["decoder_confidence"],
            places=1
        )


if __name__ == "__main__":
    unittest.main()
