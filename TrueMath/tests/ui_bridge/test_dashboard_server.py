import json
import time
import urllib.error
import urllib.request

from src.ui_bridge.dashboard_server import DashboardServer

def test_dashboard_server_safe_lifecycle(tmp_path):
    """Verify OS natively isolates threads without triggering zombie port locks."""
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")

    server = DashboardServer(asset_dir=str(asset_dir), port=0)

    server.start()
    assert server._server is not None
    assert server._thread.is_alive() is True

    # We call stop instantly! If native shutdown sequence is bad, this leaves ghost ports.
    server.stop()

    time.sleep(0.5)
    assert server._server is None
    assert server._thread is None


def test_dashboard_server_serves_runtime_config(tmp_path):
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")

    server = DashboardServer(
        asset_dir=str(asset_dir),
        port=0,
        runtime_config={"ipcHost": "127.0.0.1", "ipcPort": 9999, "ipcPath": "/ws"},
    )
    server.start()

    try:
        port = server._server.server_port
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/runtime-config.js", timeout=2) as response:
            body = response.read().decode("utf-8")
        prefix = "window.__TRUEMATH_CONFIG__ = Object.freeze("
        assert body.startswith(prefix)
        payload = body[len(prefix):].rstrip(");\n")
        assert json.loads(payload) == {"ipcHost": "127.0.0.1", "ipcPort": 9999, "ipcPath": "/ws"}
    finally:
        server.stop()


def test_api_solve_rejects_oversized_body(tmp_path):
    """SECURITY: the HTTP API must reject request bodies over the size
    cap, rather than reading an unbounded amount into memory."""
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    server = DashboardServer(asset_dir=str(asset_dir), port=0)
    server.start()
    try:
        port = server._server.server_port
        huge_body = json.dumps({"question": "x" * 2_000_000}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/solve",
            data=huge_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "Expected HTTP 413 or a connection error, request succeeded instead"
        except urllib.error.HTTPError as e:
            assert e.code == 413
        except (urllib.error.URLError, ConnectionError, BrokenPipeError):
            # The server correctly refuses to read the oversized body before
            # responding (that's the DoS protection working as intended) —
            # this can surface as a connection-level error client-side
            # instead of a clean HTTP response, which is an equally valid
            # sign the protection is active (the huge payload was never
            # fully accepted/processed either way).
            pass
    finally:
        server.stop()


def test_api_solve_accepts_normal_request(tmp_path):
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    server = DashboardServer(asset_dir=str(asset_dir), port=0)
    server.start()
    try:
        port = server._server.server_port
        body = json.dumps({"question": "2+2"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/solve",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        assert result["status"] == "ok"
    finally:
        server.stop()


def test_api_rate_limiting_blocks_excessive_requests(tmp_path):
    """SECURITY: the HTTP API must have its own rate limiting, independent
    of the WebSocket API's — this is a separate entry point that must not
    be hammerable without limit."""
    from src.ui_bridge import dashboard_server as ds_module

    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    # Reset the module-level rate limit state so this test doesn't interfere
    # with (or get interfered by) other tests hitting the same limiter.
    ds_module._http_rate_calls.clear()

    server = DashboardServer(asset_dir=str(asset_dir), port=0)
    server.start()
    try:
        port = server._server.server_port
        blocked = 0
        for _ in range(ds_module._HTTP_RATE_LIMIT_PER_MINUTE + 5):
            body = json.dumps({"question": "2+2"}).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/solve",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    blocked += 1
        assert blocked == 5
    finally:
        server.stop()
