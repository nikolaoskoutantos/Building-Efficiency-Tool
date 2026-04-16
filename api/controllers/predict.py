from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from db import SessionLocal
from models.predictor import Predictor, TrainingHistory
from services.hvac_optimizer_service import HVACOptimizerService
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from time import perf_counter
import os

from utils.auth_dependencies import get_current_user_role, get_current_websocket_role, resolve_registered_user_id
router = APIRouter(
    prefix="/predict",
    tags=["Predictors"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)
ws_router = APIRouter(
    prefix="/predict",
    tags=["Predictors"],
)

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
    building_id: int
    sensor_id: int
    knowledge_id: int = 1
    days_back: int = 30

class HVACPredictionRequest(BaseModel):
    building_id: int
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
    building_id: int
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


def _require_building_access(user: dict, building_id: int) -> None:
    from utils.policies import has_permission

    db = SessionLocal()
    try:
        user_id = resolve_registered_user_id(user, db)
        if not has_permission(user_id, "building", building_id, db):
            raise HTTPException(status_code=403, detail="You are not authorized for this building.")
    finally:
        db.close()


def _get_allowed_socket_origins() -> set[str]:
    origins = {
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    }
    custom_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if custom_origins:
        origins.update(origin.strip() for origin in custom_origins.split(",") if origin.strip())
    local_ip = os.getenv("LOCAL_NETWORK_IP")
    local_ports = os.getenv("LOCAL_NETWORK_PORTS", "3000,3001,5173")
    if local_ip:
        for port in [port.strip() for port in local_ports.split(",") if port.strip()]:
            origins.add(f"http://{local_ip}:{port}")
    return origins


def _is_allowed_socket_origin(origin: str | None) -> bool:
    if not origin:
        return True
    return origin in _get_allowed_socket_origins()

@router.post(
    "/",
    response_model=PredictorRead,
    responses={
        400: {"description": "Invalid input"},
        500: {"description": "Internal server error"},
    },
)
def create_predictor(
    predictor: PredictorCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
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
def predict_one(
    input_data: dict,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    # This is a placeholder for actual prediction logic
    # You can later load a model and return a prediction based on input_data
    return {"prediction": "This is a mock prediction", "input": input_data}

# HVAC-specific endpoints

@router.post(
    "/hvac/predict",
    responses={
        403: {"description": "Forbidden: User not authorized to predict HVAC."},
        500: {"description": "Prediction failed"},
    },
)
async def predict_hvac(request: HVACPredictionRequest, user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]):
    """Predict temperature and energy consumption for HVAC operation schedule."""
    _require_building_access(user, request.building_id)
    try:
        hvac_optimizer = HVACOptimizerService(request.building_id)
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
            "building_id": request.building_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.post(
    "/hvac/optimize",
    responses={
        403: {"description": "Forbidden: User not authorized to optimize HVAC schedule."},
        500: {"description": "Optimization failed"},
    },
)
async def optimize_hvac_schedule(request: HVACOptimizationRequest, user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]):
    """Optimize HVAC operation schedule for energy efficiency."""
    _require_building_access(user, request.building_id)
    try:
        hvac_optimizer = HVACOptimizerService(request.building_id)
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
            "building_id": request.building_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@ws_router.websocket("/hvac/optimize/ws")
async def optimize_hvac_schedule_ws(
    websocket: WebSocket,
):
    """Run HVAC optimization over WebSocket and stream progress/result updates."""
    await websocket.accept()

    try:
        if not _is_allowed_socket_origin(websocket.headers.get("origin")):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
            return

        try:
            user = get_current_websocket_role(["BUILDING_MANAGER", "ADMIN"])(websocket)
        except HTTPException as exc:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=str(exc.detail),
            )
            return

        payload = await websocket.receive_json()
        request = HVACOptimizationRequest.model_validate(payload)
        _require_building_access(user, request.building_id)

        safe_duration = clamp_duration(request.duration)
        started_at = perf_counter()

        await websocket.send_json(
            {
                "type": "optimization.status",
                "status": "accepted",
                "building_id": request.building_id,
                "optimization_type": request.optimization_type,
                "duration": safe_duration,
            }
        )

        await websocket.send_json(
            {
                "type": "optimization.status",
                "status": "initializing_optimizer",
            }
        )
        optimizer_init_started = perf_counter()
        hvac_optimizer = await run_in_threadpool(HVACOptimizerService, request.building_id)
        optimizer_init_seconds = round(perf_counter() - optimizer_init_started, 3)

        await websocket.send_json(
            {
                "type": "optimization.status",
                "status": "optimizer_ready",
                "timing": {
                    "optimizer_init_seconds": optimizer_init_seconds,
                },
            }
        )

        await websocket.send_json(
            {
                "type": "optimization.status",
                "status": "running_optimization",
            }
        )

        optimization_started = perf_counter()
        result = await run_in_threadpool(
            hvac_optimizer.get_optimization_recommendation,
            request.starting_temperature,
            request.starting_time,
            request.outdoor_temperatures,
            request.setpoint,
            request.optimization_type == "peak",
            safe_duration,
            "dict",
        )
        optimization_seconds = round(perf_counter() - optimization_started, 3)
        total_seconds = round(perf_counter() - started_at, 3)

        await websocket.send_json(
            {
                "type": "optimization.completed",
                "status": "completed",
                "building_id": request.building_id,
                "optimization_type": request.optimization_type,
                "timing": {
                    "optimizer_init_seconds": optimizer_init_seconds,
                    "optimization_seconds": optimization_seconds,
                    "total_seconds": total_seconds,
                },
                "result": result,
            }
        )
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json(
            {
                "type": "optimization.failed",
                "status": "failed",
                "detail": str(exc),
            }
        )
    finally:
        await websocket.close()

