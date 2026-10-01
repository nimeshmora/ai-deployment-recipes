"""Small, single-process AI API. See README for the deployment boundary."""

import asyncio
import hmac
import json
import logging
import math
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

LOG = logging.getLogger("uvicorn.error")
MAX_BODY = 16_384
MAX_UPSTREAM = 262_144


def secret(name: str) -> str:
    path = os.getenv(f"{name}_FILE")
    value = os.getenv(name)
    if path and value:
        raise ValueError(f"Set only one of {name} or {name}_FILE")
    return Path(path).read_text().strip() if path else (value or "").strip()


@dataclass(frozen=True)
class Settings:
    app_token: str = field(repr=False)
    mode: str = "mock"
    base_url: str = ""
    model: str = ""
    api_key: str = field(default="", repr=False)
    max_inflight: int = 4
    requests_per_minute: int = 30
    deadline_seconds: float = 30
    max_output_tokens: int = 256
    allow_http: bool = False

    def __post_init__(self):
        if len(self.app_token) < 32 or not self.app_token.isascii():
            raise ValueError("APP_TOKEN must contain at least 32 ASCII characters")
        if self.mode not in {"mock", "live"}:
            raise ValueError("MODEL_MODE must be mock or live")
        if not 1 <= self.max_inflight <= 32:
            raise ValueError("MAX_INFLIGHT must be between 1 and 32")
        if not 1 <= self.requests_per_minute <= 10_000:
            raise ValueError("REQUESTS_PER_MINUTE must be between 1 and 10000")
        if not math.isfinite(self.deadline_seconds) or not 0 < self.deadline_seconds <= 30:
            raise ValueError("UPSTREAM_DEADLINE_SECONDS must be > 0 and <= 30")
        if not 1 <= self.max_output_tokens <= 4096:
            raise ValueError("MAX_OUTPUT_TOKENS must be between 1 and 4096")
        if self.mode == "live":
            url = urlsplit(self.base_url)
            if (
                not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.scheme not in ({"https", "http"} if self.allow_http else {"https"})
                or not self.model.strip()
            ):
                raise ValueError(
                    "Live mode needs MODEL_NAME and an HTTPS MODEL_BASE_URL without credentials/query/fragment"
                )

    @classmethod
    def from_env(cls):
        return cls(
            app_token=secret("APP_TOKEN"),
            mode=os.getenv("MODEL_MODE", "mock"),
            base_url=os.getenv("MODEL_BASE_URL", ""),
            model=os.getenv("MODEL_NAME", ""),
            api_key=secret("MODEL_API_KEY"),
            max_inflight=int(os.getenv("MAX_INFLIGHT", "4")),
            requests_per_minute=int(os.getenv("REQUESTS_PER_MINUTE", "30")),
            deadline_seconds=float(os.getenv("UPSTREAM_DEADLINE_SECONDS", "30")),
            max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "256")),
            allow_http=os.getenv("ALLOW_HTTP_UPSTREAM", "false").lower() == "true",
        )


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: StrictStr = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value


class ChatOutput(BaseModel):
    answer: str
    mode: str
    model: str
    finish_reason: str | None


