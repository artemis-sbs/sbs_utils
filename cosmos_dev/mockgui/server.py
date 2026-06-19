"""
server.py — stdlib-only WebSocket bridge (no pip dependencies).

Implements HTTP + WebSocket (RFC 6455) using asyncio.start_server,
hashlib, base64, and struct.  No uvicorn/fastapi required.

Receives shared queues from the parent process via run_server() and does
NOT import the sbs module — all communication goes through the queues.

Run standalone:
    python -m cosmos_dev.mockgui.server

Or started automatically by cosmos_dev.mockgui.sbs.start_server() in a
child process.
"""

import asyncio
import base64
import hashlib
import json
import multiprocessing
import os
import struct
from typing import Dict, List, Optional, Set

VERBOSE: bool = True

def _log(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)

_HERE        = os.path.dirname(os.path.abspath(__file__))
_CLIENT_HTML = os.path.join(_HERE, "client.html")

# ---------------------------------------------------------------------------
# Injected by run_server() before the event loop starts
# ---------------------------------------------------------------------------
_gui_queue:          Optional[multiprocessing.Queue] = None
_client_event_queue: Optional[multiprocessing.Queue] = None
_gui_event_queue:    Optional[multiprocessing.Queue] = None
_ready_event:        Optional[multiprocessing.Event] = None

# ---------------------------------------------------------------------------
# Frame state
# ---------------------------------------------------------------------------
_connections:    Dict[int, Set[asyncio.StreamWriter]] = {}
_next_client_id: int = 0x8080000000000001
_last_frame:     Dict[int, List[dict]] = {}   # last committed (complete) frame
_pending_frame:  Dict[int, List[dict]] = {}   # frame being built (after clear, before complete)
_lock:           Optional[asyncio.Lock] = None

def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock

# ---------------------------------------------------------------------------
# WebSocket protocol (RFC 6455)
# ---------------------------------------------------------------------------
_WS_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def _ws_accept_key(key: str) -> str:
    combined = key.strip().encode() + _WS_GUID
    return base64.b64encode(hashlib.sha1(combined).digest()).decode()

async def _ws_send(writer: asyncio.StreamWriter, text: str) -> None:
    data   = text.encode()
    length = len(data)
    header = bytearray([0x81])          # FIN=1, opcode=1 (text frame)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header += struct.pack('>H', length)
    else:
        header.append(127)
        header += struct.pack('>Q', length)
    writer.write(bytes(header) + data)
    await writer.drain()

async def _ws_recv(reader: asyncio.StreamReader) -> tuple:
    """Returns (opcode, payload). Raises asyncio.IncompleteReadError on disconnect."""
    hdr     = await reader.readexactly(2)
    opcode  = hdr[0] & 0x0F
    masked  = bool(hdr[1] & 0x80)
    length  = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack('>H', await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack('>Q', await reader.readexactly(8))[0]
    mask    = await reader.readexactly(4) if masked else b''
    payload = await reader.readexactly(length)
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload

async def _ws_close(writer: asyncio.StreamWriter) -> None:
    try:
        writer.write(bytes([0x88, 0x00]))   # close frame
        await writer.drain()
    except Exception:
        pass
    try:
        writer.close()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
async def _read_http_headers(reader: asyncio.StreamReader) -> dict:
    """Parse HTTP request line + headers. Returns {} on error."""
    request_line = None
    headers: Dict[str, str] = {}
    while True:
        raw = await reader.readline()
        if not raw or raw == b'\r\n':
            break
        line = raw.decode('utf-8', errors='replace').rstrip()
        if request_line is None:
            request_line = line
        elif ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip().lower()] = v.strip()
    if not request_line:
        return {}
    parts = request_line.split(' ', 2)
    return {
        'method':  parts[0] if parts else '',
        'path':    parts[1] if len(parts) > 1 else '/',
        'headers': headers,
    }

async def _http_send(writer: asyncio.StreamWriter,
                     status: str, content_type: str, body) -> None:
    if isinstance(body, str):
        body = body.encode()
    resp = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode() + body
    writer.write(resp)
    await writer.drain()
    try:
        writer.close()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Connection registry
# ---------------------------------------------------------------------------
async def _register(client_id: int, writer: asyncio.StreamWriter) -> None:
    async with _get_lock():
        _connections.setdefault(client_id, set()).add(writer)

async def _unregister(client_id: int, writer: asyncio.StreamWriter) -> None:
    async with _get_lock():
        _connections.get(client_id, set()).discard(writer)

async def _replay(client_id: int, writer: asyncio.StreamWriter) -> None:
    """Send the last committed frame to a freshly connected client."""
    frames: List[dict] = []
    async with _get_lock():
        frames = list(_last_frame.get(0, [])) + list(_last_frame.get(client_id, []))
    _log(f"[replay] client={client_id} sending {len(frames)} commands "
         f"(last_frame keys={list(_last_frame.keys())})")
    for payload in frames:
        try:
            await _ws_send(writer, json.dumps(payload))
        except Exception as e:
            _log(f"[replay] send failed: {e}")
            break
    _log(f"[replay] client={client_id} done")

