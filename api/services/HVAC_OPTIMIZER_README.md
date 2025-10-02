# HVAC Optimizer Service - Location-Based Energy Optimization

## Overview

The HVAC Optimizer Service is a machine learning-based system for optimizing HVAC energy consumption while maintaining thermal comfort. The system uses location-aware models (based on latitude/longitude) to provide accurate predictions and optimization recommendations tailored to specific geographic locations and climate conditions.

## Architecture

### Service Layer Design
- **Service**: `HVACOptimizerService` - Contains all business logic and ML operations
- **Models**: `Predictor` and `TrainingHistory` - Database entities for data persistence  
- **Controllers**: RESTful API endpoints for client interaction
- **Storage**: Trained models saved as `.pkl` files in `saved_models/` directory

## Features

### Core Functionality
- **Two-Phase Prediction Model**:
  - Linear Regression for HVAC OFF state temperature prediction
  - Random Forest for HVAC ON state (energy consumption + temperature delta)
- **Location-Based Model Management**: Separate models for each lat/lon coordinate
- **Full Training Pipeline**: Complete end-to-end training with data preprocessing
- **Database Integration**: PostgreSQL storage with training history tracking
- **Optimization Algorithms**: Peak hours and normal conditions optimization

### Key Components
1. **HVACOptimizerService Class**: Main optimization engine (`services/hvac_optimizer_service.py`)
2. **Database Models**: Predictor and TrainingHistory tables with location support (`models/predictor.py`)
3. **FastAPI Controllers**: RESTful API endpoints for training, prediction, and optimization (`controllers/predict.py`)
4. **Evaluation Functions**: Comprehensive metrics for model assessment

## Installation

### Prerequisites
```bash
# Install required packages using conda
conda install -c conda-forge scikit-learn pandas numpy scipy matplotlib joblib

# Or install with specific versions (recommended)
conda install -c conda-forge scikit-learn=1.3.0 pandas=2.0.3 numpy=1.24.3 scipy=1.11.1 matplotlib=3.7.2 joblib=1.3.1
```

### Database Setup
1. Run the migration script to update your database:
```sql
-- Execute the migration file: api/db/migration_hvac_location.sql
-- This adds location columns to predictors table and creates training_history table
```

## Usage

### 1. Training a Location-Specific Model

```python
from services.hvac_optimizer_service import HVACOptimizerService

# Initialize optimizer service for a specific location
hvac_service = HVACOptimizerService(latitude=40.7128, longitude=-74.0060)

# Train the complete pipeline
results = hvac_service.train_full_pipeline(
    csv_path="path/to/hvac_dataset.csv",
    knowledge_id=1
)

print(f"Training completed. Model ID: {results['model_id']}")
```

### 2. Making Predictions

```python
# Predict energy consumption and temperature for an operation schedule
operation = [1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0]  # 1=ON, 0=OFF for each 5-min interval
outdoor_temps = [30.0, 29.8, 29.6, 29.4, 29.2, 29.0, 28.8, 28.6, 28.4, 28.2, 28.0, 27.8, 27.6]

total_consumption, temperatures = hvac_service.predict_one_hour(
    operation=operation,
    starting_temp=25.0,
    starting_time="07/08/2022 20:20",
    outdoor_temps=outdoor_temps,
    setpoint=23.0,
    duration=12
)

print(f"Total energy consumption: {total_consumption}")
print(f"Temperature predictions: {temperatures}")
```

### 3. Optimization

```python
# Normal conditions optimization
result = hvac_service.normal_conditions_optimizer(
    starting_temp=25.0,
    starting_time="07/08/2022 20:20",
    outdoor_temps=outdoor_temps,
    setpoint=23.0,
    duration=12
)

print(f"Recommended operation: {result['recommended_operation']}")
print(f"Energy savings: {result['savings_percentage']:.2f}%")

# Peak hours optimization (more aggressive)
peak_result = hvac_service.biased_random_search(
    starting_temp=25.0,
    starting_time="07/08/2022 20:20",
    outdoor_temps=outdoor_temps,
    setpoint=23.0,
    duration=12
)

print(f"Optimized operation: {peak_result['operation']}")
print(f"Total score: {peak_result['total_score']}")
```

## API Endpoints

### Training
- **POST** `/predict/hvac/train` - Train model for specific location
- **GET** `/predict/hvac/training-history/{lat}/{lon}` - Get training history

### Prediction & Optimization
- **POST** `/predict/hvac/predict` - Predict energy/temperature for operation schedule
- **POST** `/predict/hvac/optimize` - Optimize operation schedule
- **POST** `/predict/hvac/evaluate-schedule` - Evaluate specific schedule

