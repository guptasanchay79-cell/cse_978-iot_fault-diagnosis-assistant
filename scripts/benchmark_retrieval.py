"""Benchmark script to evaluate RAG retrieval accuracy across all fault modes."""

from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rag.retriever import TFIDFRetriever

def main():
    retriever = TFIDFRetriever()
    queries = [
        ("Overheating Mode", "Industrial centrifugal pump pump_centrifugal_01 exhibits severe motor stator / bearing overheating at 82.50 C exceeding thermal safety threshold of 75.0 C, and rapid thermal climb rate. Current telemetry shows temperature 82.50 C.", ["KB03_motor_winding_overheating.md", "KB04_bearing_housing_thermal_runaway.md"]),
        ("Bearing Wear Mode", "Industrial centrifugal pump pump_centrifugal_01 exhibits critical bearing vibration velocity RMS of 6.24 mm/s exceeding ISO 10816 Zone D danger limit of 4.5 mm/s, and secondary frictional temperature rise of 67.80 C. Current telemetry shows vibration 6.24 mm/s.", ["KB01_bearing_inner_raceway_fatigue.md", "KB02_bearing_lubrication_starvation.md"]),
        ("Pressure Drop / Cavitation Mode", "Industrial centrifugal pump pump_centrifugal_01 exhibits critical hydraulic discharge pressure drop to 2.10 bar falling below low operational limit of 3.0 bar, and hydraulic cavitation turbulence with vibration fluctuations. Discharge pressure is 2.10 bar.", ["KB05_discharge_pipe_rupture_leakage.md", "KB06_impeller_cavitation_hydraulic_loss.md"]),
        ("Sensor Flatline Mode", "Industrial centrifugal pump pump_centrifugal_01 exhibits temperature sensor flat-line detected: value frozen at 54.00 C with 0.00 variance across consecutive readings.", ["KB08_adc_telemetry_sensor_flatline.md"]),
        ("Sensor Disconnect Mode", "Industrial centrifugal pump pump_centrifugal_01 telemetry sensor failure: temperature sensor reading (-999.0 C) is outside physical valid range (sensor disconnect / open-circuit).", ["KB07_rtd_temperature_sensor_disconnect.md"]),
    ]

    for name, query, targets in queries:
        print(f"\n=== {name} ===")
        print(f"Query: {query}")
        results = retriever.retrieve(query, top_k=3)
        top_files = [r["source_file"] for r in results]
        hit = any(t in top_files for t in targets)
        print(f"Target in Top 3: {hit}")
        for r in results:
            print(f"  Rank #{r['rank']} | Score: {r['score']:.4f} | Source: {r['source_file']} | Section: {r['section_title']}")

if __name__ == "__main__":
    main()