# ---------------------------------------------------------------------------
# Broadcast + frame recording
# ---------------------------------------------------------------------------
async def _broadcast(payload: dict) -> None:
    """Record the command into the pending frame and forward to live clients."""
    client_id = payload.get("clientID", 0)
    cmd       = payload.get("cmd")

    if cmd == "log":
        # Log messages go to all browsers but are never recorded in frames
        # (they must not replay when a new browser tab connects).
        async with _get_lock():
            targets: Set[asyncio.StreamWriter] = set()
            for bucket in _connections.values():
                targets |= bucket
    else:
        async with _get_lock():
            if cmd == "clear":
                _pending_frame[client_id] = [payload]
            elif cmd == "complete":
                frame = _pending_frame.get(client_id, [])
                frame.append(payload)
                _last_frame[client_id]    = frame
                _pending_frame[client_id] = []
            else:
                _pending_frame.setdefault(client_id, []).append(payload)

            if client_id == 0:
                targets = set()
                for bucket in _connections.values():
                    targets |= bucket
            else:
                targets = set(_connections.get(client_id, set()))

    dead = []
    msg  = json.dumps(payload)
    for writer in targets:
        try:
            await _ws_send(writer, msg)
        except Exception:
            dead.append(writer)

    if dead:
        async with _get_lock():
            for writer in dead:
                for bucket in _connections.values():
                    bucket.discard(writer)

# ---------------------------------------------------------------------------
# Queue dispatcher
# ---------------------------------------------------------------------------
async def _queue_dispatcher() -> None:
    loop = asyncio.get_event_loop()
    while True:
        payload = await loop.run_in_executor(None, _gui_queue.get)
        await _broadcast(payload)

# ---------------------------------------------------------------------------
# WebSocket connection handler
# ---------------------------------------------------------------------------
async def _handle_websocket(client_id: int,
                              reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter) -> None:
    await _ws_send(writer, json.dumps({"cmd": "init", "clientID": client_id}))
    await _register(client_id, writer)
    _client_event_queue.put({"event": "connect", "clientID": client_id})
    _log(f"[server] client {client_id} connected")
    await _replay(client_id, writer)

    try:
        while True:
            opcode, payload = await _ws_recv(reader)
            if opcode == 8:     # close frame
                break
            if opcode == 1:     # text frame
                text  = payload.decode('utf-8', errors='replace')
                event = json.loads(text)
                # Browser may send clientID=0 to act as server; respect it
                event.setdefault("clientID", client_id)
                _log(f"[event]  client={client_id} effective={event['clientID']} {event}")
                _gui_event_queue.put(event)
    except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        await _ws_close(writer)
        await _unregister(client_id, writer)
        _client_event_queue.put({"event": "disconnect", "clientID": client_id})
        _log(f"[server] client {client_id} disconnected")

# ---------------------------------------------------------------------------
# Raw TCP connection handler (HTTP + WebSocket upgrade)
# ---------------------------------------------------------------------------
async def _handle_connection(reader: asyncio.StreamReader,
                               writer: asyncio.StreamWriter) -> None:
    global _next_client_id
    try:
        req = await _read_http_headers(reader)
        if not req:
            writer.close()
            return

        headers = req.get('headers', {})
        is_ws = (
            headers.get('upgrade', '').lower() == 'websocket'
            and 'upgrade' in headers.get('connection', '').lower()
            and 'sec-websocket-key' in headers
        )

        if is_ws:
            key    = headers['sec-websocket-key']
            accept = _ws_accept_key(key)
            writer.write((
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            ).encode())
            await writer.drain()

            async with _get_lock():
                client_id       = _next_client_id
                _next_client_id += 1
            await _handle_websocket(client_id, reader, writer)
        else:
            try:
                with open(_CLIENT_HTML, 'r', encoding='utf-8') as f:
                    html = f.read()
                await _http_send(writer, "200 OK", "text/html; charset=utf-8", html)
            except FileNotFoundError:
                await _http_send(writer, "404 Not Found", "text/plain",
                                  f"client.html not found at {_CLIENT_HTML}")
    except Exception as e:
        _log(f"[server] connection error: {e}")
        try:
            writer.close()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Main async entry
# ---------------------------------------------------------------------------
async def _serve(host: str, port: int) -> None:
    server = await asyncio.start_server(_handle_connection, host, port)
    if _ready_event is not None:
        _ready_event.set()
    _log(f"[server] listening on {host}:{port}")
    async with server:
        await asyncio.gather(
            server.serve_forever(),
            _queue_dispatcher(),
        )

# ---------------------------------------------------------------------------
# Subprocess entry point (called by sbs.start_server)
# ---------------------------------------------------------------------------
def run_server(
    gui_q:          multiprocessing.Queue,
    client_event_q: multiprocessing.Queue,
    gui_event_q:    multiprocessing.Queue,
    ready_event:    multiprocessing.Event,
    host: str = "0.0.0.0",
    port: int = 8765,
) -> None:
    """Inject shared queues, then start the asyncio event loop. Runs in a child process."""
    global _gui_queue, _client_event_queue, _gui_event_queue, _ready_event
    _gui_queue          = gui_q
    _client_event_queue = client_event_q
    _gui_event_queue    = gui_event_q
    _ready_event        = ready_event
    asyncio.run(_serve(host, port))

# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    _gui_queue          = multiprocessing.Queue()
    _client_event_queue = multiprocessing.Queue()
    _gui_event_queue    = multiprocessing.Queue()
    asyncio.run(_serve(host, port))
