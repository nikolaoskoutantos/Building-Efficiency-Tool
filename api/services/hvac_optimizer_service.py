# --- Standard Library Imports ---
import os
import sys
import json
import hashlib
import statistics
import socket
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import List, Tuple, Dict, Optional, Any
from urllib.parse import urlparse

# --- Third-Party Imports ---
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model, metrics
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# --- MLflow Setup ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
try:
    import mlflow
    from mlflow.tracking import MlflowClient
except ModuleNotFoundError:
    mlflow = None
    MlflowClient = None

# --- Path Setup (if needed for local imports) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set MLflow tracking URI from .env or default to localhost
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
if mlflow is not None and MlflowClient is not None:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow_client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
else:
    mlflow_client = None

from db import SessionLocal
from utils.building_sensor_weather_snapshot import (
    create_snapshot_batch,
    fetch_building_sensor_weather_rows,
)

# --- Deduplicated String Literals ---
MODEL_TYPE = "hvac_optimizer"
TRAINING_STATUS_STARTED = "started"
TRAINING_STATUS_COMPLETED = "completed"
TRAINING_STATUS_FAILED = "failed"
FRAMEWORK = "scikit-learn"
LINEAR_REGRESSION = "linear_regression"
RANDOM_FOREST = "random_forest"
ENERGY_CONSUMPTION = "energy_consumption"
DELTA_T = "delta_t"
LOCATION = "location"
RECOMMENDED_OPERATION = "recommended_operation"
SAVINGS_PERCENTAGE = "savings_percentage"
AVG_DEVIATION_FROM_SETPOINT = "avg_deviation_from_setpoint"
ALL_OFF = "all_off"
NORMAL = "normal"
PEAK = "peak"
OPERATION = "operation"
TOTAL_SCORE = "total_score"
COMFORT_PENALTY = "comfort_penalty"
SWITCH_PENALTY = "switch_penalty"
TEMPERATURES = "temperatures"
MODELS = "models"
TRAINING_HISTORY = "training_history"
PREDICTOR = "predictor"
KNOWLEDGE = "knowledge"
SENSOR = "sensor"
ERR_MODEL_NOT_TRAINED = "HVAC model is not ready. Train or load MLflow models first."
ERR_MLFLOW_UNAVAILABLE = "MLflow tracking server is unavailable."


