"""P_311: Machine Learning Model Training on UCI AI4I 2020 Predictive Maintenance Dataset.

Features:
- Air temperature [K]
- Process temperature [K]
- Rotational speed [rpm]
- Torque [Nm]
- Tool wear [min]
- Engineered Domain Features: Temp Difference, Power (W), Overstrain Risk (min*Nm)

Target Labels:
- Binary: Machine failure (0/1)
- Multi-label Root Causes: TWF, HDF, PWF, OSF, RNF
"""

import math
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import joblib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# Project root setup
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _PROJECT_ROOT / "data"
CSV_PATH = DATA_DIR / "ai4i2020.csv"
MODEL_OUTPUT_PATH = DATA_DIR / "ai4i_model.joblib"


def load_and_preprocess_data(csv_path: Path):
    """Load AI4I 2020 dataset and engineer physical domain features."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    print(f"[1/5] Loading dataset from {csv_path.name}...")
    df = pd.read_csv(csv_path)
    print(f"      Total records: {len(df):,} | Columns: {list(df.columns)}")

    # 1. Domain Feature Engineering
    # Heat dissipation depends on temperature gradient between process and ambient air
    df["temp_diff_k"] = df["Process temperature [K]"] - df["Air temperature [K]"]

    # Mechanical rotational power (Watts) = Torque (Nm) * Angular Velocity (rad/s)
    df["rotational_power_w"] = df["Torque [Nm]"] * (df["Rotational speed [rpm]"] * (2 * math.pi / 60))

    # Overstrain product = Tool Wear (min) * Torque (Nm)
    df["overstrain_risk"] = df["Tool wear [min]"] * df["Torque [Nm]"]

    # Type ordinal encoding: L (Low quality) = 0, M (Medium) = 1, H (High quality) = 2
    type_mapping = {"L": 0, "M": 1, "H": 2}
    df["type_encoded"] = df["Type"].map(type_mapping).fillna(0).astype(int)

    feature_cols = [
        "Air temperature [K]",
        "Process temperature [K]",
        "temp_diff_k",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "rotational_power_w",
        "Tool wear [min]",
        "overstrain_risk",
        "type_encoded",
    ]

    target_binary = "Machine failure"
    failure_types = ["TWF", "HDF", "PWF", "OSF", "RNF"]

    failure_counts = df[target_binary].value_counts().to_dict()
    print(f"      Distribution: Normal={failure_counts.get(0, 0):,} | Failure={failure_counts.get(1, 0):,}")
    print("      Failure modes breakdown:")
    for ft in failure_types:
        if ft in df.columns:
            print(f"        - {ft:4s}: {df[ft].sum():3d} incidents")

    return df, feature_cols, target_binary, failure_types


def train_and_evaluate(df: pd.DataFrame, feature_cols: list, target_binary: str, failure_types: list):
    """Train Random Forest classifiers and print evaluation metrics."""
    X = df[feature_cols]
    y_binary = df[target_binary]

    print(f"\n[2/5] Splitting dataset (80% train / 20% test, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_binary, test_size=0.20, random_state=42, stratify=y_binary
    )
    print(f"      Train set: {len(X_train):,} samples | Test set: {len(X_test):,} samples")

    print(f"\n[3/5] Training Random Forest Classifier (balanced class weights)...")
    rf_binary = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    rf_binary.fit(X_train, y_train)

    # Evaluate Binary Model
    y_pred = rf_binary.predict(X_test)
    y_prob = rf_binary.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)

    print("\n" + "=" * 65)
    print("            MODEL EVALUATION METRICS (TEST SET)            ")
    print("=" * 65)
    print(f"  - Overall Accuracy : {acc * 100:.2f}%")
    print(f"  - Precision        : {prec * 100:.2f}%")
    print(f"  - Recall           : {rec * 100:.2f}%")
    print(f"  - F1-Score         : {f1 * 100:.2f}%")
    print(f"  - ROC-AUC Score    : {roc_auc * 100:.2f}%")
    print("-" * 65)

    print("\nConfusion Matrix [ [TN, FP], [FN, TP] ]:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  [[{cm[0][0]:4d}, {cm[0][1]:4d}],")
    print(f"   [{cm[1][0]:4d}, {cm[1][1]:4d}]]")
    print(f"  -> True Negatives (Correct Normal) : {cm[0][0]:4d}")
    print(f"  -> False Positives (False Alarms)  : {cm[0][1]:4d}")
    print(f"  -> False Negatives (Missed Faults) : {cm[1][0]:4d}")
    print(f"  -> True Positives (Caught Faults)  : {cm[1][1]:4d}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Nominal (0)", "Failure (1)"]))

    print("Top Feature Importances:")
    importances = sorted(
        zip(feature_cols, rf_binary.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )
    for name, imp in importances:
        bar = "#" * int(imp * 35)
        print(f"  - {name:25s} : {imp:6.4f}  {bar}")

    # Train Multi-label failure mode classifier
    print(f"\n[4/5] Training Multi-Label Failure Mode Classifier for {failure_types}...")
    y_multi = df[failure_types]
    _, _, y_multi_train, y_multi_test = train_test_split(
        X, y_multi, test_size=0.20, random_state=42, stratify=y_binary
    )
    rf_multi = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf_multi.fit(X_train, y_multi_train)

    return rf_binary, rf_multi, {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": roc_auc,
        "confusion_matrix": cm.tolist(),
        "feature_importances": dict(importances),
    }


def save_model(model_binary, model_multi, feature_cols, failure_types, metrics, output_path: Path):
    """Save trained models and metadata to a single joblib archive."""
    print(f"\n[5/5] Saving model bundle to {output_path.name}...")
    bundle = {
        "model_binary": model_binary,
        "model_multi": model_multi,
        "feature_cols": feature_cols,
        "failure_types": failure_types,
        "metrics": metrics,
        "type_mapping": {"L": 0, "M": 1, "H": 2},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output_path)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"      Model saved successfully! ({size_mb:.2f} MB)")


def demonstrate_inference(model_path: Path):
    """Run interactive demonstration classifying sample machine scenarios."""
    print("\n" + "=" * 65)
    print("           SAMPLE INFERENCE DEMONSTRATION                  ")
    print("=" * 65)
    bundle = joblib.load(model_path)
    model = bundle["model_binary"]
    multi = bundle["model_multi"]
    cols = bundle["feature_cols"]

    test_cases = [
        {
            "name": "Scenario A: Nominal Steady-State (L-type machine)",
            "data": {
                "Air temperature [K]": 298.1,
                "Process temperature [K]": 308.6,
                "temp_diff_k": 10.5,
                "Rotational speed [rpm]": 1550,
                "Torque [Nm]": 42.0,
                "rotational_power_w": 42.0 * (1550 * 2 * math.pi / 60),
                "Tool wear [min]": 15,
                "overstrain_risk": 15 * 42.0,
                "type_encoded": 0,
            },
        },
        {
            "name": "Scenario B: Severe Heat Dissipation & Power Imbalance",
            "data": {
                "Air temperature [K]": 302.5,
                "Process temperature [K]": 310.5,
                "temp_diff_k": 8.0,  # below 8.6 K critical threshold
                "Rotational speed [rpm]": 1280,
                "Torque [Nm]": 68.5,  # high torque, low speed
                "rotational_power_w": 68.5 * (1280 * 2 * math.pi / 60),
                "Tool wear [min]": 195,
                "overstrain_risk": 195 * 68.5,
                "type_encoded": 0,
            },
        },
        {
            "name": "Scenario C: Advanced Tool Wear Failure (TWF)",
            "data": {
                "Air temperature [K]": 298.8,
                "Process temperature [K]": 308.9,
                "temp_diff_k": 10.1,
                "Rotational speed [rpm]": 1450,
                "Torque [Nm]": 44.0,
                "rotational_power_w": 44.0 * (1450 * 2 * math.pi / 60),
                "Tool wear [min]": 225,  # tool wear exceeded 200 min limit
                "overstrain_risk": 225 * 44.0,
                "type_encoded": 0,
            },
        },
    ]

    for tc in test_cases:
        row = pd.DataFrame([tc["data"]])[cols]
        is_failure = model.predict(row)[0]
        prob = model.predict_proba(row)[0][1]
        modes = multi.predict(row)[0]
        active_modes = [name for name, active in zip(bundle["failure_types"], modes) if active == 1]

        status_str = "FAILURE DETECTED" if is_failure else "NOMINAL OPERATION"
        print(f"\n{tc['name']}:")
        print(f"  - Prediction  : [{status_str}] (Failure Probability: {prob*100:.1f}%)")
        if active_modes:
            print(f"  - Root Causes : {', '.join(active_modes)}")
        else:
            print(f"  - Root Causes : None (Healthy Machine)")


def main():
    df, feature_cols, target_binary, failure_types = load_and_preprocess_data(CSV_PATH)
    model_binary, model_multi, metrics = train_and_evaluate(df, feature_cols, target_binary, failure_types)
    save_model(model_binary, model_multi, feature_cols, failure_types, metrics, MODEL_OUTPUT_PATH)
    demonstrate_inference(MODEL_OUTPUT_PATH)


if __name__ == "__main__":
    main()
