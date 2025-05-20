import logging
from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SafeFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        request.state.logger = logging.LoggerAdapter(logging.getLogger("app"), {"request_id": request_id})

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Set up base logger
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = SafeFormatter(
    '[%(asctime)s] [%(levelname)s] [%(request_id)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
