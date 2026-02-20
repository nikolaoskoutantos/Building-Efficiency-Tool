from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from db import SessionLocal
from models.predictor import Predictor, TrainingHistory
from services.hvac_optimizer_service import HVACOptimizerService
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field

router = APIRouter(prefix="/predict", tags=["Predictors"])

# Pydantic schemas
class PredictorBase(BaseModel):
    name: str
    framework: str
    scores: dict = Field(default_factory=dict)
    knowledge_id: int

class PredictorCreate(PredictorBase):
    pass

class PredictorRead(PredictorBase):
    id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    model_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    class Config:
        from_attributes = True

# HVAC-specific schemas
class HVACTrainingRequest(BaseModel):
    latitude: float
    longitude: float
    sensor_id: int
    knowledge_id: int = 1
    days_back: int = 30

class HVACPredictionRequest(BaseModel):
    latitude: float
    longitude: float
    operation: List[int]  # List of 0s and 1s for HVAC operation
    starting_temperature: float
    starting_time: str  # Format: '%d/%m/%Y %H:%M'
    outdoor_temperatures: List[float]  # Forecast temperatures
    setpoint: float
    duration: int = 12  # Number of 5-minute intervals

def clamp_duration(duration: int, min_val: int = 1, max_val: int = 288) -> int:
    """Clamp duration to a safe range (default: 1 to 288 for 5-min intervals in a day)."""
    if duration < min_val:
        return min_val
    if duration > max_val:
        return max_val
    return duration

class HVACOptimizationRequest(BaseModel):
    latitude: float
    longitude: float
    starting_temperature: float
    starting_time: str
    outdoor_temperatures: List[float]
    setpoint: float
    duration: int = 12
    optimization_type: str = "normal"  # "normal" or "peak"

class HVACEvaluationRequest(BaseModel):
    y_true: List[float]
    y_pred: List[float]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/",
    response_model=PredictorRead,
    responses={
        400: {"description": "Invalid input"},
        500: {"description": "Internal server error"},
    },
)
def create_predictor(predictor: PredictorCreate, db: Annotated[Session, Depends(get_db)]):
    db_predictor = Predictor(**predictor.dict())
    db.add(db_predictor)
    db.commit()
    db.refresh(db_predictor)
    return db_predictor

@router.get(
    "/",
    response_model=List[PredictorRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
def read_predictors(db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100):
    return db.query(Predictor).offset(skip).limit(limit).all()

@router.post("/predict_one")
def predict_one(input_data: dict):
    # This is a placeholder for actual prediction logic
    # You can later load a model and return a prediction based on input_data
    return {"prediction": "This is a mock prediction", "input": input_data}

# HVAC-specific endpoints
@router.post(
    "/hvac/train",
    responses={
        500: {"description": "Training failed"},
    },
)
async def train_hvac_model(request: HVACTrainingRequest, background_tasks: BackgroundTasks):
    """Train HVAC optimization model for a specific location using database sensor data."""
    try:
        hvac_optimizer = HVACOptimizerService(request.latitude, request.longitude)
        
        # Run training in background
        def run_training():
            return hvac_optimizer.train_full_pipeline(
                sensor_id=request.sensor_id,
                knowledge_id=request.knowledge_id,
                days_back=request.days_back
            )
        
        background_tasks.add_task(run_training)
        
        return {
            "message": f"HVAC training started for location ({request.latitude}, {request.longitude}) using sensor {request.sensor_id}",
            "status": "training_started",
            "sensor_id": request.sensor_id,
            "days_back": request.days_back
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@router.post(
    "/hvac/predict",
    responses={
        500: {"description": "Prediction failed"},
    },
)
async def predict_hvac(request: HVACPredictionRequest):
    """Predict temperature and energy consumption for HVAC operation schedule."""
    try:
        hvac_optimizer = HVACOptimizerService(request.latitude, request.longitude)
        safe_duration = clamp_duration(request.duration)
        total_consumption, temperatures = hvac_optimizer.predict_one_hour(
            operation=request.operation,
            starting_temp=request.starting_temperature,
            starting_time=request.starting_time,
            outdoor_temps=request.outdoor_temperatures,
            setpoint=request.setpoint,
            duration=safe_duration
        )
        
        return {
            "total_energy_consumption": total_consumption,
            "temperature_predictions": temperatures,
            "operation_schedule": request.operation,
            "location": {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.post(
    "/hvac/optimize",
    responses={
        500: {"description": "Optimization failed"},
    },
)
async def optimize_hvac_schedule(request: HVACOptimizationRequest):
    """Optimize HVAC operation schedule for energy efficiency."""
    try:
        hvac_optimizer = HVACOptimizerService(request.latitude, request.longitude)
        safe_duration = clamp_duration(request.duration)
        if request.optimization_type == "peak":
            result = hvac_optimizer.biased_random_search(
                starting_temp=request.starting_temperature,
                starting_time=request.starting_time,
                outdoor_temps=request.outdoor_temperatures,
                setpoint=request.setpoint,
                duration=safe_duration
            )
        else:  # normal conditions
            result = hvac_optimizer.normal_conditions_optimizer(
                starting_temp=request.starting_temperature,
                starting_time=request.starting_time,
                outdoor_temps=request.outdoor_temperatures,
                setpoint=request.setpoint,
                duration=safe_duration
            )
        
        return {
            "optimization_type": request.optimization_type,
            "result": result,
            "location": {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@router.post(
    "/hvac/evaluate",
    responses={
        500: {"description": "Evaluation failed"},
    },
)
async def evaluate_metrics(request: HVACEvaluationRequest):
    """Calculate evaluation metrics for HVAC predictions."""
    try:
        # Create a temporary optimizer instance for metric calculation
        hvac_optimizer = HVACOptimizerService(0.0, 0.0)  # Location doesn't matter for metrics
        
        metrics = hvac_optimizer.get_evaluation_metrics(request.y_true, request.y_pred)
        
        return {
            "metrics": metrics,
            "data_points": len(request.y_true)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.get(
    "/hvac/models",
    responses={
        500: {"description": "Failed to retrieve models"},
    },
)
async def get_all_hvac_models():
    """Get all HVAC models across all locations."""
    try:
        models = HVACOptimizerService.get_all_location_models()
        return {
            "models": models,
            "total_models": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve models: {str(e)}")

@router.get(
    "/hvac/training-history/{latitude}/{longitude}",
    responses={
        500: {"description": "Failed to retrieve training history"},
    },
)
async def get_hvac_training_history(latitude: float, longitude: float):
    """Get training history for a specific location."""
    try:
        hvac_optimizer = HVACOptimizerService(latitude, longitude)
        history = hvac_optimizer.get_training_history()
        
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "training_history": history,
            "total_trainings": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve training history: {str(e)}")

@router.post(
    "/hvac/evaluate-schedule",
    responses={
        500: {"description": "Schedule evaluation failed"},
    },
)
async def evaluate_hvac_schedule(request: HVACPredictionRequest):
    """Evaluate a specific HVAC operation schedule with detailed metrics."""
    try:
        hvac_optimizer = HVACOptimizerService(request.latitude, request.longitude)
        safe_duration = clamp_duration(request.duration)
        result = hvac_optimizer.evaluate_schedule(
            operation=request.operation,
            starting_temp=request.starting_temperature,
            starting_time=request.starting_time,
            outdoor_temps=request.outdoor_temperatures,
            setpoint=request.setpoint,
            duration=safe_duration
        )
        
        return {
            "evaluation": result,
            "location": {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule evaluation failed: {str(e)}")