@router.post(
    "/hvac/evaluate",
    responses={
        403: {"description": "Forbidden: User not authorized to evaluate HVAC metrics."},
        500: {"description": "Evaluation failed"},
    },
)
async def evaluate_metrics(request: HVACEvaluationRequest, user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]):
    """Calculate evaluation metrics for HVAC predictions."""
    from utils.policies import has_permission
    # For evaluation, permission check can be skipped or tied to a building if needed
    try:
        hvac_optimizer = HVACOptimizerService(0)  # Dummy building_id for metrics
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
        403: {"description": "Forbidden: User not authorized to retrieve HVAC models."},
        500: {"description": "Failed to retrieve models"},
    },
)
async def get_all_hvac_models(user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]):
    """Get all HVAC models across all locations."""
    from utils.policies import has_permission
    # Optionally filter models by user permission
    try:
        models = HVACOptimizerService.get_all_location_models()
        return {
            "models": models,
            "total_models": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve models: {str(e)}")

@router.get(
    "/hvac/training-history/{building_id}",
    responses={
        403: {"description": "Forbidden: User not authorized to retrieve HVAC training history."},
        500: {"description": "Failed to retrieve training history"},
    },
)
async def get_hvac_training_history(building_id: int, user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]):
    """Get training history for a specific building."""
    _require_building_access(user, building_id)
    try:
        hvac_optimizer = HVACOptimizerService(building_id)
        history = hvac_optimizer.get_training_history()
        return {
            "building_id": building_id,
            "training_history": history,
            "total_trainings": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve training history: {str(e)}")

@router.post(
    "/hvac/evaluate-schedule",
    responses={
        403: {"description": "Forbidden: User not authorized to evaluate HVAC schedule."},
        500: {"description": "Schedule evaluation failed"},
    },
)
async def evaluate_hvac_schedule(request: HVACPredictionRequest, user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]):
    """Evaluate a specific HVAC operation schedule with detailed metrics."""
    _require_building_access(user, request.building_id)
    try:
        hvac_optimizer = HVACOptimizerService(request.building_id)
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
            "building_id": request.building_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule evaluation failed: {str(e)}")
