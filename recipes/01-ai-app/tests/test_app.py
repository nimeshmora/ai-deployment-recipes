import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import pytest

from app.main import MAX_UPSTREAM, Boundary, Settings, create_app

TOKEN = "test-token-" + "a" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class BytesStream(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        yield self.data


def reply(payload, status=200, headers=None):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return httpx.Response(status, stream=BytesStream(raw), headers=headers)


def good():
    return reply({"choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}]})


@asynccontextmanager
async def client_for(handler=None, **overrides):
    values = {"app_token": TOKEN}
    if handler:
        values.update(mode="live", base_url="https://model.example/v1", model="test-model")
    values.update(overrides)
    app = create_app(Settings(**values), httpx.MockTransport(handler) if handler else None)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            yield client, app


async def test_mock_and_health():
    async with client_for() as (client, app):
        for path in ("/health/live", "/health/ready", "/", "/static/app.js"):
            assert (await client.get(path)).status_code == 200
        result = await client.post("/api/chat", headers=AUTH, json={"message": "Hello"})
        assert result.status_code == 200
        assert result.json()["mode"] == "mock"
        assert "MOCK" in result.json()["answer"]
        assert len(result.headers["x-request-id"]) == 32
        assert "frame-ancestors 'none'" in result.headers["content-security-policy"]
        assert result.headers["cache-control"] == "no-store"
        assert app.state.inflight == 0


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic token"}]
)
async def test_auth(headers):
    async with client_for() as (client, _):
        result = await client.post("/api/chat", headers=headers, json={"message": "Hello"})
        assert result.status_code == 401
        assert result.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "  "},
        {"message": 4},
        {"message": "a" * 4001},
        {"message": "hi", "model": "injected"},
        {},
    ],
)
async def test_validation(payload):
    async with client_for() as (client, _):
        result = await client.post("/api/chat", headers=AUTH, json=payload)
        assert result.status_code == 422
        assert "injected" not in result.text


async def test_invalid_json_and_content_type():
    async with client_for() as (client, _):
        assert (await client.post("/api/chat", headers=AUTH, content=b"{}")).status_code == 415
        result = await client.post(
            "/api/chat", headers={**AUTH, "Content-Type": "application/json"}, content=b"{secret"
        )
        assert result.status_code == 422
        assert "secret" not in result.text


async def test_body_limit_with_streamed_input():
    async def chunks():
        yield b"a" * 10_000
        yield b"b" * 10_000

    async with client_for() as (client, _):
        result = await client.post("/api/chat", headers=AUTH, content=chunks())
        assert result.status_code == 413


async def test_fixed_window_and_recovery():
    async with client_for(requests_per_minute=1) as (client, app):
        first = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        second = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        assert first.status_code == 200
        assert second.status_code == 429
        assert 1 <= int(second.headers["retry-after"]) <= 60
        app.state.window -= 61
        assert (
            await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        ).status_code == 200


async def test_upstream_contract():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url == "https://model.example/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer provider-secret"
        assert json.loads(request.content) == {
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 256,
            "stream": False,
        }
        return good()

    async with client_for(handler, api_key="provider-secret") as (client, _):
        result = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        assert result.status_code == 200
        assert result.json()["answer"] == "Hello"
        assert len(calls) == 1


@pytest.mark.parametrize(
    "upstream,expected", [(429, 503), (500, 503), (503, 503), (401, 502), (400, 502), (302, 502)]
)
async def test_provider_errors_sanitized_no_retry(upstream, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return reply({"secret": "do-not-expose"}, upstream, {"Location": "https://other.example"})

    async with client_for(handler) as (client, app):
        result = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        assert result.status_code == expected
        assert "do-not-expose" not in result.text
        assert len(calls) == 1
        assert app.state.inflight == 0


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        {},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "text"}, "finish_reason": 2}]},
    ],
)
async def test_malformed_upstream(payload):
    async with client_for(lambda r: reply(payload)) as (client, _):
        assert (
            await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        ).status_code == 502


async def test_response_size_cap():
    async with client_for(lambda r: reply(b"x" * (MAX_UPSTREAM + 1))) as (client, _):
        assert (
            await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        ).status_code == 502


async def test_reject_encoded_response():
    async with client_for(lambda r: reply(b"anything", headers={"Content-Encoding": "gzip"})) as (
        client,
        _,
    ):
        assert (
            await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        ).status_code == 502


async def test_wall_clock_deadline_releases_slot():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(1)
        return good()

    async with client_for(handler, deadline_seconds=0.03, max_inflight=1) as (client, app):
        result = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        assert result.status_code == 504
        assert app.state.inflight == 0
        assert (
            await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        ).status_code == 200


@pytest.mark.parametrize("kind,status", [(httpx.ConnectError, 502), (httpx.ReadTimeout, 504)])
async def test_transport_failure(kind, status):
    def handler(request):
        raise kind("secret upstream details", request=request)

    async with client_for(handler) as (client, _):
        result = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        assert result.status_code == status
        assert "secret upstream details" not in result.text


async def test_concurrent_overload_and_health():
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(request):
        entered.set()
        await release.wait()
        return good()

    async with client_for(handler, max_inflight=1) as (client, app):
        pending = asyncio.create_task(
            client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
        )
        await asyncio.wait_for(entered.wait(), 1)
        try:
            busy = await client.post("/api/chat", headers=AUTH, json={"message": "Hi"})
            assert busy.status_code == 503
            assert busy.headers["retry-after"] == "1"
            assert (await client.get("/health/live")).status_code == 200
        finally:
            release.set()
        assert (await pending).status_code == 200
        assert app.state.inflight == 0


async def test_cancellation_releases_slot():
    entered = asyncio.Event()

    async def handler(request):
        entered.set()
        await asyncio.sleep(10)
        return good()

    async with client_for(handler) as (client, app):
        task = asyncio.create_task(client.post("/api/chat", headers=AUTH, json={"message": "Hi"}))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert app.state.inflight == 0


async def test_logs_do_not_include_inputs(caplog):
    async with client_for() as (client, _):
        with caplog.at_level("INFO", logger="uvicorn.error"):
            await client.post(
                "/api/chat?secret=query-secret", headers=AUTH, json={"message": "private-prompt"}
            )
        assert "http_request" in caplog.text
        for secret in ("query-secret", "private-prompt", TOKEN):
            assert secret not in caplog.text


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_token": "short"},
        {"mode": "oops"},
        {"max_inflight": 0},
        {"deadline_seconds": 31},
        {"deadline_seconds": float("nan")},
        {"max_output_tokens": 0},
        {"mode": "live", "base_url": "http://model.example/v1", "model": "m"},
        {"mode": "live", "base_url": "https://user:pass@model.example/v1", "model": "m"},
    ],
)
def test_config_fails_closed(overrides):
    with pytest.raises(ValueError):
        Settings(**({"app_token": TOKEN} | overrides))


async def test_boundary_body_timeout(monkeypatch):
    real_timeout = asyncio.timeout
    monkeypatch.setattr("app.main.asyncio.timeout", lambda seconds: real_timeout(0.01))

    async def app(scope, receive, send):
        pytest.fail("Body should not reach application")

    async def receive():
        await asyncio.sleep(1)

    sent = []

    async def send(message):
        sent.append(message)

    await Boundary(app)({"type": "http"}, receive, send)
    assert sent[0]["status"] == 408