class Boundary:
    """Bound incoming bodies before JSON parsing; attach safe request metadata."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        status = 500

        async def send_with_headers(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                    ),
                ]
            await send(message)

        async def reject(code, detail):
            await JSONResponse({"detail": detail}, status_code=code)(
                scope, receive, send_with_headers
            )

        try:
            chunks = []
            size = 0
            try:
                async with asyncio.timeout(5):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            status = 499
                            return
                        chunk = message.get("body", b"")
                        size += len(chunk)
                        if size > MAX_BODY:
                            return await reject(413, "Request body too large")
                        chunks.append(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                return await reject(408, "Request body timeout")
            replayed = False

            async def replay():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
                return await receive()

            await self.app(scope, replay, send_with_headers)
        finally:
            # Intentionally exclude paths, query strings, headers, prompts and outputs.
            LOG.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "status": status,
                        "duration_ms": round((time.monotonic() - started) * 1000, 1),
                    }
                )
            )


async def completion(client: httpx.AsyncClient, settings: Settings, message: str):
    headers = {"Accept-Encoding": "identity"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    payload = {
        "model": settings.model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": settings.max_output_tokens,
        "stream": False,
    }
    try:
        # HTTPX phase timeouts do not enforce an overall deadline; use both.
        async with asyncio.timeout(settings.deadline_seconds):
            async with client.stream(
                "POST",
                settings.base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code == 429 or response.status_code >= 500:
                    raise HTTPException(
                        503, "Model service temporarily unavailable", headers={"Retry-After": "10"}
                    )
                if response.status_code != 200:
                    raise HTTPException(502, "Model service rejected the request")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise HTTPException(502, "Unsupported model response encoding")
                data = bytearray()
                async for chunk in response.aiter_raw():
                    data.extend(chunk)
                    if len(data) > MAX_UPSTREAM:
                        raise HTTPException(502, "Model response exceeds size limit")
                result = json.loads(data)
                choice = result["choices"][0]
                answer = choice["message"]["content"]
                finish_reason = choice.get("finish_reason")
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("No text answer")
                if finish_reason is not None and not isinstance(finish_reason, str):
                    raise ValueError("Invalid finish reason")
                return answer, finish_reason
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(504, "Model request timed out") from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, "Could not reach the model service") from exc
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(502, "Invalid model response") from exc


def create_app(settings: Settings | None = None, transport=None):
    @asynccontextmanager
    async def lifespan(app):
        config = settings or Settings.from_env()
        app.state.settings = config
        app.state.inflight = 0
        app.state.window = time.monotonic()
        app.state.requests = 0
        app.state.ready = True
        async with httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(20, connect=5, pool=1),
            limits=httpx.Limits(
                max_connections=config.max_inflight, max_keepalive_connections=config.max_inflight
            ),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            app.state.client = client
            yield
            app.state.ready = False

    app = FastAPI(
        title="AI Deployment Recipes",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(Boundary)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default validation response can echo input. Return a fixed message.
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Expected only message: a non-blank string of at most 4000 characters"
            },
        )

    @app.get("/health/live")
    async def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready():
        if not getattr(app.state, "ready", False):
            raise HTTPException(503, "Not ready")
        return {"status": "ready", "mode": app.state.settings.mode}

    @app.get("/")
    async def index():
        # This recipe is an API, not a web app. No UI is served.
        return {
            "service": "ai-deployment-recipes/01-ai-app",
            "mode": app.state.settings.mode,
            "endpoints": {
                "chat": 'POST /api/chat  (header "Authorization: Bearer <token>", body {"message": "..."})',
                "health": ["/health/live", "/health/ready"],
            },
            "check_safeguards": "python3 tools/readiness-check/readiness_check.py <url> --token <token>",
        }

    @app.post("/api/chat", response_model=ChatOutput)
    async def chat(request: Request):
        config = app.state.settings
        supplied = request.headers.get("authorization", "").encode()
        expected = f"Bearer {config.app_token}".encode()
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                401, "Valid bearer token required", headers={"WWW-Authenticate": "Bearer"}
            )
        if (
            request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            raise HTTPException(415, "Use application/json")
        try:
            data = ChatInput.model_validate_json(await request.body())
        except ValueError as exc:
            raise HTTPException(
                422, "Expected only message: a non-blank string of at most 4000 characters"
            ) from exc
        now = time.monotonic()
        if now - app.state.window >= 60:
            app.state.window = now
            app.state.requests = 0
        if app.state.requests >= config.requests_per_minute:
            raise HTTPException(
                429,
                "Local request limit reached",
                headers={"Retry-After": str(max(1, math.ceil(60 - (now - app.state.window))))},
            )
        if app.state.inflight >= config.max_inflight:
            raise HTTPException(503, "Service busy", headers={"Retry-After": "1"})
        # No await between checking and incrementing: single event loop, one worker.
        app.state.requests += 1
        app.state.inflight += 1
        try:
            if config.mode == "mock":
                return ChatOutput(
                    answer="[MOCK — no model called] Deployment check passed. Your authenticated request reached the application.",
                    mode="mock",
                    model="mock",
                    finish_reason="stop",
                )
            answer, reason = await completion(app.state.client, config, data.message)
            return ChatOutput(answer=answer, mode="live", model=config.model, finish_reason=reason)
        finally:
            app.state.inflight -= 1

    return app


app = create_app()
