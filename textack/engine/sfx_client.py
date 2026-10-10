# textack/engine/sfx_client.py
"""Director side of the sfx worker (phase 2).

Fire-and-forget triggers never block the game loop (notify semantic:
without an id the worker produces no reply, so the pipe can never fill
up). Requests WITH ids are matched by a background reader thread, which
also keeps the pipe drained on platforms where select() cannot poll
pipes (Windows). Usage:

    with SfxClient() as sfx:
        sfx.trigger("shoot")   # never blocks
        sfx.set_on(False)
"""
import itertools
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from textack.engine.transport import MessageIO

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class SfxError(RuntimeError):
    pass


class SfxClient:
    def __init__(self, base_dir=None, cwd=None):
        cmd = [sys.executable, "-m", "textack.engine.sfx_worker"]
        if base_dir is not None:
            cmd += ["--dir", str(base_dir)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL,
                                     cwd=str(cwd or REPO_ROOT))
        self.io = MessageIO(self.proc.stdout, self.proc.stdin)
        self._incoming: queue.Queue = queue.Queue()
        self._ids = itertools.count(1)
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()
        self.send_hello()

    def _pump(self):
        try:
            while True:
                self._incoming.put(self.io.recv())
        except (EOFError, ValueError, OSError):
            self._incoming.put(None)

    def _send(self, msg):
        try:
            self.io.send(msg)
        except (BrokenPipeError, OSError) as e:
            raise SfxError(f"worker unreachable: {e}")

    def send_hello(self):
        self._send({"v": 1, "t": "hello", "role": "director", "proto": [1]})

    def trigger(self, name):
        """Fire-and-forget sound. Never blocks, never reads."""
        self._send({"v": 1, "t": "sfx-trigger", "name": name})

    def set_on(self, on):
        """Fire-and-forget on/off switch."""
        self._send({"v": 1, "t": "sfx-set", "on": bool(on)})

    def request(self, msg, timeout=10.0):
        """Send a request and wait for its matching reply. An explicit id
        is honored; otherwise one is generated."""
        req = dict(msg)
        mid = req.get("id")
        if mid is None:
            mid = next(self._ids)
            req["id"] = mid
        self._send(req)
        return self._await(mid, timeout)

    def _await(self, mid, timeout):
        stash = []
        end = time.monotonic() + timeout
        try:
            while True:
                left = end - time.monotonic()
                if left <= 0:
                    raise SfxError("worker timeout")
                try:
                    rep = self._incoming.get(timeout=left)
                except queue.Empty:
                    raise SfxError("worker timeout")
                if rep is None:
                    raise SfxError("worker exited")
                if isinstance(rep, dict) and rep.get("id") == mid:
                    return rep
                stash.append(rep)
        finally:
            for m in stash:
                self._incoming.put(m)

    def ping(self, timeout=10.0):
        rep = self.request({"v": 1, "t": "ping"}, timeout)
        return rep.get("t") == "pong"

    @property
    def alive(self):
        return self.proc.poll() is None

    def close(self, timeout=5.0):
        try:
            rep = self.request({"v": 1, "t": "bye"}, timeout)
            ok = rep.get("t") == "bye"
        except SfxError:
            ok = False
        try:
            self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        return ok

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):  # best effort; prefer close() / context manager
        try:
            proc = getattr(self, "proc", None)
            if proc is not None and proc.poll() is None:
                proc.kill()
        except Exception:  # noqa: BLE001, S110
            pass
