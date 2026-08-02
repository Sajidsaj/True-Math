import pytest
import asyncio
import json
from src.ui_bridge.ipc_handler import IPCBridgeServer, _is_loopback_host, _RateLimiter, _RATE_LIMITED_ACTIONS


class DummyWriter:
    def __init__(self):
        self.buffer = bytearray()

    def write(self, data):
        self.buffer.extend(data)

    async def drain(self):
        return None

@pytest.mark.asyncio
async def test_ipc_callback_binding():
    """Verify that backend logic commands map smoothly."""
    server = IPCBridgeServer()
    
    # Mathematical mock function
    def mock_pause(data):
        return {"status": "success", "internal_id": data.get("id")}
        
    server.register_action("PAUSE_MATH", mock_pause)
    assert "PAUSE_MATH" in server._callbacks
    
    # Internal execution check
    result = server._callbacks["PAUSE_MATH"]({"id": 999})
    assert result["status"] == "success"
    assert result["internal_id"] == 999

def test_slots_memory_preservation():
    """Verify that slots prevent arbitrary internal bloat locally."""
    server = IPCBridgeServer()
    
    with pytest.raises(AttributeError):
        # We structurally block any unknown variables to reserve RAM exclusively for math
        server.arbitrary_memory_field = 123


def test_loopback_host_validator():
    assert _is_loopback_host("127.0.0.1") is True
    assert _is_loopback_host("localhost:9999") is True
    assert _is_loopback_host("0.0.0.0") is False


@pytest.mark.asyncio
async def test_ipc_handshake_rejects_non_loopback_origin():
    request = (
        b"GET /ws HTTP/1.1\r\n"
        b"Host: 127.0.0.1:9999\r\n"
        b"Origin: http://evil.example\r\n"
        b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        b"\r\n"
    )
    reader = asyncio.StreamReader()
    reader.feed_data(request)
    reader.feed_eof()
    writer = DummyWriter()

    server = IPCBridgeServer()
    accepted = await server.perform_handshake(reader, writer)

    assert accepted is False
    assert writer.buffer == b""


@pytest.mark.asyncio
async def test_ipc_handshake_accepts_loopback_request():
    request = (
        b"GET /ws HTTP/1.1\r\n"
        b"Host: 127.0.0.1:9999\r\n"
        b"Origin: http://127.0.0.1:8080\r\n"
        b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        b"\r\n"
    )
    reader = asyncio.StreamReader()
    reader.feed_data(request)
    reader.feed_eof()
    writer = DummyWriter()

    server = IPCBridgeServer()
    accepted = await server.perform_handshake(reader, writer)

    assert accepted is True
    assert b"101 Switching Protocols" in writer.buffer


def test_rate_limiter_allows_calls_under_the_limit():
    limiter = _RateLimiter()
    limit = _RATE_LIMITED_ACTIONS["ask_question"]
    for _ in range(limit):
        assert limiter.check("session_1", "ask_question") is True


def test_rate_limiter_blocks_calls_over_the_limit():
    limiter = _RateLimiter()
    limit = _RATE_LIMITED_ACTIONS["ask_question"]
    for _ in range(limit):
        limiter.check("session_1", "ask_question")
    # One more call beyond the limit must be rejected
    assert limiter.check("session_1", "ask_question") is False


def test_rate_limiter_is_per_session_not_global():
    limiter = _RateLimiter()
    limit = _RATE_LIMITED_ACTIONS["ask_question"]
    for _ in range(limit):
        limiter.check("session_1", "ask_question")
    # A DIFFERENT session must not be affected by session_1 hitting its limit
    assert limiter.check("session_2", "ask_question") is True


def test_rate_limiter_is_per_action_not_shared_across_actions():
    limiter = _RateLimiter()
    limit = _RATE_LIMITED_ACTIONS["ask_question"]
    for _ in range(limit):
        limiter.check("session_1", "ask_question")
    # A different action for the SAME session should have its own budget
    assert limiter.check("session_1", "run_conjecture_check") is True


def test_rate_limiter_ignores_unrestricted_actions():
    limiter = _RateLimiter()
    # An action not in _RATE_LIMITED_ACTIONS should never be blocked
    for _ in range(1000):
        assert limiter.check("session_1", "get_problem_catalog") is True
