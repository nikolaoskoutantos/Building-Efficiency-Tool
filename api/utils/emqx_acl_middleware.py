import os
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv()

EMQX_ACL_SECRET = os.environ["emqx_acl_secret"]

class EMQXACLHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only check for /device/acl endpoint
        if request.url.path == "/device/acl":
            token = request.headers.get("X-EMQX-Token")
            if token != EMQX_ACL_SECRET:
                return JSONResponse({"result": "deny"})
        response = await call_next(request)
        return response
