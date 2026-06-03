"""
Unit tests for the chat endpoint.
Uses mock LLM — no real API calls.
"""

import pytest
from httpx import ASGITransport, AsyncClient

# Set env before importing app
import os
os.environ["APP_SECRET_KEY"] = "test-secret-key-32-characters-long-xx"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "development"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"

from app.main import app

DEMO_TENANT = "00000000-0000-0000-0000-000000000001"
HEADERS = {"X-Tenant-ID": DEMO_TENANT, "Content-Type": "application/json"}


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_basic(client):
    r = await client.post(
        "/api/v1/chat",
        json={
            "message": "Hola",
            "session_token": "test-session-abc123",
            "history": [],
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert "response" in body
    assert len(body["response"]) > 0
    assert body["provider"] == "mock"


@pytest.mark.asyncio
async def test_chat_requires_tenant_header(client):
    r = await client.post(
        "/api/v1/chat",
        json={"message": "Hola", "session_token": "test-abc", "history": []},
        # No X-Tenant-ID header
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_chat_empty_message(client):
    r = await client.post(
        "/api/v1/chat",
        json={"message": "   ", "session_token": "test-abc", "history": []},
        headers=HEADERS,
    )
    assert r.status_code in (422, 400)


@pytest.mark.asyncio
async def test_chat_message_too_long(client):
    r = await client.post(
        "/api/v1/chat",
        json={"message": "x" * 501, "session_token": "test-abc", "history": []},
        headers=HEADERS,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_security_headers(client):
    r = await client.get("/health")
    assert "content-security-policy" in r.headers
    assert "x-frame-options" in r.headers
    assert "x-content-type-options" in r.headers


@pytest.mark.asyncio
async def test_chat_with_history(client):
    r = await client.post(
        "/api/v1/chat",
        json={
            "message": "¿Cuánto tardan en entregar?",
            "session_token": "test-session-history",
            "history": [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "¡Hola! ¿En qué te puedo ayudar?"},
            ],
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["session_token"] == "test-session-history"
