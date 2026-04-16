from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field


class AuthMessage(BaseModel):
    type: Literal["auth"]
    token: str = Field(min_length=1)


class ProgressMessage(BaseModel):
    type: Literal["progress"] = "progress"
    value: int = Field(ge=0, le=100)


class AlertMessage(BaseModel):
    type: Literal["alert"] = "alert"
    level: Literal["info", "warning", "critical"]
    message: str = Field(min_length=1)


class ResultMessage(BaseModel):
    type: Literal["result"] = "result"
    data: dict[str, Any]


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str = Field(min_length=1)
    code: str = Field(min_length=1)


class PingMessage(BaseModel):
    type: Literal["ping"] = "ping"


class PongMessage(BaseModel):
    type: Literal["pong"] = "pong"


ClientMessage = AuthMessage | PingMessage | PongMessage
ServerMessage = ProgressMessage | AlertMessage | ResultMessage | ErrorMessage | PingMessage | PongMessage

ModelT = TypeVar("ModelT", bound=BaseModel)


def model_validate(model_cls: type[ModelT], payload: dict[str, Any]) -> ModelT:
    validate = getattr(model_cls, "model_validate", None)
    if callable(validate):
        return validate(payload)
    return model_cls.parse_obj(payload)


def model_dump(model: BaseModel) -> dict[str, Any]:
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump()
    return model.dict()


def parse_auth_message(payload: dict[str, Any]) -> AuthMessage:
    return model_validate(AuthMessage, payload)


def parse_runtime_client_message(payload: dict[str, Any]) -> PingMessage | PongMessage:
    message_type = payload.get("type")
    if message_type == "ping":
        return model_validate(PingMessage, payload)
    if message_type == "pong":
        return model_validate(PongMessage, payload)
    raise ValueError(f"Unsupported runtime message type: {message_type}")
