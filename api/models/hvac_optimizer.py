import pandas as pd
import numpy as np
from sklearn import linear_model, metrics
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib
import json
import hashlib
from datetime import datetime, timedelta
from itertools import combinations
from typing import List, Tuple, Dict, Optional, Any
import statistics
import matplotlib.pyplot as plt
from sqlalchemy.orm import Session

from .predictor import Predictor, TrainingHistory
from db import SessionLocal

class HVACOptimizer:
    """
    HVAC Energy Optimization class with location-based model management.
    
    Implements two-phase prediction:
    1. Linear Regression for HVAC OFF state
    2. Random Forest for HVAC ON state with energy consumption and temperature delta prediction
    
    Features location-aware model storage and retrieval based on latitude/longitude.
    """
    
    # Constants
    MODEL_NOT_TRAINED_ERROR = "Model not trained. Please train the model first."
    
    def __init__(self, latitude: float, longitude: float, location_tolerance: float = 0.01):
        """
        Initialize HVAC Optimizer for a specific location.
        
        Args:
            latitude: Geographic latitude of the location
            longitude: Geographic longitude of the location
            location_tolerance: Tolerance for finding nearby models (degrees)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.location_tolerance = location_tolerance
        
        # Model parameters (will be loaded from DB or set during training)
        self.a_coefficient = None  # Linear regression coefficient for HVAC OFF
        self.avg_consumption_off = None  # Average energy consumption when HVAC OFF
        self.rf_model = None  # Random Forest model for HVAC ON
        self.model_id = None  # Database ID of the loaded model
        
        # Load existing model for this location if available
        self._load_location_model()
    
    def _load_location_model(self) -> bool:
        """
        Load existing trained model for the current location from database.
        
        Returns:
            bool: True if model was loaded successfully, False otherwise
        """
        db = SessionLocal()
        try:
            # Find model within location tolerance
            model = db.query(Predictor).filter(
                Predictor.model_type == 'hvac_optimizer',
                Predictor.latitude.between(
                    self.latitude - self.location_tolerance,
                    self.latitude + self.location_tolerance
                ),
                Predictor.longitude.between(
                    self.longitude - self.location_tolerance,
                    self.longitude + self.location_tolerance
                )
            ).order_by(Predictor.updated_at.desc()).first()
            
            if model and model.model_data:
                model_data = model.model_data
                self.a_coefficient = model_data.get('a_coefficient')
                self.avg_consumption_off = model_data.get('avg_consumption_off')
                self.model_id = model.id
                
                # Load Random Forest model if available
                if 'rf_model_path' in model_data:
                    try:
                        self.rf_model = joblib.load(model_data['rf_model_path'])
                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except Exception:
                        self.rf_model = None
                
                print(f"Loaded HVAC model for location ({self.latitude}, {self.longitude})")
                return True
            
            print(f"No existing model found for location ({self.latitude}, {self.longitude})")
            return False
            
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
        finally:
            db.close()
    
    def train_full_pipeline(self, csv_path: str, knowledge_id: int = 1) -> Dict[str, Any]:
        """
        Complete training pipeline including data preprocessing, model training, and database storage.
        
        Args:
            csv_path: Path to the training CSV file
            knowledge_id: ID of the knowledge record to associate with
            
        Returns:
            Dict containing training results and metrics
        """
        db = SessionLocal()
        training_record = None
        
        try:
            # Create training history record
            training_record = TrainingHistory(
                latitude=self.latitude,
                longitude=self.longitude,
                training_status='started',
                training_started_at=datetime.now()
            )
            db.add(training_record)
            db.commit()
            
            print(f"Starting HVAC training for location ({self.latitude}, {self.longitude})")
            
            # 1. Data preprocessing
            print("Step 1: Data preprocessing...")
            x_off, y_off, x_on, y_on = self._preprocess_data(csv_path)
            
            # Calculate data hash for version control
            data_hash = self._calculate_data_hash(csv_path)
            
            # 2. Train Linear Regression for HVAC OFF
            print("Step 2: Training Linear Regression (HVAC OFF)...")
            a_coeff, avg_cons_off, lr_metrics = self._train_linear_regression(x_off, y_off)
            
            # 3. Compute Delta T for HVAC ON training
            print("Step 3: Computing Delta T for HVAC ON...")
            x_on_processed, y_on_processed = self._compute_delta_t(x_on, y_on, a_coeff)
            
            # 4. Train Random Forest for HVAC ON
            print("Step 4: Training Random Forest (HVAC ON)...")
            rf_model, rf_metrics = self._train_random_forest(x_on_processed, y_on_processed)
            
            # 5. Save models to database
            print("Step 5: Saving models to database...")
            model_path = f"hvac_model_{self.latitude}_{self.longitude}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            joblib.dump(rf_model, model_path)
            
            # Store model in database
            predictor = Predictor(
                name=f"HVAC_Optimizer_lat_{self.latitude}_lon_{self.longitude}",
                framework="scikit-learn",
                model_type="hvac_optimizer",
                latitude=self.latitude,
                longitude=self.longitude,
                knowledge_id=knowledge_id,
                training_data_hash=data_hash,
                model_data={
                    'a_coefficient': float(a_coeff),
                    'avg_consumption_off': float(avg_cons_off),
                    'rf_model_path': model_path,
                    'linear_regression_metrics': lr_metrics,
                    'random_forest_metrics': rf_metrics
                },
                scores={
                    'linear_regression': lr_metrics,
                    'random_forest': rf_metrics
                }
            )
            
            db.add(predictor)
            db.commit()
            
            # Update training history
            training_record.predictor_id = predictor.id
            training_record.training_status = 'completed'
            training_record.training_completed_at = datetime.now()
            training_record.training_metrics = {
                'linear_regression': lr_metrics,
                'random_forest': rf_metrics
            }
            training_record.data_size = len(x_off) + len(x_on)
            training_record.model_parameters = {
                'location_tolerance': self.location_tolerance,
                'rf_n_estimators': 100,
                'rf_max_depth': 25
            }
            db.commit()
            
            # Update instance variables
            self.a_coefficient = a_coeff
            self.avg_consumption_off = avg_cons_off
            self.rf_model = rf_model
            self.model_id = predictor.id
            
            print(f"Training completed successfully. Model ID: {predictor.id}")
            
            return {
                'model_id': predictor.id,
                'linear_regression_metrics': lr_metrics,
                'random_forest_metrics': rf_metrics,
                'training_time': (training_record.training_completed_at - training_record.training_started_at).total_seconds()
            }
            
        except Exception as e:
            print(f"Training failed: {e}")
            if training_record:
                training_record.training_status = 'failed'
                training_record.notes = str(e)
                db.commit()
            raise e
        finally:
            db.close()
    
    def _preprocess_data(self, csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Preprocess CSV data and split by HVAC operation status."""
        data = []
        with open(csv_path, newline="") as csvfile:
            import csv
            reader = csv.reader(csvfile, delimiter=',')
            for row in reader:
                data.append(row)
        
        data.pop(0)  # Remove header
        
        hvac_off_in, hvac_off_out, hvac_off_prev = [], [], []
        hvac_on_in, hvac_on_out, hvac_on_prev = [], [], []
        time_on = []
        setpoint_on = []
        energy_consumption_off, energy_consumption_on = [], []
        outlet, inlet, diff = [], [], []
        
        for i in range(1, len(data)):
            if data[i][2] == '0':  # HVAC OFF
                hvac_off_in.append(float(data[i][1]))
                hvac_off_out.append(float(data[i][3]))
                hvac_off_prev.append(float(data[i-1][1]))
                energy_consumption_off.append(float(data[i][4]))
            else:  # HVAC ON
                hvac_on_in.append(float(data[i][1]))
                hvac_on_out.append(float(data[i][3]))
                hvac_on_prev.append(float(data[i-1][1]))
                time_on.append(data[i][0])
                energy_consumption_on.append(float(data[i][4]))
                setpoint_on.append(float(data[i][5]))
                outlet.append(float(data[i][6]))
                inlet.append(float(data[i][7]))
                diff.append(float(data[i][3]) - float(data[i][5]))
        
        # Create DataFrames for HVAC OFF
        x_off = pd.DataFrame({
            'prev_indoor_temp': hvac_off_prev,
            'outdoor_temp': hvac_off_out
        })
        y_off = pd.DataFrame({
            'indoor_temp': hvac_off_in,
            'energy_consumption': energy_consumption_off
        })
        
        # Create DataFrames for HVAC ON
        df_on = pd.DataFrame({
            'prev_indoor_temp': hvac_on_prev,
            'outdoor_temp': hvac_on_out,
            'stp': setpoint_on,
            'diff': diff,
            'inlet': inlet,
            'outlet': outlet,
            'Date': time_on
        })
        
        # Process time parameters
        x_on = df_on[['Date', 'prev_indoor_temp', 'outdoor_temp', 'stp', 'diff']].copy()
        x_on['Date'] = pd.to_datetime(df_on['Date'], format='%d/%m/%Y %H:%M')
        x_on['hour'] = x_on['Date'].dt.hour
        x_on['minute'] = x_on['Date'].dt.minute
        x_on['dayofweek'] = x_on['Date'].dt.dayofweek
        x_on['month'] = x_on['Date'].dt.month
        x_on = x_on.drop(columns='Date')
        x_on['inlet'] = df_on['inlet']
        x_on['outlet'] = df_on['outlet']
        
        y_on = pd.DataFrame({
            'indoor_temp': hvac_on_in,
            'energy_consumption': energy_consumption_on
        })
        
        return x_off, y_off, x_on, y_on
    
    def _train_linear_regression(self, x_off: pd.DataFrame, y_off: pd.DataFrame) -> Tuple[float, float, Dict]:
        """Train linear regression model for HVAC OFF state."""
        # Split data
        x_train, x_test, y_train, y_test = train_test_split(
            x_off, y_off, train_size=0.8, test_size=0.2, random_state=0
        )
        
        # Modify data for linear regression: Tin(t) - Tin(t-1) = a(Tout(t-1) - Tin(t-1))
        x_train_mod = pd.DataFrame(x_train['outdoor_temp'] - x_train['prev_indoor_temp'])
        y_train_mod = pd.DataFrame(y_train['indoor_temp'] - x_train['prev_indoor_temp'])
        
        # Calculate average consumption when AC is OFF
        avg_cons_off = statistics.mean(y_train['energy_consumption'])
        
        # Train linear regression
        regr = linear_model.LinearRegression(fit_intercept=False)
        regr.fit(x_train_mod, y_train_mod)
        a_coeff = regr.coef_[0][0]
        
        # Evaluate model
        x_test_mod = pd.DataFrame(x_test['outdoor_temp'] - x_test['prev_indoor_temp'])
        y_test_mod = pd.DataFrame(y_test['indoor_temp'] - x_test['prev_indoor_temp'])
        y_pred = regr.predict(x_test_mod)
        
        metrics_dict = {
            'r2_score': float(metrics.r2_score(y_test_mod, y_pred)),
            'rmse': float(np.sqrt(metrics.mean_squared_error(y_test_mod, y_pred))),
            'mae': float(metrics.mean_absolute_error(y_test_mod, y_pred)),
            'mape': float(metrics.mean_absolute_percentage_error(y_test_mod, y_pred))
        }
        
        return a_coeff, avg_cons_off, metrics_dict
    
    def _compute_delta_t(self, x_on: pd.DataFrame, y_on: pd.DataFrame, a_coeff: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Compute Delta T for HVAC ON training data."""
        # Split data
        x_train_dt, x_test_dt, y_train_dt, y_test_dt = train_test_split(
            x_on, y_on, train_size=0.8, test_size=0.2, random_state=0
        )
        
        # Compute Delta T for training data
        dts_train = (y_train_dt['indoor_temp'] - x_train_dt['prev_indoor_temp'] - 
                    a_coeff * (x_train_dt['outdoor_temp'] - x_train_dt['prev_indoor_temp']))
        
        # Compute Delta T for test data
        dts_test = (y_test_dt['indoor_temp'] - x_test_dt['prev_indoor_temp'] - 
                   a_coeff * (x_test_dt['outdoor_temp'] - x_test_dt['prev_indoor_temp']))
        
        # Add Delta T to datasets
        y_train_dt = y_train_dt.copy()
        y_test_dt = y_test_dt.copy()
        y_train_dt['DT'] = dts_train
        y_test_dt['DT'] = dts_test
        
        return pd.concat([x_train_dt, x_test_dt]), pd.concat([y_train_dt, y_test_dt])
    
    def _train_random_forest(self, x_on: pd.DataFrame, y_on: pd.DataFrame) -> Tuple[RandomForestRegressor, Dict]:
        """Train Random Forest model for HVAC ON state."""
        # Select best features based on notebook analysis
        feature_cols = ['prev_indoor_temp', 'outdoor_temp', 'stp', 'hour', 'minute', 'dayofweek', 'month']
        x_features = x_on[feature_cols]
        y_targets = y_on[['energy_consumption', 'DT']]
        
        # Split data
        x_train, x_test, y_train, y_test = train_test_split(
            x_features, y_targets, train_size=0.8, test_size=0.2, random_state=0
        )
        
        # Explicitly set all relevant hyperparameters for reproducibility and SonarQube compliance
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=25,
            min_samples_leaf=1,
            max_features='auto',
            random_state=0
        )
        rf_model.fit(x_train, y_train)
        
        # Evaluate model
        y_pred = rf_model.predict(x_test)
        
        # Calculate metrics for energy consumption
        energy_metrics = {
            'r2_score': float(metrics.r2_score(y_test['energy_consumption'], y_pred[:, 0])),
            'rmse': float(np.sqrt(metrics.mean_squared_error(y_test['energy_consumption'], y_pred[:, 0]))),
            'mae': float(metrics.mean_absolute_error(y_test['energy_consumption'], y_pred[:, 0])),
            'mape': float(metrics.mean_absolute_percentage_error(y_test['energy_consumption'], y_pred[:, 0]))
        }
        
        # Calculate metrics for Delta T
        dt_metrics = {
            'r2_score': float(metrics.r2_score(y_test['DT'], y_pred[:, 1])),
            'rmse': float(np.sqrt(metrics.mean_squared_error(y_test['DT'], y_pred[:, 1]))),
            'mae': float(metrics.mean_absolute_error(y_test['DT'], y_pred[:, 1])),
            'mape': float(metrics.mean_absolute_percentage_error(y_test['DT'], y_pred[:, 1]))
        }
        
        metrics_dict = {
            'energy_consumption': energy_metrics,
            'delta_t': dt_metrics,
            'feature_importance': dict(zip(feature_cols, rf_model.feature_importances_.tolist()))
        }
        
        return rf_model, metrics_dict
    
    def _calculate_data_hash(self, csv_path: str) -> str:
        """Calculate hash of training data for version control."""
        with open(csv_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
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
            raise ValueError(self.MODEL_NOT_TRAINED_ERROR)
        
        temp = [starting_temp]
        start = datetime.strptime(starting_time, '%d/%m/%Y %H:%M')
        h, m, d, month, dayofweek = start.hour, start.minute, start.day, start.month, start.weekday()
        
        total_cons = 0
        
        for i in range(duration):
            if operation[i] == 1:  # HVAC ON
                df = pd.DataFrame({
                    'prev_indoor_temp': [temp[i]],
                    'outdoor_temp': [outdoor_temps[i+1]],
                    'stp': [setpoint],
                    'hour': [h],
                    'minute': [m],
                    'dayofweek': [dayofweek],
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
            raise ValueError(self.MODEL_NOT_TRAINED_ERROR)
        
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
            raise ValueError(self.MODEL_NOT_TRAINED_ERROR)
        
        best_score = float('inf')
        best_result = None
        
        for num_switches in [1, 2]:
            result = self._search_with_switches(
                num_switches, starting_temp, starting_time, outdoor_temps, setpoint, duration
            )
            if result and result['total_score'] < best_score:
                best_score = result['total_score']
                best_result = result
        
        return best_result
    
    def _search_with_switches(self, num_switches: int, starting_temp: float, 
                             starting_time: str, outdoor_temps: List[float], 
                             setpoint: float, duration: int) -> Dict[str, Any]:
        """
        Search for best operation schedule with a specific number of switches.
        
        Returns:
            Dict containing best operation schedule for this switch count
        """
        best_score = float('inf')
        best_result = None
        
        for switches in combinations(range(duration), num_switches):
            for starting_operation in [0, 1]:
                operation = self._build_operation_schedule(switches, starting_operation, duration)
                result = self._evaluate_operation_schedule(
                    operation, starting_temp, starting_time, outdoor_temps, setpoint, duration
                )
                
                if result['total_score'] < best_score:
                    best_score = result['total_score']
                    best_result = result
        
        return best_result
    
    def _build_operation_schedule(self, switches: tuple, starting_operation: int, 
                                 duration: int) -> List[int]:
        """
        Build operation schedule based on switch points and starting operation.
        
        Args:
            switches: Tuple of time points where operation switches
            starting_operation: Initial operation state (0 or 1)
            duration: Total duration in time steps
            
        Returns:
            List of operation states for each time step
        """
        operation = []
        current = starting_operation
        operation.append(current)
        
        for i in range(duration):
            if i in switches:
                current ^= 1
            operation.append(current)
        
        return operation
    
    def _evaluate_operation_schedule(self, operation: List[int], starting_temp: float, 
                                   starting_time: str, outdoor_temps: List[float], 
                                   setpoint: float, duration: int) -> Dict[str, Any]:
        """
        Evaluate an operation schedule and return results with operation included.
        
        Returns:
            Dict containing evaluation results with operation schedule
        """
        result = self.evaluate_schedule(
            operation, starting_temp, starting_time, outdoor_temps, setpoint, duration
        )
        result['operation'] = operation
        return result
    
    def normal_conditions_optimizer(self, starting_temp: float, starting_time: str, 
                                  outdoor_temps: List[float], setpoint: float, 
                                  duration: int = 12) -> Dict[str, Any]:
        """
        Optimizer for normal conditions (non-peak hours).
        
        Returns:
            Dict containing recommended operation and savings analysis
        """
        if not self._is_model_ready():
            raise ValueError(self.MODEL_NOT_TRAINED_ERROR)
        
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
        if result_off['temperatures'][-1] <= setpoint + 1.0:  # Tolerance of 1°C
            savings_percent = ((result_on['total_energy_consumption'] - result_off['total_energy_consumption']) / 
                              result_on['total_energy_consumption']) * 100
            
            return {
                'recommended_operation': operation_off,
                'recommendation_type': 'all_off',
                'energy_consumption': result_off['total_energy_consumption'],
                'temperatures': result_off['temperatures'],
                'savings_percentage': savings_percent,
                'avg_deviation_from_setpoint': result_off['avg_deviation_from_setpoint']
            }
        else:
            # Use optimization
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
                'avg_deviation_from_setpoint': optimized_result['avg_deviation_from_setpoint']
            }
    
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
    
    def get_training_history(self) -> List[Dict]:
        """Get training history for this location."""
        db = SessionLocal()
        try:
            history = db.query(TrainingHistory).filter(
                TrainingHistory.latitude.between(
                    self.latitude - self.location_tolerance,
                    self.latitude + self.location_tolerance
                ),
                TrainingHistory.longitude.between(
                    self.longitude - self.location_tolerance,
                    self.longitude + self.location_tolerance
                )
            ).order_by(TrainingHistory.training_started_at.desc()).all()
            
            return [{
                'id': record.id,
                'training_started_at': record.training_started_at.isoformat() if record.training_started_at else None,
                'training_completed_at': record.training_completed_at.isoformat() if record.training_completed_at else None,
                'training_status': record.training_status,
                'training_metrics': record.training_metrics,
                'data_size': record.data_size,
                'notes': record.notes
            } for record in history]
            
        finally:
            db.close()
    
    def _is_model_ready(self) -> bool:
        """Check if model is ready for predictions."""
        return (self.a_coefficient is not None and 
                self.avg_consumption_off is not None and 
                self.rf_model is not None)
    
    @classmethod
    def get_all_location_models(cls) -> List[Dict]:
        """Get all HVAC models across all locations."""
        db = SessionLocal()
        try:
            models = db.query(Predictor).filter(
                Predictor.model_type == 'hvac_optimizer'
            ).all()
            
            return [{
                'id': model.id,
                'latitude': model.latitude,
                'longitude': model.longitude,
                'name': model.name,
                'created_at': model.created_at.isoformat() if model.created_at else None,
                'updated_at': model.updated_at.isoformat() if model.updated_at else None,
                'scores': model.scores
            } for model in models]
            
        finally:
            db.close()
