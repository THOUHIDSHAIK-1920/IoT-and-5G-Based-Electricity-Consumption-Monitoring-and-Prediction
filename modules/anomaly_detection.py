"""
VoltSense 5G - Module 2: Anomaly Detection Engine
Multi-tier detection using Statistical Rules (Z-Score, IQR) and Machine Learning (Scikit-Learn Isolation Forest).
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from sklearn.ensemble import IsolationForest

from database.database import DatabaseManager
from config import (
    VOLTAGE_MIN_NORMAL_V,
    VOLTAGE_MAX_NORMAL_V,
    VOLTAGE_CRITICAL_LOW_V,
    VOLTAGE_CRITICAL_HIGH_V,
    NOMINAL_VOLTAGE_V,
    TARGET_POWER_FACTOR
)


class AnomalyDetector:
    """
    Identifies electrical disturbances, abnormal power spikes, off-hours leakage, and non-linear outliers.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db

    def scan_and_log_anomalies(
        self, 
        device_id: Optional[str] = None, 
        sensitivity: float = 0.03,
        method: str = "HYBRID"  # 'STATISTICAL', 'ISOLATION_FOREST', 'HYBRID'
    ) -> pd.DataFrame:
        """
        Scans readings in database, applies mathematical detection models, logs anomalies, and returns findings.
        """
        df = self.db.get_readings(device_id=device_id, order="ASC")
        if df.empty or len(df) < 15:
            return pd.DataFrame()

        detected_events = []

        if method in ("STATISTICAL", "HYBRID"):
            stat_anomalies = self._detect_statistical_and_domain_anomalies(df)
            detected_events.extend(stat_anomalies)

        if method in ("ISOLATION_FOREST", "HYBRID"):
            ml_anomalies = self._detect_isolation_forest_anomalies(df, contamination=sensitivity)
            detected_events.extend(ml_anomalies)

        # De-duplicate events by (device_id, timestamp, metric)
        unique_events = {}
        for ev in detected_events:
            key = (ev["device_id"], str(ev["timestamp"]), ev["metric"])
            if key not in unique_events or (ev["severity"] == "CRITICAL" and unique_events[key]["severity"] != "CRITICAL"):
                unique_events[key] = ev

        event_list = list(unique_events.values())

        # Persist detected events to SQLite anomalies table
        if event_list:
            self.db.insert_anomalies_bulk(event_list)

        # Retrieve full anomalies dataframe with device metadata
        return self.db.get_anomalies(device_id=device_id)

    def _detect_statistical_and_domain_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Applies rolling statistical Z-score, IQR, and IEEE 1459 grid bounds."""
        anomalies = []

        for dev_id, group in df.groupby("device_id"):
            g = group.sort_values("timestamp").copy()
            if not pd.api.types.is_datetime64_any_dtype(g["timestamp"]):
                g["timestamp"] = pd.to_datetime(g["timestamp"])

            # 1. Grid Voltage Sag / Surge Violations
            for _, row in g.iterrows():
                v = float(row["voltage"])
                ts = str(row["timestamp"])

                if v <= VOLTAGE_CRITICAL_LOW_V:
                    anomalies.append({
                        "device_id": dev_id,
                        "timestamp": ts,
                        "metric": "Grid Voltage (V)",
                        "detected_value": v,
                        "expected_range": f"{VOLTAGE_MIN_NORMAL_V}V - {VOLTAGE_MAX_NORMAL_V}V",
                        "severity": "CRITICAL",
                        "detection_method": "Electrical Limit",
                        "reason": f"Severe Grid Brownout / Voltage Sag ({v:.1f}V < {VOLTAGE_CRITICAL_LOW_V}V)"
                    })
                elif v >= VOLTAGE_CRITICAL_HIGH_V:
                    anomalies.append({
                        "device_id": dev_id,
                        "timestamp": ts,
                        "metric": "Grid Voltage (V)",
                        "detected_value": v,
                        "expected_range": f"{VOLTAGE_MIN_NORMAL_V}V - {VOLTAGE_MAX_NORMAL_V}V",
                        "severity": "CRITICAL",
                        "detection_method": "Electrical Limit",
                        "reason": f"High Voltage Surge / Swell ({v:.1f}V > {VOLTAGE_CRITICAL_HIGH_V}V)"
                    })

                # 2. Power Factor Degradation
                pf = float(row["power_factor"])
                if pf < 0.70:
                    anomalies.append({
                        "device_id": dev_id,
                        "timestamp": ts,
                        "metric": "Power Factor (cos φ)",
                        "detected_value": pf,
                        "expected_range": ">= 0.85",
                        "severity": "MEDIUM" if pf >= 0.60 else "CRITICAL",
                        "detection_method": "Electrical Limit",
                        "reason": f"Severe Reactive Power Load (PF {pf:.2f} < 0.70) - APFC failure"
                    })

            # 3. Active Power Z-Score and IQR Spikes
            power_series = g["active_power"]
            mean_p = power_series.mean()
            std_p = power_series.std()
            q25 = power_series.quantile(0.25)
            q75 = power_series.quantile(0.75)
            iqr = q75 - q25
            iqr_upper_bound = q75 + (2.5 * iqr)

            if std_p > 0:
                z_scores = (power_series - mean_p) / std_p
                spike_mask = (z_scores > 3.0) | (power_series > iqr_upper_bound)

                for _, row in g[spike_mask].iterrows():
                    val = float(row["active_power"])
                    z_val = float(z_scores.loc[row.name])
                    anomalies.append({
                        "device_id": dev_id,
                        "timestamp": str(row["timestamp"]),
                        "metric": "Active Power (W)",
                        "detected_value": val,
                        "expected_range": f"<= {iqr_upper_bound:.1f} W (Z: {z_val:.1f})",
                        "severity": "CRITICAL" if z_val > 4.5 else "MEDIUM",
                        "detection_method": "Z-Score",
                        "reason": f"Unexpected power surge: {val:,.1f}W ({z_val:.1f}σ above device baseline)"
                    })

            # 4. Off-Hours Base Load Leakage (Night hours 01:00 - 05:00)
            g["hour"] = g["timestamp"].dt.hour
            night_mask = g["hour"].isin([1, 2, 3, 4])
            night_mean = g.loc[night_mask, "active_power"].mean() if night_mask.any() else 0
            if night_mean > 0:
                leakage_rows = g[night_mask & (g["active_power"] > (night_mean * 3.0))]
                for _, row in leakage_rows.iterrows():
                    val = float(row["active_power"])
                    anomalies.append({
                        "device_id": dev_id,
                        "timestamp": str(row["timestamp"]),
                        "metric": "Unscheduled Night Load (W)",
                        "detected_value": val,
                        "expected_range": f"Normal night base: ~{night_mean:.0f} W",
                        "severity": "MEDIUM",
                        "detection_method": "IQR Rule",
                        "reason": f"Off-hours energy leakage at {row['timestamp'].strftime('%H:%M')} ({val:,.1f}W)"
                    })

        return anomalies

    def _detect_isolation_forest_anomalies(self, df: pd.DataFrame, contamination: float = 0.03) -> List[Dict[str, Any]]:
        """Applies multi-dimensional unsupervised Isolation Forest."""
        anomalies = []
        if len(df) < 30:
            return anomalies

        df_ml = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_ml["timestamp"]):
            df_ml["timestamp"] = pd.to_datetime(df_ml["timestamp"])

        df_ml["hour"] = df_ml["timestamp"].dt.hour
        df_ml["dayofweek"] = df_ml["timestamp"].dt.dayofweek

        feature_cols = ["voltage", "current", "active_power", "power_factor", "hour"]
        X = df_ml[feature_cols].fillna(0).values

        # Isolation Forest fit
        iso = IsolationForest(
            n_estimators=100,
            contamination=max(0.01, min(0.10, contamination)),
            random_state=42
        )
        preds = iso.fit_predict(X)
        scores = iso.decision_function(X)

        df_ml["is_outlier"] = preds == -1
        df_ml["anomaly_score"] = scores

        outliers = df_ml[df_ml["is_outlier"]]
        for _, row in outliers.iterrows():
            score = float(row["anomaly_score"])
            severity = "CRITICAL" if score < -0.15 else "MEDIUM"
            anomalies.append({
                "device_id": str(row["device_id"]),
                "timestamp": str(row["timestamp"]),
                "metric": "Multi-dimensional Outlier",
                "detected_value": float(row["active_power"]),
                "expected_range": f"Iso-Score >= 0.0 (Got {score:.3f})",
                "severity": severity,
                "detection_method": "Isolation Forest",
                "reason": f"Multivariate divergence in electrical profile (Score: {score:.3f})"
            })

        return anomalies
