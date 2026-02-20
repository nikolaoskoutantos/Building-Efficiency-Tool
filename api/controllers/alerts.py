# app/routers/alerts.py

ALERT_NOT_FOUND = "Alert not found"

from fastapi import APIRouter, HTTPException, Depends

try:
    from typing import Annotated, List
except ImportError:
    from typing_extensions import Annotated
    from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import db
from ..models import alerts as alerts_model
from ..schemas import alerts as alerts_schema

router = APIRouter(prefix="/alerts", tags=["alerts"])


# Dependency to get DB session
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@router.post(
    "/",
    response_model=alerts_schema.Alert,
    responses={404: {"description": "Alert not found"}, 422: {"description": "Validation Error"}},
)
def create_alert(
    alert: alerts_schema.AlertCreate,
    db_session: Annotated[Session, Depends(get_db)],
):
    db_alert = alerts_model.Alert(**alert.dict())
    db_session.add(db_alert)
    db_session.commit()
    db_session.refresh(db_alert)
    return db_alert


@router.get(
    "/",
    response_model=List[alerts_schema.Alert],
    responses={422: {"description": "Validation Error"}},
)
def read_alerts(
    skip: int = 0,
    limit: int = 100,
    db_session: Annotated[Session, Depends(get_db)] = None,
):
    # SQLAlchemy 2.0-friendly approach (works in 1.4+ too)
    stmt = select(alerts_model.Alert).offset(skip).limit(limit)
    return db_session.execute(stmt).scalars().all()


@router.get(
    "/{alert_id}",
    response_model=alerts_schema.Alert,
    responses={404: {"description": "Alert not found"}, 422: {"description": "Validation Error"}},
)
def read_alert(
    alert_id: int,
    db_session: Annotated[Session, Depends(get_db)],
):
    stmt = select(alerts_model.Alert).where(alerts_model.Alert.id == alert_id)
    alert = db_session.execute(stmt).scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail=ALERT_NOT_FOUND)
    return alert


@router.put(
    "/{alert_id}",
    response_model=alerts_schema.Alert,
    responses={404: {"description": "Alert not found"}, 422: {"description": "Validation Error"}},
)
def update_alert(
    alert_id: int,
    alert: alerts_schema.AlertUpdate,
    db_session: Annotated[Session, Depends(get_db)],
):
    stmt = select(alerts_model.Alert).where(alerts_model.Alert.id == alert_id)
    db_alert = db_session.execute(stmt).scalars().first()

    if not db_alert:
        raise HTTPException(status_code=404, detail=ALERT_NOT_FOUND)

    for key, value in alert.dict(exclude_unset=True).items():
        setattr(db_alert, key, value)

    db_session.commit()
    db_session.refresh(db_alert)
    return db_alert


@router.delete(
    "/{alert_id}",
    responses={
        200: {"description": "Alert deleted"},
        404: {"description": "Alert not found"},
        422: {"description": "Validation Error"},
    },
)
def delete_alert(
    alert_id: int,
    db_session: Annotated[Session, Depends(get_db)],
):
    stmt = select(alerts_model.Alert).where(alerts_model.Alert.id == alert_id)
    db_alert = db_session.execute(stmt).scalars().first()

    if not db_alert:
        raise HTTPException(status_code=404, detail=ALERT_NOT_FOUND)

    db_session.delete(db_alert)
    db_session.commit()
    return {"ok": True}