### Model Management
- **GET** `/predict/hvac/models` - List all location-based models
- **POST** `/predict/hvac/evaluate` - Calculate evaluation metrics

## Database Schema

### Enhanced Predictors Table
```sql
CREATE TABLE predictors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    framework VARCHAR(255) NOT NULL,
    latitude FLOAT NULL,
    longitude FLOAT NULL,
    model_type VARCHAR(50) NULL,
    model_data JSON NULL,
    training_data_hash VARCHAR(32) NULL,
    scores JSON NULL,
    knowledge_id INTEGER REFERENCES knowledge(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Training History Table
```sql
CREATE TABLE training_history (
    id SERIAL PRIMARY KEY,
    predictor_id INTEGER REFERENCES predictors(id),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    training_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_completed_at TIMESTAMP NULL,
    training_status VARCHAR(20) NOT NULL,
    training_metrics JSON NULL,
    data_size INTEGER NULL,
    model_parameters JSON NULL,
    notes TEXT NULL
);
```

## Data Format

The training CSV should have the following columns:
```
timestamp, indoor_temp, hvac_operation, outdoor_temp, energy_consumption, setpoint_temp, outlet_temp, inlet_temp
```

Example:
```
07/08/2022 20:20, 25.2, 1, 30.1, 2.5, 23.0, 18.5, 26.0
07/08/2022 20:25, 24.8, 1, 30.0, 2.3, 23.0, 18.2, 25.8
```

## Location-Based Model Management

The system automatically manages models based on location:

1. **Model Storage**: Each location (lat/lon) has its own trained model
2. **Location Tolerance**: Configurable tolerance for finding nearby models (default: 0.01 degrees)
3. **Automatic Loading**: Models are automatically loaded when creating HVACOptimizer instances
4. **Version Control**: Training data hash tracking for model versioning

## Evaluation Metrics

The system provides comprehensive evaluation metrics:

- **R² Score**: Coefficient of determination
- **RMSE**: Root Mean Square Error
- **MAE**: Mean Absolute Error
- **MAPE**: Mean Absolute Percentage Error
- **Normalized RMSE**: RMSE normalized by data range

## Algorithm Details

### HVAC OFF Prediction
Uses linear regression on the equation:
```
Tin(t) - Tin(t-1) = a × (Tout(t-1) - Tin(t-1))
```

### HVAC ON Prediction
Random Forest predicts:
1. Energy consumption
2. Temperature delta (ΔT)

Final temperature: `Tin(t) = a × (Tout(t-1) - Tin(t-1)) + Tin(t-1) + ΔT`

### Optimization Scoring
```
Total Score = comfort_penalty_weight × comfort_penalty + switch_penalty_weight × switch_penalty + energy_consumption
```

Where:
- `comfort_penalty = Σ(predicted_temp - setpoint)²`
- `switch_penalty = number of HVAC on/off switches`

## Example Usage in Controller

```python
from services.hvac_optimizer_service import HVACOptimizerService

# Example controller usage
@app.post("/optimize-hvac")
async def optimize_hvac_for_location(
    latitude: float,
    longitude: float,
    starting_temp: float,
    outdoor_forecast: List[float],
    setpoint: float
):
    hvac_service = HVACOptimizerService(latitude, longitude)
    
    result = hvac_service.normal_conditions_optimizer(
        starting_temp=starting_temp,
        starting_time=datetime.now().strftime('%d/%m/%Y %H:%M'),
        outdoor_temps=outdoor_forecast,
        setpoint=setpoint
    )
    
    return {
        "optimized_schedule": result['recommended_operation'],
        "energy_savings": result['savings_percentage'],
        "comfort_deviation": result['avg_deviation_from_setpoint']
    }
```

## File Structure

```
api/
├── services/
│   ├── __init__.py
│   └── hvac_optimizer_service.py    # Main HVAC optimization service
├── models/
│   ├── predictor.py                 # Database models (Predictor, TrainingHistory)
│   └── ...
├── controllers/
│   ├── predict.py                   # API endpoints for HVAC operations
│   └── ...
├── saved_models/                    # Directory for trained .pkl files
│   └── .gitkeep
└── ...
```

## Notes

- Models are location-specific and automatically selected based on latitude/longitude
- Training history is tracked for audit and retraining decisions
- The system supports both real-time optimization and batch processing
- All evaluation functions are available for controller endpoints
- Background training tasks prevent API blocking during model training