class HVACOptimizerService:
        RF_MODEL_NAME = "energy_temp_rf"
        LEGACY_RF_MODEL_NAME = "hvac_random_forest"


        def _set_model_load_failure(self, message: str, should_print: bool = False) -> bool:
            if should_print:
                print(message)
            self.model_load_error = message
            self.rf_model = None
            return False

        def _ensure_mlflow_runtime_available(self) -> bool:
            if mlflow is None or MlflowClient is None:
                return self._set_model_load_failure(
                    "MLflow is not installed in this environment.",
                    should_print=True,
                )
            return True

        def _ensure_mlflow_tracking_uri_reachable(self) -> bool:
            parsed_uri = urlparse(MLFLOW_TRACKING_URI)
            if not parsed_uri.hostname or not parsed_uri.port:
                return True

            try:
                connection = socket.create_connection((parsed_uri.hostname, parsed_uri.port), timeout=1.5)
                connection.close()
            except OSError as exc:
                return self._set_model_load_failure(
                    f"{ERR_MLFLOW_UNAVAILABLE} {exc}",
                    should_print=True,
                )
            return True

        def _find_latest_random_forest_model_version(
            self,
            client: MlflowClient,
            building_id: str,
        ) -> tuple[Any, Optional[str]]:
            candidate_model_names = [self.RF_MODEL_NAME, self.LEGACY_RF_MODEL_NAME]
            for model_name in candidate_model_names:
                versions = client.search_model_versions(
                    f"name = '{model_name}' and tags.buildingID = '{building_id}'"
                )
                if versions:
                    return max(versions, key=lambda mv: mv.creation_timestamp), model_name

            print(
                f"No model versions found for {candidate_model_names} "
                f"with buildingID={building_id}"
            )
            self.model_load_error = (
                f"No MLflow model versions found for building {building_id}."
            )
            return None, None

        def _apply_model_version_tags(self, model_version: Any) -> None:
            if not model_version.tags:
                return

            a_tag = model_version.tags.get("a_coefficient")
            if a_tag is not None:
                self.a_coefficient = float(a_tag)

            avg_cons_tag = model_version.tags.get("avg_consumption_off")
            if avg_cons_tag is not None:
                self.avg_consumption_off = float(avg_cons_tag)

        def _load_random_forest_from_mlflow(self) -> bool:
            """
            Load random forest model and optional avg_consumption_off from latest MLflow model version for this building.
            Expects model registered under RF_MODEL_NAME and tagged with buildingID.
            """
            if not self._ensure_mlflow_runtime_available():
                return False

            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_registry_uri(MLFLOW_TRACKING_URI)
            building_id = str(self.building_id)
            try:
                if not self._ensure_mlflow_tracking_uri_reachable():
                    return False

                client = MlflowClient(tracking_uri=mlflow.get_tracking_uri(), registry_uri=mlflow.get_registry_uri())
                latest, chosen_model_name = self._find_latest_random_forest_model_version(client, building_id)
                if latest is None or chosen_model_name is None:
                    return False

                model_uri = f"models:/{chosen_model_name}/{latest.version}"
                self.rf_model = mlflow.sklearn.load_model(model_uri)
                self.model_load_error = None

                self._apply_model_version_tags(latest)

                print(
                    f"Loaded Random Forest model from MLflow for building {self.building_id} "
                    f"from '{chosen_model_name}' (version {latest.version})"
                )
                return True
            except Exception as e:
                print(f"Error fetching Random Forest model from MLflow: {e}")
                return self._set_model_load_failure(f"Failed to load MLflow model: {e}")

        def __init__(self, building_id: int, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
            import time
            t0 = time.time()
            """
            Initialize HVAC Optimizer service for a specific building.
            Args:
                building_id: Building ID for dataset/model fetching
                start_time: Optional start datetime for dataset
                end_time: Optional end datetime for dataset
            """
            self.building_id = building_id
            self.start_time = start_time
            self.end_time = end_time

            # Latitude/longitude will be fetched from DB using building_id
            self.latitude = None
            self.longitude = None

            # Model parameters (will be loaded from DB or set during training)
            self.a_coefficient = None  # Linear regression coefficient for HVAC OFF
            self.avg_consumption_off = None  # Average energy consumption when HVAC OFF
            self.rf_model = None  # Random Forest model for HVAC ON
            self.model_id = None  # Database ID of the loaded model
            self.model_load_error = None

            # Fetch lat/lon from DB and load model
            print("[HVACOptimizerService] Initializing location and models...")
            self._init_location_and_model()
            print(f"[HVACOptimizerService] Location/model init took {time.time() - t0:.2f} seconds")

            # Fetch dataset for this building and time range
            t1 = time.time()
            print("[HVACOptimizerService] Fetching building sensor weather data...")
            self.data = self._fetch_building_sensor_weather()
            print(f"[HVACOptimizerService] Data fetch took {time.time() - t1:.2f} seconds")

        def _generate_operation(self, duration: int, switches, starting_operation: int) -> List[int]:
            """Generate the 12-step service schedule used by the app/API."""
            current = starting_operation
            operation: List[int] = []
            for i in range(duration):
                if i in switches:
                    current ^= 1
                operation.append(current)
            return operation

        def _generate_notebook_operation(self, duration: int, switches, starting_operation: int) -> List[int]:
            """Generate the raw notebook optimizer output (initial state + duration steps)."""
            current = starting_operation
            operation: List[int] = [current]
            for i in range(duration):
                if i in switches:
                    current ^= 1
                operation.append(current)
            return operation

        def _evaluate_candidate(self, operation, starting_temp, starting_time, outdoor_temps, setpoint, duration):
            result = self.evaluate_schedule(
                operation, starting_temp, starting_time, outdoor_temps, setpoint, duration
            )
            result['operation'] = operation
            return result

        def _fetch_building_sensor_weather(self):
            """Fetch building sensor weather data as a DataFrame."""
            import pandas as pd
            db = SessionLocal()
            try:
                start, end = self._resolve_query_window()
                print("DEBUG: Querying time range:")
                print(f"  start: {start}")
                print(f"  end: {end}")

                rows = fetch_building_sensor_weather_rows(db, self.building_id, start, end)
                df = pd.DataFrame(rows) if rows else pd.DataFrame()
                
                # Debug: Print sample of actual fetched data
                print(f"DEBUG: Fetched {len(df)} rows")
                if len(df) > 0:
                    print("DEBUG: Sample sensor_value values:", df['sensor_value'].head(10).tolist())
                    print("DEBUG: Sample temperature values:", df['temperature'].head(10).tolist())
                    print("DEBUG: First 3 rows:")
                    print(df.head(3).to_string())
                
                return df
            finally:
                db.close()

        def _resolve_query_window(self):
            if self.start_time is None and self.end_time is None:
                start = datetime(2026, 3, 2, 17, 0, 0)
                end = datetime(2026, 3, 2, 18, 0, 0)
            else:
                end = self.end_time or datetime.now(timezone.utc)
                start = self.start_time or (end - timedelta(hours=1))
            return start, end

        def create_input_snapshot(self, created_by_user_id: int | None = None, source_label: str = "hvac_optimizer_service"):
            db = SessionLocal()
            try:
                start, end = self._resolve_query_window()
                rows = fetch_building_sensor_weather_rows(db, self.building_id, start, end)
                return create_snapshot_batch(
                    db,
                    building_id=self.building_id,
                    start_time=start,
                    end_time=end,
                    rows=rows,
                    created_by_user_id=created_by_user_id,
                    source_label=source_label,
                )
            finally:
                db.close()

        def _init_location_and_model(self):
            """Fetch latitude/longitude from DB using building_id and load model."""
            import time
            from sqlalchemy import text
            db = SessionLocal()
            try:
                t0 = time.time()
                building = db.execute(
                    text("SELECT lat, lon FROM public.buildings WHERE id = :bid"),
                    {'bid': self.building_id}
                ).fetchone()
                print(f"[HVACOptimizerService] DB lat/lon query took {time.time() - t0:.2f} seconds")
                if building:
                    self.latitude = building.lat
                    self.longitude = building.lon

                    # Load Random Forest model (includes LR parameters from tags)
                    t1 = time.time()
                    print("[HVACOptimizerService] Loading random forest model from MLflow...")
                    self._load_random_forest_model()
                    print(f"[HVACOptimizerService] Random forest model load took {time.time() - t1:.2f} seconds")
                   
                else:
                    raise ValueError(f"Building ID {self.building_id} not found in DB.")
            finally:
                db.close()


        def _load_random_forest_model(self) -> bool:
            """Load Random Forest model for the current building from MLflow."""
            return self._load_random_forest_from_mlflow()

        def _get_model_not_ready_error(self) -> str:
            return self.model_load_error or ERR_MODEL_NOT_TRAINED
            
        def _transform_data_for_rf(self) -> pd.DataFrame:
            """
            Transform database data from long format to wide format for Random Forest.
            Uses the 'a' parameter for temperature calculations.
            
            Returns:
                DataFrame with columns: prev_indoor_temp, outdoor_temp, stp, hour, minute, dayofweek, month
            """
            if self.data.empty:
                return pd.DataFrame()
            
            print("Debug: Checking data columns and values...")
            print(f"Weather temperature values: {self.data['temperature'].dropna().unique()}")
            print("Sensor values by type:")
            for sensor_type in self.data['sensor_type'].unique():
                sensor_data = self.data[self.data['sensor_type'] == sensor_type]['sensor_value']
                non_null_count = sensor_data.dropna().shape[0]
                print(f"  {sensor_type}: {non_null_count} non-null values out of {len(sensor_data)}")
            
            # Get unique time intervals with weather and HVAC data  
            intervals = self.data.drop_duplicates(['hvac_interval_start', 'hvac_interval_end']).copy()
            intervals = intervals[['hvac_interval_start', 'hvac_interval_end', 'temperature', 'hvac_setpoint', 'hvac_is_on']]
            
            # Remove timezone from datetime columns
            print("Debug: Removing timezone from timestamps...")
            if pd.api.types.is_datetime64_any_dtype(intervals['hvac_interval_start']):
                intervals['hvac_interval_start'] = pd.to_datetime(intervals['hvac_interval_start']).dt.tz_localize(None)
            if pd.api.types.is_datetime64_any_dtype(intervals['hvac_interval_end']):
                intervals['hvac_interval_end'] = pd.to_datetime(intervals['hvac_interval_end']).dt.tz_localize(None)
            
            intervals = intervals.sort_values('hvac_interval_start').reset_index(drop=True)
            
            print(f"Debug: Found {len(intervals)} unique time intervals")
            print("Sample intervals:")
            print(intervals.head())
            
            # Create RF features
            rf_data = []
            for i in range(1, len(intervals)):
                # Use default indoor temp since sensor readings are None
                # In production, you'd get this from actual temperature sensor
                prev_indoor_temp = 22.0  # Default starting indoor temperature
                
                # Current interval data
                current = intervals.iloc[i]
                outdoor_temp = current['temperature']  # Weather temperature
                setpoint = current['hvac_setpoint'] 
                timestamp = pd.to_datetime(current['hvac_interval_start'])
                
                if pd.notna(outdoor_temp) and pd.notna(setpoint):
                    rf_data.append({
                        'prev_indoor_temp': prev_indoor_temp,
                        'outdoor_temp': outdoor_temp,
                        'stp': setpoint,
                        'hour': timestamp.hour,
                        'minute': timestamp.minute,
                        'dayofweek': timestamp.weekday(),
                        'month': timestamp.month
                    })
            
            result = pd.DataFrame(rf_data)
            print(f"Debug: Created {len(result)} RF training samples")
            return result

        def train_full_pipeline(self, sensor_id: int, knowledge_id: int = 1, days_back: int = 30) -> Dict[str, Any]:
            raise ValueError("Training is disabled in HVACOptimizerService. Use pre-trained models from MLflow.")

        def predict_one_hour(self, operation: List[int], starting_temp: float, 
                            starting_time: str, outdoor_temps: List[float], 
                            setpoint: float, duration: int = 12) -> Tuple[float, List[float]]:
            """
            Predict temperature and energy consumption for the next hour.
            
            Args:
                operation: List of HVAC operations (0/1) for each time step
                starting_temp: Current indoor temperature
                starting_time: Starting timestamp in format '%d/%m/%Y %H:%M'
                outdoor_temps: Forecast outdoor temperatures
                setpoint: AC setpoint temperature
                duration: Number of 5-minute intervals (default 12 = 1 hour)
                
            Returns:
                Tuple of (total_energy_consumption, temperature_predictions)
            """
            if not self._is_model_ready():
                raise ValueError(self._get_model_not_ready_error())
            
            temp = [starting_temp]
            start = datetime.strptime(starting_time, '%d/%m/%Y %H:%M')
            h, m, d, month, _ = start.hour, start.minute, start.day, start.month, start.weekday()
            
            total_cons = 0
            
            for i in range(duration):
                if operation[i] == 1:  # HVAC ON
                    df = pd.DataFrame({
                        'prev_indoor_temp': [temp[i]],
                        'outdoor_temp': [outdoor_temps[i+1]],
                        'stp': [setpoint],
                        'hour': [h],
                        'minute': [m],
                        # Match the notebook's inference logic exactly, even though it
                        # uses day-of-month rather than weekday for this feature.
                        'dayofweek': [d],
                        'month': [month]
                    })
                    pred = self.rf_model.predict(df)
                    total_cons += pred[0][0]
                    temp.append(temp[i] + self.a_coefficient * (outdoor_temps[i+1] - temp[i]) + pred[0][1])
                else:  # HVAC OFF
                    total_cons += self.avg_consumption_off
                    temp.append(temp[i] + self.a_coefficient * (outdoor_temps[i+1] - temp[i]))
                
                # Update time
                m += 5
                if m == 60:
                    m = 0
                    h += 1
                if h == 24:
                    h = 0
                    d += 1
                if d == 31:
                    d = 1
                    month += 1
            
            return total_cons, temp

        def evaluate_schedule(self, operation: List[int], starting_temp: float, 
                                starting_time: str, outdoor_temps: List[float], 
                                setpoint: float, duration: int = 12) -> Dict[str, Any]:
            """
            Evaluate an operation schedule with penalty scoring.
            
            Returns:
                Dict containing energy consumption, comfort penalty, switch penalty, temperatures, and total score
            """
            if not self._is_model_ready():
                raise ValueError(self._get_model_not_ready_error())
            
            comfort_penalty_weight = 50
            switch_penalty_weight = 10
            
            total_cons, temp = self.predict_one_hour(
                operation, starting_temp, starting_time, outdoor_temps, setpoint, duration
            )
            
            # Calculate comfort penalty
            comfort_penalty = sum((t - setpoint)**2 for t in temp[1:])
            
            # Calculate switch penalty
            switch_penalty = sum(1 for i in range(1, duration) if operation[i] != operation[i-1])
            
            # Total score
            score = comfort_penalty_weight * comfort_penalty + switch_penalty_weight * switch_penalty + total_cons
            
            return {
                'total_energy_consumption': total_cons,
                'comfort_penalty': comfort_penalty,
                'switch_penalty': switch_penalty,
                'temperatures': temp,
                'total_score': score,
                'avg_deviation_from_setpoint': sum(abs(t - setpoint) for t in temp[1:]) / len(temp[1:])
            }

        def biased_random_search(self, starting_temp: float, starting_time: str, 
                                outdoor_temps: List[float], setpoint: float, 
                                duration: int = 12) -> Dict[str, Any]:
            """
            Optimized search for best operation schedule (peak hours optimization).
            
            Returns:
                Dict containing best operation schedule and its evaluation
            """
            if not self._is_model_ready():
                raise ValueError(self._get_model_not_ready_error())

            best_score = float('inf')
            best_result = None

            for num_switches in [1, 2]:
                for switches in combinations(range(duration), num_switches):
                    for starting_operation in [0, 1]:
                        notebook_raw_operation = self._generate_notebook_operation(duration, switches, starting_operation)
                        operation = notebook_raw_operation[:-1]
                        result = self._evaluate_candidate(operation, starting_temp, starting_time, outdoor_temps, setpoint, duration)
                        result['notebook_raw_operation'] = notebook_raw_operation
                        result['notebook_effective_operation'] = operation
                        if result['total_score'] < best_score:
                            best_score = result['total_score']
                            best_result = result

            return best_result

        def normal_conditions_optimizer(self, starting_temp: float, starting_time: str, 
                                        outdoor_temps: List[float], setpoint: float, 
                                        duration: int = 12) -> Dict[str, Any]:
            """
            Optimizer for normal conditions (non-peak hours).
            
            Returns:
                Dict containing recommended operation and savings analysis
            """
            if not self._is_model_ready():
                raise ValueError(self._get_model_not_ready_error())
            
            # Test all OFF operation
            operation_off = [0] * duration
            result_off = self.evaluate_schedule(
                operation_off, starting_temp, starting_time, outdoor_temps, setpoint, duration
            )
            
            # Test all ON operation
            operation_on = [1] * duration
            result_on = self.evaluate_schedule(
                operation_on, starting_temp, starting_time, outdoor_temps, setpoint, duration
            )
            
            # Check if OFF maintains comfort
            if result_off['temperatures'][-1] > setpoint:
                optimized_result = self.biased_random_search(
                    starting_temp, starting_time, outdoor_temps, setpoint, duration
                )
                
                savings_percent = ((result_on['total_energy_consumption'] - optimized_result['total_energy_consumption']) / 
                                    result_on['total_energy_consumption']) * 100
                
                return {
                    'recommended_operation': optimized_result['operation'],
                    'recommendation_type': 'optimized',
                    'energy_consumption': optimized_result['total_energy_consumption'],
                    'temperatures': optimized_result['temperatures'],
                    'savings_percentage': savings_percent,
                    'avg_deviation_from_setpoint': optimized_result['avg_deviation_from_setpoint'],
                    'notebook_raw_operation': optimized_result.get('notebook_raw_operation'),
                    'notebook_effective_operation': optimized_result.get('notebook_effective_operation', optimized_result['operation']),
                    'baseline_all_off': {
                        'operation': operation_off,
                        'energy_consumption': result_off['total_energy_consumption'],
                        'temperatures': result_off['temperatures'],
                    },
                    'baseline_all_on': {
                        'operation': operation_on,
                        'energy_consumption': result_on['total_energy_consumption'],
                        'temperatures': result_on['temperatures'],
                    },
                    'optimized_candidate': {
                        'operation': optimized_result['operation'],
                        'energy_consumption': optimized_result['total_energy_consumption'],
                        'temperatures': optimized_result['temperatures'],
                    },
                    'notebook_payload': self._build_notebook_payload(
                        optimized_result.get('notebook_raw_operation', optimized_result['operation']),
                        optimized_result['temperatures'],
                        optimized_result['total_energy_consumption'],
                        effective_operation=optimized_result.get('notebook_effective_operation', optimized_result['operation']),
                    ),
                }
            else:
                savings_percent = ((result_on['total_energy_consumption'] - result_off['total_energy_consumption']) / 
                                    result_on['total_energy_consumption']) * 100
                
                return {
                    'recommended_operation': operation_off,
                    'recommendation_type': 'all_off',
                    'energy_consumption': result_off['total_energy_consumption'],
                    'temperatures': result_off['temperatures'],
                    'savings_percentage': savings_percent,
                    'avg_deviation_from_setpoint': result_off['avg_deviation_from_setpoint'],
                    'baseline_all_off': {
                        'operation': operation_off,
                        'energy_consumption': result_off['total_energy_consumption'],
                        'temperatures': result_off['temperatures'],
                    },
                    'baseline_all_on': {
                        'operation': operation_on,
                        'energy_consumption': result_on['total_energy_consumption'],
                        'temperatures': result_on['temperatures'],
                    },
                    'notebook_payload': self._build_notebook_payload(
                        operation_off,
                        result_off['temperatures'],
                        result_off['total_energy_consumption'],
                    ),
                }

        def _to_notebook_optimization_response(self, result: Dict[str, Any]) -> Tuple[List[int], List[float], float]:
            """
            Convert the service-level optimization payload into the notebook's raw return signature:
            (recommended_operation, temperatures, energy_consumption).
            """
            return (
                (result.get("notebook_payload") or result)[RECOMMENDED_OPERATION],
                (result.get("notebook_payload") or result)[TEMPERATURES],
                (result.get("notebook_payload") or result)["energy_consumption"],
            )

        def _build_notebook_payload(
            self,
            operation: List[int],
            temperatures: List[float],
            energy_consumption: float,
            effective_operation: Optional[List[int]] = None,
        ) -> Dict[str, Any]:
            """
            Embed the notebook-equivalent optimization payload inside the richer service response.
            """
            payload = {
                RECOMMENDED_OPERATION: operation,
                TEMPERATURES: temperatures,
                "energy_consumption": energy_consumption,
            }
            if effective_operation is not None:
                payload["effective_operation"] = effective_operation
            return payload

        def get_optimization_recommendation(self, starting_temp: float, starting_time: str,
                                          outdoor_temps: List[float], setpoint: float, 
                                          is_peak_hours: bool = False, duration: int = 12,
                                          response_format: str = "dict") -> Dict[str, Any] | Tuple[List[int], List[float], float]:
            """
            Get HVAC optimization recommendation using Random Forest model.
            
            Args:
                starting_temp: Current indoor temperature
                starting_time: Starting timestamp in format '%d/%m/%Y %H:%M'
                outdoor_temps: Forecast outdoor temperatures (13 values for 12 intervals)
                setpoint: AC setpoint temperature
                is_peak_hours: True for peak hours optimization, False for normal conditions
                duration: Number of 5-minute intervals (default 12 = 1 hour)
                response_format: "dict" for the service response shape, or "notebook"
                    for the notebook's raw tuple signature
                    (recommended_operation, temperatures, energy_consumption)
                
            Returns:
                Either:
                - Dict containing recommendation, energy consumption, savings, and comfort metrics
                - Tuple matching the notebook signature:
                  (recommended_operation, temperatures, energy_consumption)
            """
            if not self._is_model_ready():
                raise ValueError(self._get_model_not_ready_error())

            if response_format not in {"dict", "notebook"}:
                raise ValueError("response_format must be either 'dict' or 'notebook'")
            
            if is_peak_hours:
                # Peak hours: Use biased random search for optimal schedule
                result = self.biased_random_search(
                    starting_temp, starting_time, outdoor_temps, setpoint, duration
                )
                response = {
                    'recommendation_type': 'peak_hours_optimized',
                    'recommended_operation': result['operation'],
                    'energy_consumption': result['total_energy_consumption'],
                    'temperatures': result['temperatures'],
                    'total_score': result['total_score'],
                    'comfort_penalty': result['comfort_penalty'],
                    'switch_penalty': result['switch_penalty'],
                    'avg_deviation_from_setpoint': result['avg_deviation_from_setpoint'],
                    'notebook_raw_operation': result.get('notebook_raw_operation'),
                    'notebook_effective_operation': result.get('notebook_effective_operation', result['operation']),
                    'notebook_payload': self._build_notebook_payload(
                        result.get('notebook_raw_operation', result['operation']),
                        result['temperatures'],
                        result['total_energy_consumption'],
                        effective_operation=result.get('notebook_effective_operation', result['operation']),
                    ),
                }
                if response_format == "notebook":
                    return self._to_notebook_optimization_response(response)
                return response
            else:
                # Normal conditions: Smart optimization
                response = self.normal_conditions_optimizer(
                    starting_temp, starting_time, outdoor_temps, setpoint, duration
                )
                if response_format == "notebook":
                    return self._to_notebook_optimization_response(response)
                return response

        def get_evaluation_metrics(self, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
            """
            Calculate evaluation metrics for model assessment.
            
            Args:
                y_true: Actual values
                y_pred: Predicted values
                
            Returns:
                Dict containing various evaluation metrics
            """
            return {
                'explained_variance': float(metrics.explained_variance_score(y_true, y_pred)),
                'mean_absolute_error': float(metrics.mean_absolute_error(y_true, y_pred)),
                'mape': float(metrics.mean_absolute_percentage_error(y_true, y_pred)),
                'mse': float(metrics.mean_squared_error(y_true, y_pred)),
                'rmse': float(np.sqrt(metrics.mean_squared_error(y_true, y_pred))),
                'r2_score': float(metrics.r2_score(y_true, y_pred)),
                'normalized_rmse': float(np.sqrt(metrics.mean_squared_error(y_true, y_pred)) / 
                                        (max(y_true) - min(y_true)))
            }

        @staticmethod
        def register_notebook_models_to_mlflow(building_id: int, notebook_rf_model_path: str = None, 
                                              a_coefficient: float = None, avg_cons_off: float = None):
            """
            Helper method to register Random Forest model and parameters from notebook to MLflow.
            
            Args:
                building_id: Building ID to tag the models with
                notebook_rf_model_path: Path to the trained RF model .pkl file from notebook
                a_coefficient: The 'a' parameter from linear regression  
                avg_cons_off: Average consumption when HVAC OFF
            """
            if mlflow is None:
                print("MLflow is not installed in this environment, cannot register notebook models.")
                return
            import mlflow.sklearn
            import joblib
            
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_registry_uri(MLFLOW_TRACKING_URI)
            
            # Default values from notebook if not provided
            if a_coefficient is None:
                a_coefficient = 0.00144072
            if avg_cons_off is None:
                avg_cons_off = 0.38
            if notebook_rf_model_path is None:
                notebook_rf_model_path = "random_forest_model.pkl"
            
            try:
                # Load RF model from notebook
                rf_model = joblib.load(notebook_rf_model_path)
                
                with mlflow.start_run(run_name=f"hvac_rf_building_{building_id}"):
                    # Log and register Random Forest model
                    mlflow.sklearn.log_model(
                        rf_model,
                        "random_forest",
                        registered_model_name=HVACOptimizerService.RF_MODEL_NAME
                    )
                    
                    # Log parameters as metrics and tags
                    mlflow.log_param("building_id", building_id)
                    mlflow.log_param("a_coefficient", a_coefficient)
                    mlflow.log_param("avg_consumption_off", avg_cons_off)
                    mlflow.log_metric("avg_consumption_off_value", avg_cons_off)
                    
                    # Get model version and add tags
                    model_version = mlflow.tracking.MlflowClient().get_latest_versions(
                        HVACOptimizerService.RF_MODEL_NAME, stages=["None"]
                    )[0]
                    
                    mlflow.tracking.MlflowClient().set_model_version_tag(
                        HVACOptimizerService.RF_MODEL_NAME,
                        model_version.version,
                        "buildingID", 
                        str(building_id)
                    )
                    
                    mlflow.tracking.MlflowClient().set_model_version_tag(
                        HVACOptimizerService.RF_MODEL_NAME,
                        model_version.version,
                        "avg_consumption_off", 
                        str(avg_cons_off)
                    )
                    
                print(f"✅ Successfully registered RF model for building {building_id}")
                print(f"   - Model: {HVACOptimizerService.RF_MODEL_NAME} v{model_version.version}")
                print(f"   - Tags: buildingID={building_id}, avg_consumption_off={avg_cons_off}")
                
            except Exception as e:
                print(f"❌ Error registering model: {e}")

        def _is_model_ready(self) -> bool:
            """Check if model is ready for predictions."""
            return (self.a_coefficient is not None and 
                    self.avg_consumption_off is not None and 
                    self.rf_model is not None)
