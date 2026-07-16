import json
import logging
import random
import numpy as np
from vireon.core.event_bus import Event
from vireon.core.zta import TrustContext, AuthorizationDecision

logger = logging.getLogger(__name__)

class CoordinatorCallbacks:
    def __init__(self, coordinator):
        self.c = coordinator

    def ws_broadcast_callback(self, data, channels, sample_rate):
        """Callback to serialize and broadcast simulation state over WebSockets."""
        if self.c.ws_server is not None:
            state = self.c.twin.get_state()
            # Send Channel 1 signal chunk as JSON-serializable list (Ch 0 is often package count)
            # Replace NaNs with 0.0 because standard JSON (and JS JSON.parse) cannot handle NaN
            signal_chunk = data[1, :]
            
            # Apply Differential Privacy if enabled
            if self.c.privacy_filter is not None:
                # We need to reshape slightly or just pass the 1D array
                signal_chunk = self.c.privacy_filter.filter_signal(signal_chunk.copy())
                if self.c.privacy_tracker:
                    self.c.privacy_tracker.consume(0.001)  # Nominal budget consumption per chunk
                    
            signal_list = signal_chunk.tolist()
            state["signal_chunk"] = [0.0 if np.isnan(x) else x for x in signal_list]
            
            active_attack = self.c.twin.active_attack
            state["active_attack"] = active_attack
            if self.c.threat_intel and active_attack != "none":
                tara_intel = self.c.threat_intel.resolve_attack(active_attack)
                if tara_intel:
                    state["threat_intel"] = tara_intel
            
            if hasattr(self.c, 'ids') and self.c.ids:
                state["security_logs"] = list(self.c.ids.detections)
                
            if hasattr(self.c, 'ips') and self.c.ips:
                state["blocked_attacks_count"] = self.c.ips.blocked_attacks_count
                state["clamping_active"] = self.c.ips.clamping_active
                state["blocked_mtu_abuses"] = getattr(self.c.ips, 'blocked_mtu_abuses', 0)
                
            if self.c.twin.nsp_mode and self.c.nsp_wrapper:
                state = self.c.nsp_wrapper.encrypt_payload(state)
                
            self.c.ws_server.broadcast_sync(json.dumps(state))

    def build_trust_context(self):
        # Determine biometric confidence
        bio_conf = 1.0
        if self.c.biometric_gate and self.c.biometric_gate.is_locked:
            bio_conf = 0.0
        elif self.c.ids and self.c.ids.history_confidence:
            bio_conf = self.c.ids.history_confidence[-1]

        return TrustContext(
            biometric_confidence=bio_conf,
            firmware_healthy=not getattr(self.c.emulator, 'crashed', False) if self.c.emulator else True,
            e2ee_established=self.c.twin.e2ee_mode,
            clinical_mode=getattr(self.c.config.security, 'clinical_mode', False)
        )

    def simulation_callback(self, raw_data, eeg_channels, sample_rate):
        """Unified callback executed every block by the ReplayEngine."""
        # 0. ZTA Telemetry Check
        if self.c.zta_engine:
            ctx = self.build_trust_context()
            decision = self.c.zta_engine.evaluate_request("telemetry_read", ctx)
            if decision == AuthorizationDecision.DENY:
                return

        num_samples = raw_data.shape[1]

        # 0. Update timed attack scenario if loaded
        if self.c.scenario and self.c.engine:
            self.c.scenario.update(self.c.engine.sim_clock, self.c.attack_engine, self.c.registry)

        # Resolve active flags dynamically (supports web UI live toggling)
        dbs_active = self.c.twin.dbs_mode
        secure_active = self.c.twin.secure_mode

        # 1. Acquire signal source
        if dbs_active and self.c.dbs_controller:
            data_to_process = self.c.dbs_controller.lfp_generator.read_chunk(
                num_samples, self.c.dbs_controller.stimulation_mode
            )
            raw_data[:data_to_process.shape[0], :] = data_to_process[:, :]
        else:
            data_to_process = raw_data.copy()

        # Simulate physical ADC input amplifier saturation limits
        data_to_process = self.c.twin.simulate_adc_saturation(data_to_process)

        # IDS/IPS signal filtering
        if secure_active and self.c.ids and self.c.ips:
            anomalies = self.c.ids.analyze_signal(data_to_process)
            data_to_process = self.c.ips.mitigate_signal_anomalies(data_to_process, anomalies)

            if anomalies:
                self.c.event_bus.publish(Event(
                    topic="ids.anomaly_detected",
                    data={"anomalies": anomalies, "sim_clock": self.c.engine.sim_clock},
                    source="ids"
                ))

        # 2. BLE transmission layer
        if self.c.config.emulation.ble and self.c.ble_link and self.c.ble_client:
            if not self.c.ble_link.connected:
                self.c.twin.set_connection(False)
                return

            payload = data_to_process.tobytes()

            from vireon.plugins.ble.attacks import GATTCorruptionAttack, MalformedNotificationAttack
            if self.c.config.emulation.ble_attack == "gatt_corrupt":
                payload = GATTCorruptionAttack(corruption_probability=1.0).apply(payload)
            elif self.c.config.emulation.ble_attack == "malformed_notify":
                attack = MalformedNotificationAttack(packet_size=len(payload))
                payload = attack.apply()

            self.c.ble_client.receive_notification(payload)

            try:
                reconstructed_bytes = b"".join(self.c.ble_client.received_packets)
                self.c.ble_client.received_packets.clear()

                if self.c.ble_link.mtu < 23:
                    if random.random() < 0.8:
                        raise ValueError("Packet loss under restricted MTU")

                data_to_process = np.frombuffer(
                    reconstructed_bytes[:raw_data.nbytes], dtype=raw_data.dtype
                ).copy().reshape(raw_data.shape)
            except Exception as e:
                logger.error(f"BLE packet reconstruction failed: {e}", exc_info=True)
                self.c.twin.hazard_state = "FAULT"
                data_to_process = np.full(raw_data.shape, np.nan)

            if secure_active and self.c.ids and self.c.ips:
                anomalies = self.c.ids.analyze_signal(data_to_process)
                data_to_process = self.c.ips.mitigate_signal_anomalies(data_to_process, anomalies)

        # 3. Clinical closed-loop evaluation
        if dbs_active and self.c.dbs_controller:
            dbs_attack_type = "phase_shift" if self.c.twin.active_attack == "phase_shift" else ""
            self.c.dbs_controller.process_lfp(
                data_to_process, eeg_channels, sample_rate,
                attack_active=(dbs_attack_type == "phase_shift")
            )
            if secure_active and self.c.ids and self.c.ips and self.c.dbs_controller.history_beta_power:
                curr_pow = self.c.dbs_controller.history_beta_power[-1]
                stim_active = self.c.twin.stimulation_enabled
                stim_amp = self.c.twin.stimulation_amplitude_ma
                clinical_anomalies = self.c.ids.analyze_clinical(curr_pow, stim_active, stim_amp)
                self.c.ips.mitigate_pathological_sync(clinical_anomalies)
        else:
            self.c.clinical_sim.process_signal(data_to_process, eeg_channels, sample_rate)

        # 3.5 Biometric Authentication
        if getattr(self.c.config.security, 'biometric_auth', False) and self.c.biometric_gate:
            self.c.biometric_gate.authenticate_window(data_to_process, sample_rate)
            if self.c.biometric_gate.is_locked:
                print("[Coordinator] Egress blocked by BiometricGate.")
                return

        # 4. Push final data to LSL if active
        if self.c.lsl_streamer:
            lsl_data = data_to_process
            if self.c.privacy_filter is not None:
                lsl_data = self.c.privacy_filter.filter_signal(lsl_data.copy())
                if self.c.privacy_tracker:
                    self.c.privacy_tracker.consume(0.001)
                    
            if self.c.p300_analyzer is not None:
                leakage_report = self.c.p300_analyzer.scan_for_leakage(lsl_data)
                self.c.total_p300_leakage_events += leakage_report["p300_events_detected"]
                    
            self.c.lsl_streamer.push_eeg_chunk(lsl_data)
            
            active_attack = self.c.twin.active_attack
            telemetry = {
                "sim_clock": self.c.engine.sim_clock,
                "niss_score": self.c.twin.niss_score,
                "hazard_state": self.c.twin.hazard_state,
                "iso_severity": self.c.twin.iso_severity,
                "temperature_celsius": self.c.twin.temperature_celsius,
                "active_attack": active_attack
            }
            
            # Map Active Attack to Threat Intel
            if self.c.threat_intel and active_attack != "none":
                tara_intel = self.c.threat_intel.resolve_attack(active_attack)
                if tara_intel:
                    telemetry["threat_intel"] = tara_intel
            
            if self.c.config.security.enabled and self.c.ids:
                telemetry["mean_confidence"] = self.c.ids.history_confidence[-1] if self.c.ids.history_confidence else 1.0
                
            if self.c.twin.nsp_mode and self.c.nsp_wrapper:
                telemetry = self.c.nsp_wrapper.encrypt_payload(telemetry)
                
            if self.c.twin.e2ee_mode and self.c.e2ee_channel:
                telemetry = {"e2ee_payload": self.c.e2ee_channel.encrypt_payload(telemetry)}
                
            self.c.lsl_streamer.push_telemetry(telemetry)
