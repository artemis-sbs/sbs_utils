"""A stdlib obs-websocket v5 client - just enough of the protocol for the harness.

Why not `obsws-python`: everything in cosmos_dev is stdlib-only (driver.py,
mission_soak.py, mockgui/server.py), the dev interpreter moves ahead of wheel
availability, and the parts of the protocol used here are small.

The RFC 6455 framing is the mirror of `cosmos_dev/mockgui/server.py`, which implements
the SERVER half. The one thing a client must do that a server must not: mask every
frame it sends.
"""
import os
import json
import base64
import hashlib
import secrets
import socket
import struct
import time


DEFAULT_PORT = 4455
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# obs-websocket opcodes
OP_HELLO = 0
OP_IDENTIFY = 1
OP_IDENTIFIED = 2
OP_REQUEST = 6
OP_REQUEST_RESPONSE = 7


class ObsError(RuntimeError):
    """A request was refused by OBS, or the connection could not be established."""


def obs_config_path():
    """Where OBS keeps the websocket server's own settings."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return os.path.join(appdata, "obs-studio", "plugin_config",
                        "obs-websocket", "config.json")


def obs_config():
    """Read OBS's websocket config: server_enabled, server_port, server_password.

    Read rather than asked for on the command line - the settings already exist, and a
    flag that disagrees with them is just a second place to be wrong.
    """
    p = obs_config_path()
    if not p or not os.path.isfile(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# --- RFC 6455, client half ------------------------------------------------------------

def _accept_key(key):
    return base64.b64encode(
        hashlib.sha1((key + _GUID).encode("ascii")).digest()).decode("ascii")


def _send_frame(sock, payload, opcode=0x1):
    """Send one masked frame. A client MUST mask; a server MUST NOT."""
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    n = len(data)
    hdr = bytearray([0x80 | opcode])
    if n < 126:
        hdr.append(0x80 | n)
    elif n < (1 << 16):
        hdr.append(0x80 | 126)
        hdr += struct.pack(">H", n)
    else:
        hdr.append(0x80 | 127)
        hdr += struct.pack(">Q", n)
    mask = secrets.token_bytes(4)
    hdr += mask
    sock.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ObsError("connection closed by OBS")
        buf += chunk
    return buf


def _recv_frame(sock):
    """Read one frame, reassembling continuations. Returns (opcode, bytes)."""
    payload = b""
    first_op = None
    while True:
        b0, b1 = _recv_exact(sock, 2)
        fin = b0 & 0x80
        opcode = b0 & 0x0F
        masked = b1 & 0x80
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack(">H", _recv_exact(sock, 2))[0]
        elif n == 127:
            n = struct.unpack(">Q", _recv_exact(sock, 8))[0]
        mask = _recv_exact(sock, 4) if masked else None
        data = _recv_exact(sock, n) if n else b""
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        if first_op is None and opcode != 0x0:
            first_op = opcode
        payload += data
        if fin:
            return (first_op if first_op is not None else opcode), payload


# --- the client -----------------------------------------------------------------------

class ObsClient:
    """A connected obs-websocket session. Use as a context manager."""

    def __init__(self, sock, rpc_version, ws_version):
        self._sock = sock
        self.rpc_version = rpc_version
        self.ws_version = ws_version
        self._n = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass

    def request(self, request_type, data=None, timeout=15.0):
        """Send one request and return its responseData. Raises ObsError on failure."""
        self._n += 1
        rid = "sz%d" % self._n
        _send_frame(self._sock, json.dumps({
            "op": OP_REQUEST,
            "d": {"requestType": request_type, "requestId": rid,
                  "requestData": data or {}},
        }))
        deadline = time.time() + timeout
        while True:
            self._sock.settimeout(max(0.1, deadline - time.time()))
            opcode, raw = _recv_frame(self._sock)
            if opcode == 0x8:
                raise ObsError("OBS closed the connection")
            if opcode not in (0x1, 0x2):
                continue
            msg = json.loads(raw.decode("utf-8"))
            if msg.get("op") != OP_REQUEST_RESPONSE:
                continue                      # an event; not what we asked for
            d = msg.get("d") or {}
            if d.get("requestId") != rid:
                continue                      # someone else's reply; keep reading
            status = d.get("requestStatus") or {}
            if not status.get("result"):
                raise ObsError("%s failed: %s" % (
                    request_type, status.get("comment") or status.get("code")))
            return d.get("responseData") or {}

    # --- the handful of requests the harness actually uses ---------------------------

    def version(self):
        return self.request("GetVersion")

    def scenes(self):
        return self.request("GetSceneList")

    def inputs(self):
        return self.request("GetInputList")

    # --- scene / source plumbing -----------------------------------------------------

    def scene_names(self):
        return [s.get("sceneName") for s in (self.scenes().get("scenes") or [])]

    def current_scene(self):
        out = self.request("GetCurrentProgramScene")
        return out.get("sceneName") or out.get("currentProgramSceneName")

    def set_current_scene(self, name):
        self.request("SetCurrentProgramScene", {"sceneName": name})

    def create_scene(self, name, timeout=5.0):
        """Create a scene and WAIT until OBS agrees it exists.

        Checking scene_names() first and skipping was racy: a RemoveScene immediately
        before can still be settling, so the name looks present, CreateScene is
        skipped, and the CreateInput that follows fails with "no source was found by
        the name of <scene>". Ask unconditionally, tolerate "already exists", then
        confirm.
        """
        try:
            self.request("CreateScene", {"sceneName": name})
        except ObsError:
            pass                              # already there is fine
        deadline = time.time() + timeout
        while time.time() < deadline:
            if name in self.scene_names():
                return True
            time.sleep(0.15)
        raise ObsError("scene %r never appeared after CreateScene" % name)

    def remove_scene(self, name):
        try:
            self.request("RemoveScene", {"sceneName": name})
        except ObsError:
            pass

    def create_window_capture(self, scene, input_name, window):
        """A game_capture locked to one window title.

        `window` is OBS's triple - "<title>:<class>:<exe>". The engine's class is
        `Engine`, which is what makes capture-by-title work at all: the harness
        renames each client window and OBS finds it by that name.
        """
        self.request("CreateInput", {
            "sceneName": scene,
            "inputName": input_name,
            "inputKind": "game_capture",
            "inputSettings": {
                "capture_mode": "window",
                "window": window,
                "capture_audio": False,
                "capture_cursor": False,
            },
        })

    def input_names(self):
        return [i.get("inputName") for i in (self.inputs().get("inputs") or [])]

    def remove_input(self, input_name, timeout=5.0):
        """Remove an input and WAIT until OBS agrees it is gone.

        RemoveInput returns before the source is actually torn down, so a CreateInput
        immediately after fails with "a source already exists by that input name" -
        and the name in question is one this harness only just asked to delete. Same
        shape as the CreateScene race above.
        """
        try:
            self.request("RemoveInput", {"inputName": input_name})
        except ObsError:
            return                            # not there to begin with
        deadline = time.time() + timeout
        while time.time() < deadline:
            if input_name not in self.input_names():
                return
            time.sleep(0.15)

    # --- video settings and recording ------------------------------------------------

    def video_settings(self):
        return self.request("GetVideoSettings")

    def set_video_settings(self, base_w, base_h, out_w, out_h):
        """Set canvas and output size. CHANGES THE USER'S PROFILE - save the old values
        and put them back."""
        self.request("SetVideoSettings", {
            "baseWidth": int(base_w), "baseHeight": int(base_h),
            "outputWidth": int(out_w), "outputHeight": int(out_h),
        })

    def fit_source_to_canvas(self, scene, input_name):
        """Stretch a scene item to fill the canvas.

        A freshly created input sits at its native size at 0,0. If the canvas and the
        source differ at all, the take is captured with a border or a crop - and that
        is only visible once the reel is cut.
        """
        items = self.request("GetSceneItemList", {"sceneName": scene}).get("sceneItems") or []
        item_id = None
        for it in items:
            if it.get("sourceName") == input_name:
                item_id = it.get("sceneItemId")
                break
        if item_id is None:
            return False
        v = self.video_settings()
        self.request("SetSceneItemTransform", {
            "sceneName": scene,
            "sceneItemId": item_id,
            "sceneItemTransform": {
                "positionX": 0, "positionY": 0,
                "boundsType": "OBS_BOUNDS_SCALE_INNER",
                "boundsAlignment": 0,
                "boundsWidth": float(v.get("baseWidth") or 1920),
                "boundsHeight": float(v.get("baseHeight") or 1080),
            },
        })
        return True

    def set_record_directory(self, path):
        self.request("SetRecordDirectory", {"recordDirectory": path})

    def start_record(self):
        self.request("StartRecord")

    def stop_record(self):
        """Stop, and return the file OBS actually wrote."""
        out = self.request("StopRecord")
        return out.get("outputPath")

    def record_status(self):
        return self.request("GetRecordStatus")

    def source_screenshot(self, source, fmt="png", width=None):
        """Return one source's current frame as raw image bytes.

        This is the whole reason for preferring OBS over a desktop grab: it is cropped
        to the source and correct even when the window is occluded.
        """
        data = {"sourceName": source, "imageFormat": fmt}
        if width:
            data["imageWidth"] = int(width)
        out = self.request("GetSourceScreenshot", data)
        b64 = out.get("imageData") or ""
        if "," in b64:                        # data:image/png;base64,....
            b64 = b64.split(",", 1)[1]
        return base64.b64decode(b64)


def connect(host="127.0.0.1", port=None, password=None, timeout=10.0):
    """Open an obs-websocket session, authenticating if OBS asks.

    Port and password default to whatever OBS itself has configured.
    """
    cfg = obs_config()
    port = int(port or cfg.get("server_port") or DEFAULT_PORT)
    if password is None:
        password = cfg.get("server_password")

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as e:
        if cfg.get("server_enabled") is False:
            hint = ("the OBS websocket server is disabled - turn it on in "
                    "OBS -> Tools -> WebSocket Server Settings")
        else:
            hint = "is OBS running?"
        raise ObsError("cannot reach OBS at %s:%s (%s); %s" % (host, port, e, hint))

    key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
    sock.sendall(("GET / HTTP/1.1\r\n"
                  "Host: %s:%s\r\n"
                  "Upgrade: websocket\r\n"
                  "Connection: Upgrade\r\n"
                  "Sec-WebSocket-Key: %s\r\n"
                  "Sec-WebSocket-Version: 13\r\n\r\n"
                  % (host, port, key)).encode("ascii"))
    resp = b""
    sock.settimeout(timeout)
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise ObsError("OBS closed the connection during the handshake")
        resp += chunk
    head = resp.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    if "101" not in head.split("\r\n")[0]:
        raise ObsError("OBS refused the websocket upgrade: %s" % head.splitlines()[0])
    if _accept_key(key).lower() not in head.lower():
        raise ObsError("OBS returned a bad Sec-WebSocket-Accept")

    opcode, raw = _recv_frame(sock)
    hello = json.loads(raw.decode("utf-8"))
    if hello.get("op") != OP_HELLO:
        raise ObsError("expected Hello, got op %s" % hello.get("op"))
    hd = hello.get("d") or {}
    rpc = hd.get("rpcVersion", 1)

    ident = {"rpcVersion": rpc}
    auth = hd.get("authentication")
    if auth:
        if not password:
            raise ObsError("OBS requires a password and none was found in its config")
        secret = base64.b64encode(hashlib.sha256(
            (password + auth["salt"]).encode("utf-8")).digest()).decode("ascii")
        ident["authentication"] = base64.b64encode(hashlib.sha256(
            (secret + auth["challenge"]).encode("utf-8")).digest()).decode("ascii")

    _send_frame(sock, json.dumps({"op": OP_IDENTIFY, "d": ident}))
    opcode, raw = _recv_frame(sock)
    msg = json.loads(raw.decode("utf-8"))
    if msg.get("op") != OP_IDENTIFIED:
        raise ObsError("OBS did not accept Identify: %s" % msg)

    return ObsClient(sock, rpc, hd.get("obsWebSocketVersion"))
