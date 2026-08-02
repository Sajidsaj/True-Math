"""
Module Name: ipc_handler
Purpose: Establish massive Asyncio communication throughput with the Tauri Frontend using native WebSockets.
Responsibilities:
  - Expose Python asynchronous WebSockets natively.
  - Provide a stream of real-time mathematically intense stats (MCTS sizes, memory).
  - Securely handle incoming Frontend actions (Pause Research, Restart).
Dependencies: asyncio, json, hashlib, base64
"""
import asyncio
import base64
import hashlib
import json
import time
import uuid
from typing import Any, Callable, Dict, Optional, Set
from urllib.parse import urlsplit

from src.core.sys_logger import get_logger

logger = get_logger("UI_IPC_Bridge")

# Security: maximum inbound WebSocket frame accepted (64 KB)
_MAX_WS_FRAME_BYTES: int = 65_536
# Security: maximum concurrent WebSocket connections
_MAX_CONNECTIONS: int = 10
_MAX_HEADER_BYTES: int = 8_192

# Actions that do real CPU/network work and could be abused if hammered
# repeatedly by a single client (public multi-user deployments especially).
# Format: action_name -> max calls allowed per rolling 60-second window.
_RATE_LIMITED_ACTIONS: Dict[str, int] = {
    "ask_question": 15,
    "ask_agent": 10,
    "run_conjecture_check": 10,
    "solve_hard_problem": 30,
    "discover": 20,
    "oeis_lookup": 15,
    "search_arxiv": 15,
    "export_history": 5,
}


class _RateLimiter:
    """Simple per-session sliding-window rate limiter (in-memory, no
    external dependency). Tracks recent call timestamps per (session_id,
    action) pair and rejects once the per-minute cap is exceeded."""

    def __init__(self):
        self._calls: Dict[str, list] = {}

    def check(self, session_id: str, action: str) -> bool:
        """Returns True if this call is allowed, False if rate-limited."""
        limit = _RATE_LIMITED_ACTIONS.get(action)
        if limit is None:
            return True  # not a rate-limited action

        key = f"{session_id}:{action}"
        now = time.monotonic()
        window_start = now - 60.0
        recent = [t for t in self._calls.get(key, []) if t > window_start]

        if len(recent) >= limit:
            self._calls[key] = recent
            return False

        recent.append(now)
        self._calls[key] = recent
        return True


def _is_loopback_host(host: str | None) -> bool:
    if host is None:
        return False
    normalized = host.strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    if ":" in normalized and normalized.count(":") == 1 and normalized not in {"::1"}:
        normalized = normalized.split(":", 1)[0]
    return normalized in {"127.0.0.1", "localhost", "::1"}

