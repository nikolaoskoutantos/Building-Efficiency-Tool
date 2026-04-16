from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from utils.ws_protocol import AlertMessage, ErrorMessage, ProgressMessage, ResultMessage


TaskHandler = Callable[["TaskExecutionContext"], Awaitable[None]]
BuildingAccessGuard = Callable[[int], int]


class TaskNotRegisteredError(RuntimeError):
    pass


@dataclass(slots=True)
class TaskExecutionContext:
    task_id: str
    auth_payload: dict
    registered_user_id: int
    require_building_access: BuildingAccessGuard
    send_progress: Callable[[ProgressMessage], Awaitable[None]]
    send_alert: Callable[[AlertMessage], Awaitable[None]]
    send_result: Callable[[ResultMessage], Awaitable[None]]
    send_error: Callable[[ErrorMessage], Awaitable[None]]


async def counter_demo_task(ctx: TaskExecutionContext) -> None:
    await ctx.send_alert(
        AlertMessage(level="info", message="Counter demo started.")
    )

    for value in range(101):
        if value == 25:
            await ctx.send_alert(
                AlertMessage(level="info", message="25% complete. Processing is stable.")
            )
        elif value == 60:
            await ctx.send_alert(
                AlertMessage(level="warning", message="60% complete. Running post-processing stage.")
            )
        elif value == 90:
            await ctx.send_alert(
                AlertMessage(level="critical", message="Finalizing result payload.")
            )

        await ctx.send_progress(ProgressMessage(value=value))
        await asyncio.sleep(0.05)

    await ctx.send_result(
        ResultMessage(
            data={
                "task_id": ctx.task_id,
                "status": "completed",
                "value": 100,
                "user_id": ctx.auth_payload.get("user_id"),
            }
        )
    )


TASK_REGISTRY: dict[str, TaskHandler] = {
    "counter-demo": counter_demo_task,
}


def resolve_task_handler(task_id: str) -> TaskHandler:
    handler = TASK_REGISTRY.get(task_id)
    if handler is None:
        raise TaskNotRegisteredError(f"No websocket task registered for '{task_id}'")
    return handler
