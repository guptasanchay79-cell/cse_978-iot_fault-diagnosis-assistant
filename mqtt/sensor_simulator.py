"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: mqtt/sensor_simulator.py
Simulates realistic IoT telemetry for an industrial centrifugal pump.
Supports smooth continuous physics-based drift (Ornstein-Uhlenbeck random walk)
and progressive fault signatures (overheating, bearing wear, pressure drop, sensor failure).
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
import random
import signal
import sys
import time
from typing import Any, Dict, Optional

# Ensure project root is in sys.path regardless of execution directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import paho.mqtt.client as mqtt

from config import (
    ALL_FAULT_MODES,
    DEFAULT_DEVICE_ID,
    FAULT_MODE_BEARING_WEAR,
    FAULT_MODE_NORMAL,
    FAULT_MODE_OVERHEATING,
    FAULT_MODE_PRESSURE_DROP,
    FAULT_MODE_SENSOR_FAILURE,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE_SECONDS,
    MQTT_TELEMETRY_TOPIC,
    PRESSURE_LOW_THRESHOLD,
    PRESSURE_NORMAL_MAX,
    PRESSURE_NORMAL_MIN,
    SIM_MEAN_REVERSION_RATE,
    SIM_NOISE_STD_PRESSURE,
    SIM_NOISE_STD_TEMP,
    SIM_NOISE_STD_VIB,
    TELEMETRY_PUBLISH_INTERVAL,
    TEMP_NORMAL_MAX,
    TEMP_NORMAL_MIN,
    TEMP_WARNING_THRESHOLD,
    VIB_NORMAL_MAX,
    VIB_NORMAL_MIN,
    VIB_WARNING_THRESHOLD,
)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SensorSimulator")