class IPCBridgeServer:
    __slots__ = ('host', 'port', '_server', '_server_task', '_callbacks', '_connections', '_loop', '_on_connect_callback', '_rate_limiter')
    
    def __init__(self, host: str = '127.0.0.1', port: int = 9999):
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None
        self._server_task = None
        self._callbacks: Dict[str, Callable] = {}
        self._connections: Set[asyncio.StreamWriter] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._on_connect_callback: Optional[Callable] = None
        self._rate_limiter = _RateLimiter()
        logger.info(f"IPC Frontend Bridge bound securely to {host}:{port}")

    def register_action(self, action_name: str, callback: Callable) -> None:
        """Binds a Frontend React command to a Python Backend function natively."""
        self._callbacks[action_name] = callback
        logger.debug(f"IPC Registered command mapping: {action_name}")

    def register_on_connect(self, callback: Callable) -> None:
        """Register a callback to send initial data when a new client connects."""
        self._on_connect_callback = callback

    async def send_to_client(self, writer: asyncio.StreamWriter, message: Dict[str, Any]) -> None:
        """Send a message to a single specific client."""
        try:
            frame_bytes = self.encode_websocket_frame(json.dumps(message))
            writer.write(frame_bytes)
            await writer.drain()
        except Exception:
            self._connections.discard(writer)

    async def perform_handshake(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """Parses browser HTTP WebSocket upgrade request and sends standard handshake response."""
        headers = {}
        request_line = None
        header_bytes = 0
        try:
            while True:
                line_bytes = await reader.readline()
                header_bytes += len(line_bytes)
                if header_bytes > _MAX_HEADER_BYTES:
                    logger.warning("IPC handshake rejected: request headers exceeded size cap.")
                    return False
                if not line_bytes or line_bytes == b"\r\n":
                    break
                line = line_bytes.decode('utf-8', errors='ignore').strip()
                if request_line is None:
                    request_line = line
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
        except Exception:
            return False

        if not request_line:
            return False

        parts = request_line.split()
        if len(parts) != 3 or parts[0] != "GET":
            logger.warning(f"IPC handshake rejected: invalid request line '{request_line}'.")
            return False

        request_path = urlsplit(parts[1]).path
        if request_path != "/ws":
            logger.warning(f"IPC handshake rejected: unexpected WebSocket path '{request_path}'.")
            return False

        host_header = headers.get("host")
        if host_header and not _is_loopback_host(host_header):
            logger.warning(f"IPC handshake rejected: non-loopback host header '{host_header}'.")
            return False

        origin = headers.get("origin")
        if origin:
            origin_host = urlsplit(origin).hostname
            if not _is_loopback_host(origin_host):
                logger.warning(f"IPC handshake rejected: non-loopback origin '{origin}'.")
                return False

        key = headers.get("sec-websocket-key")
        if not key:
            return False

        # Standard RFC 6455 GUID for WebSockets accept hashing
        guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_raw = key + guid
        accept_sha1 = hashlib.sha1(accept_raw.encode('utf-8')).digest()
        accept_key = base64.b64encode(accept_sha1).decode('utf-8')
        
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        try:
            writer.write(response.encode('utf-8'))
            await writer.drain()
            return True
        except Exception:
            return False

    async def read_websocket_frame(self, reader: asyncio.StreamReader) -> Optional[str]:
        """Reads and decodes a single client-to-server WebSocket frame."""
        try:
            header = await reader.readexactly(2)
        except (asyncio.IncompleteReadError, ConnectionResetError, OSError):
            return None
            
        b1, b2 = header[0], header[1]
        opcode = b1 & 0x0f
        masked = (b2 & 0x80) != 0
        payload_len = b2 & 0x7f

        if opcode == 0x8:  # Connection close frame
            return None

        if not masked:
            logger.warning("Security: Rejected unmasked client WebSocket frame.")
            return None

        if payload_len == 126:
            len_bytes = await reader.readexactly(2)
            payload_len = int.from_bytes(len_bytes, byteorder='big')
        elif payload_len == 127:
            len_bytes = await reader.readexactly(8)
            payload_len = int.from_bytes(len_bytes, byteorder='big')

        # Security: reject oversized frames before allocating memory
        if payload_len > _MAX_WS_FRAME_BYTES:
            logger.warning(f"Security: Rejected oversized WebSocket frame ({payload_len} bytes). Closing connection.")
            return None
            
        mask_key = b""
        if masked:
            mask_key = await reader.readexactly(4)
            
        try:
            payload = await reader.readexactly(payload_len)
        except (asyncio.IncompleteReadError, ConnectionResetError, OSError):
            return None
            
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            
        return payload.decode('utf-8', errors='ignore')

    def encode_websocket_frame(self, message: str) -> bytes:
        """Wraps a UTF-8 string message into a standard server-to-client WebSocket frame."""
        payload = message.encode('utf-8')
        length = len(payload)
        
        header = bytearray([0x81])  # FIN=1, opcode=1 (text)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header.extend(length.to_bytes(2, byteorder='big'))
        else:
            header.append(127)
            header.extend(length.to_bytes(8, byteorder='big'))
            
        return bytes(header) + payload

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Asynchronously processes incoming UI JSON payloads without blocking calculations."""
        addr = writer.get_extra_info('peername')

        # Security: reject connections above the connection cap
        if len(self._connections) >= _MAX_CONNECTIONS:
            logger.warning(f"Security: Connection limit ({_MAX_CONNECTIONS}) reached. Rejecting {addr}.")
            writer.close()
            return

        logger.info(f"IPC connection attempt from {addr}")
        self._connections.add(writer)
        session_id = str(uuid.uuid4())
        
        try:
            is_websocket = await self.perform_handshake(reader, writer)
            if not is_websocket:
                logger.warning(f"Handshake failed or connection from {addr} is not a valid WebSocket.")
                return
                
            logger.info(f"IPC WebSocket handshaked successfully for {addr}")

            # Send initial state to new client if callback registered
            if self._on_connect_callback:
                initial_messages = self._on_connect_callback()
                for msg in initial_messages:
                    await self.send_to_client(writer, msg)
            
            while True:
                message = await self.read_websocket_frame(reader)
                if message is None:
                    break
                    
                try:
                    payload = json.loads(message)
                    action = payload.get("action")
                    
                    if action in self._callbacks:
                        if not self._rate_limiter.check(session_id, action):
                            response = {
                                "status": "error",
                                "message": f"Rate limit hit for '{action}' — thodi der ruk kar dobara try karein (max {_RATE_LIMITED_ACTIONS.get(action)}/minute).",
                            }
                        else:
                            call_data = dict(payload.get("data", {}))
                            call_data["_session_id"] = session_id
                            result = self._callbacks[action](call_data)
                            # Some actions (e.g. ask_question) call the LLM and are
                            # implemented as async methods so the blocking HTTP
                            # call runs in a thread executor instead of freezing
                            # this event loop for every other connected client.
                            response = await result if asyncio.iscoroutine(result) else result
                    else:
                        response = {"status": "error", "message": f"Unknown structural action {action}"}
                        
                    frame_bytes = self.encode_websocket_frame(json.dumps(response))
                    writer.write(frame_bytes)
                    await writer.drain()
                    
                except json.JSONDecodeError:
                    logger.warning("IPC received fatal unstructured JSON payload.")
                    err_frame = self.encode_websocket_frame(json.dumps({"status": "error", "message": "Invalid JSON"}))
                    writer.write(err_frame)
                    await writer.drain()
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in IPC WebSocket handler for {addr}: {e}")
        finally:
            logger.info(f"IPC Connection {addr} terminated gracefully.")
            self._connections.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start_server(self):
        """Spins up the async socket handler loops."""
        self._loop = asyncio.get_running_loop()
        self._server = await asyncio.start_server(self.handle_client, self.host, self.port)
        
        import socket
        for sock in self._server.sockets:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
        try:
            async with self._server:
                logger.info("IPC Socket loop fully engaged with WebSockets and TCP_NODELAY optimization.")
                await self._server.serve_forever()
        except asyncio.CancelledError:
            logger.info("IPC Server serve_forever task was cancelled.")

    async def stop_server(self):
        """Cleanly stops the TCP/WebSocket server socket loop and active client connections."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            
        if self._connections:
            temp_connections = list(self._connections)
            for writer in temp_connections:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
            self._connections.clear()
        logger.info("IPC Socket server cleanly shut down and ports released.")

    def stop(self) -> None:
        """Synchronously schedules shutdown on the server loop from another thread."""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.stop_server(), self._loop)
            try:
                future.result(timeout=2.0)
            except Exception as exc:
                logger.warning(f"IPC shutdown did not complete cleanly: {exc}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Asynchronously pushes a message payload to all connected clients."""
        if not self._connections:
            return
            
        payload = json.dumps(message)
        frame_bytes = self.encode_websocket_frame(payload)
        
        # Make a copy of connections to iterate safely
        active_writers = list(self._connections)
        for writer in active_writers:
            try:
                writer.write(frame_bytes)
                await writer.drain()
            except Exception:
                self._connections.discard(writer)

    def broadcast_sync(self, message: Dict[str, Any]) -> None:
        """Thread-safe synchronous wrapper to broadcast from other OS threads."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)