_RUNNING = True


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle termination signals (Ctrl+C) gracefully."""
    global _RUNNING
    logger.info("Shutdown signal received (%d). Terminating simulator cleanly...", signum)
    _RUNNING = False


class PumpTelemetrySimulator:
    """Stateful physical telemetry simulator for an industrial centrifugal pump.

    Uses mean-reverting drift and Gaussian noise for baseline steady-state,
    and models physical progressive fault dynamics.
    """

    def __init__(
        self,
        device_id: str = DEFAULT_DEVICE_ID,
        mode: str = FAULT_MODE_NORMAL,
        sensor_failure_type: str = "flatline",
        test_mode: bool = False,
    ) -> None:
        self.device_id = device_id
        self.mode = mode
        self.sensor_failure_type = sensor_failure_type
        self.test_mode = test_mode
        self.step_count = 0

        # Baseline setpoints (nominal healthy operating points)
        self.target_temp = 54.0
        self.target_vib = 1.4
        self.target_pressure = 5.0

        # Current internal state
        self.current_temp = self.target_temp
        self.current_vib = self.target_vib
        self.current_pressure = self.target_pressure

        # Snapshot value for flatline sensor simulation
        self._frozen_temp_reading: Optional[float] = None

    def _drift(self, current: float, target: float, std_noise: float) -> float:
        """Apply mean-reverting Ornstein-Uhlenbeck drift with Gaussian noise."""
        noise = random.gauss(0.0, std_noise)
        restoring = SIM_MEAN_REVERSION_RATE * (target - current)
        return current + restoring + noise

    def step(self) -> Dict[str, Any]:
        """Advance simulation by one time step and produce a telemetry dictionary."""
        self.step_count += 1
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if self.mode == FAULT_MODE_NORMAL:
            # Healthy steady-state with natural physical drift
            self.current_temp = self._drift(self.current_temp, self.target_temp, SIM_NOISE_STD_TEMP)
            self.current_vib = self._drift(self.current_vib, self.target_vib, SIM_NOISE_STD_VIB)
            self.current_pressure = self._drift(
                self.current_pressure, self.target_pressure, SIM_NOISE_STD_PRESSURE
            )

        elif self.mode == FAULT_MODE_OVERHEATING:
            # Motor winding/bearing cooling breakdown: temperature climbs progressively
            # Target elevated temperature: 80.0°C - 85.0°C (Warning threshold is 75.0°C)
            overheat_target = 82.0
            if self.current_temp < overheat_target:
                self.current_temp += random.uniform(1.2, 2.2)
            else:
                self.current_temp = self._drift(self.current_temp, overheat_target, SIM_NOISE_STD_TEMP)

            # Vibration and pressure remain within normal parameters
            self.current_vib = self._drift(self.current_vib, self.target_vib, SIM_NOISE_STD_VIB)
            self.current_pressure = self._drift(
                self.current_pressure, self.target_pressure, SIM_NOISE_STD_PRESSURE
            )

        elif self.mode == FAULT_MODE_BEARING_WEAR:
            # Progressive mechanical degradation: vibration climbs past ISO Class II threshold (4.5 mm/s)
            vib_target = 6.2
            if self.current_vib < vib_target:
                self.current_vib += random.uniform(0.4, 0.8)
            else:
                self.current_vib = self._drift(self.current_vib, vib_target, SIM_NOISE_STD_VIB)

            # Secondary friction causes slight temperature climb (elevated, but below pure overheat)
            if self.current_temp < 68.0:
                self.current_temp += random.uniform(0.2, 0.4)
            else:
                self.current_temp = self._drift(self.current_temp, 68.0, SIM_NOISE_STD_TEMP)

            # Pressure remains normal
            self.current_pressure = self._drift(
                self.current_pressure, self.target_pressure, SIM_NOISE_STD_PRESSURE
            )

        elif self.mode == FAULT_MODE_PRESSURE_DROP:
            # Discharge line rupture / impeller cavitation: pressure falls rapidly below 3.0 bar
            pressure_target = 2.0
            if self.current_pressure > pressure_target:
                self.current_pressure -= random.uniform(0.35, 0.6)
            else:
                self.current_pressure = self._drift(
                    self.current_pressure, pressure_target, SIM_NOISE_STD_PRESSURE
                )

            # Cavitation bubbles collapsing cause turbulent vibration jitter
            cavitation_vib_target = self.target_vib + 0.6
            self.current_vib = self._drift(self.current_vib, cavitation_vib_target, 0.15)
            self.current_temp = self._drift(self.current_temp, self.target_temp, SIM_NOISE_STD_TEMP)

        elif self.mode == FAULT_MODE_SENSOR_FAILURE:
            # Normal physical pump conditions, but telemetry sensor malfunctions
            self.current_vib = self._drift(self.current_vib, self.target_vib, SIM_NOISE_STD_VIB)
            self.current_pressure = self._drift(
                self.current_pressure, self.target_pressure, SIM_NOISE_STD_PRESSURE
            )

            if self.sensor_failure_type == "disconnect":
                # Out-of-range sensor disconnect value
                out_temp = -999.0
            else:
                # Frozen flatline: sensor locks onto the first captured value with zero variance
                if self._frozen_temp_reading is None:
                    self._frozen_temp_reading = round(self.current_temp, 2)
                out_temp = self._frozen_temp_reading

        else:
            raise ValueError(f"Unknown simulation mode: {self.mode}")

        # Assemble final payload
        if self.mode == FAULT_MODE_SENSOR_FAILURE:
            final_temp = out_temp
        else:
            final_temp = round(self.current_temp, 2)

        payload: Dict[str, Any] = {
            "device_id": self.device_id,
            "timestamp": timestamp,
            "temperature": final_temp,
            "vibration": round(self.current_vib, 2),
            "pressure": round(self.current_pressure, 2),
        }

        # Hidden ground truth label included ONLY in test/evaluation mode
        if self.test_mode:
            payload["ground_truth_fault"] = self.mode

        return payload


def generate_baseline_telemetry(device_id: str = DEFAULT_DEVICE_ID) -> Dict[str, Any]:
    """Generate a single healthy baseline telemetry reading formatted as a dictionary.

    Convenience function for callers and test suites.
    """
    sim = PumpTelemetrySimulator(device_id=device_id, mode=FAULT_MODE_NORMAL, test_mode=False)
    return sim.step()


def on_connect(
    client: mqtt.Client,
    userdata: Any,
    flags: mqtt.ConnectFlags,
    rc: mqtt.ReasonCode,
    properties: Any = None,
) -> None:
    """Paho MQTT 2.x on_connect callback."""
    if rc.is_failure:
        logger.error("Failed to connect to MQTT broker: %s", rc)
    else:
        logger.info(
            "Connected to Mosquitto broker at %s:%d (Reason: %s)",
            MQTT_BROKER_HOST,
            MQTT_BROKER_PORT,
            rc,
        )


def run_simulator(
    host: str = MQTT_BROKER_HOST,
    port: int = MQTT_BROKER_PORT,
    topic: str = MQTT_TELEMETRY_TOPIC,
    device_id: str = DEFAULT_DEVICE_ID,
    mode: str = FAULT_MODE_NORMAL,
    sensor_failure_type: str = "flatline",
    test_mode: bool = False,
    interval: float = TELEMETRY_PUBLISH_INTERVAL,
    count: Optional[int] = None,
) -> int:
    """Run telemetry simulator with specified operational or fault mode."""
    global _RUNNING
    _RUNNING = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    simulator = PumpTelemetrySimulator(
        device_id=device_id,
        mode=mode,
        sensor_failure_type=sensor_failure_type,
        test_mode=test_mode,
    )

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"simulator_{device_id}_{mode}",
    )
    client.on_connect = on_connect

    try:
        logger.info("Connecting to Mosquitto at %s:%d...", host, port)
        client.connect(host, port, keepalive=MQTT_KEEPALIVE_SECONDS)
        client.loop_start()
    except Exception as exc:
        logger.error("Broker connection failed: %s", exc)
        return 1

    published_count = 0
    try:
        logger.info(
            "Streaming telemetry: Mode='%s' | Topic='%s' | TestMode=%s | Interval=%.1fs | Count=%s",
            mode,
            topic,
            test_mode,
            interval,
            "infinite" if count is None else count,
        )
        while _RUNNING:
            payload = simulator.step()
            payload_str = json.dumps(payload)

            result = client.publish(topic, payload_str, qos=1)
            result.wait_for_publish(timeout=5.0)

            extra_gt = f" [GT: {payload['ground_truth_fault']}]" if "ground_truth_fault" in payload else ""
            logger.info(
                "[PUBLISHED] Mode=%-14s | Temp=%6.2f C | Vib=%4.2f mm/s | Press=%4.2f bar%s",
                mode,
                payload["temperature"],
                payload["vibration"],
                payload["pressure"],
                extra_gt,
            )

            published_count += 1
            if count is not None and published_count >= count:
                logger.info("Target count of %d messages reached.", count)
                break

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught.")
    finally:
        logger.info("Disconnecting simulator client...")
        client.loop_stop()
        client.disconnect()
        logger.info(
            "Simulator shutdown complete. Published %d messages in mode '%s'.",
            published_count,
            mode,
        )

    return 0


def main() -> int:
    """Parse CLI arguments and run simulator."""
    parser = argparse.ArgumentParser(
        description="P_311 Realistic Industrial Pump Telemetry Simulator"
    )
    parser.add_argument("--host", default=MQTT_BROKER_HOST, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=MQTT_BROKER_PORT, help="MQTT broker port")
    parser.add_argument("--topic", default=MQTT_TELEMETRY_TOPIC, help="MQTT topic")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID, help="Device ID")
    parser.add_argument(
        "--mode",
        choices=ALL_FAULT_MODES,
        default=FAULT_MODE_NORMAL,
        help=f"Simulation mode: {', '.join(ALL_FAULT_MODES)} (default: normal)",
    )
    parser.add_argument(
        "--sensor-failure-type",
        choices=["flatline", "disconnect"],
        default="flatline",
        help="Type of sensor failure if --mode sensor_failure is selected (default: flatline)",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Attach hidden ground_truth_fault label to payload for evaluation scoring",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=TELEMETRY_PUBLISH_INTERVAL,
        help="Streaming interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of messages to publish before exit (default: infinite)",
    )

    args = parser.parse_args()
    return run_simulator(
        host=args.host,
        port=args.port,
        topic=args.topic,
        device_id=args.device_id,
        mode=args.mode,
        sensor_failure_type=args.sensor_failure_type,
        test_mode=args.test_mode,
        interval=args.interval,
        count=args.count,
    )


if __name__ == "__main__":
    sys.exit(main())
