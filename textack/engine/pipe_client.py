# textack/engine/pipe_client.py
"""Generic stdio worker client (phase 5).

One pattern for the whole fleet: spawn, fire-and-forget notifies (no id
means no reply, so the pipe can never fill up), id-matched requests via
a background reader thread (works where select() cannot poll pipes,
i.e. Windows). SfxClient (sfx_client.py) is a thin trigger-flavored
subclass; the supervisor uses this class directly for sim/content.
"""
import itertools
import queue
import subprocess
import threading
import time
from pathlib import Path

from textack.engine.transport import MessageIO

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class PipeError(RuntimeError):
    pass


class PipeClient:
    def __init__(self, cmd, cwd=None):
        self.proc = subprocess.Popen(list(cmd), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL,
                                     cwd=str(cwd or REPO_ROOT))
        self.io = MessageIO(self.proc.stdout, self.proc.stdin)
        self._incoming: queue.Queue = queue.Queue()
        self._ids = itertools.count(1)
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _pump(self):
        try:
            while True:
                self._incoming.put(self.io.recv())
        except (EOFError, ValueError, TypeError, OSError):
            self._incoming.put(None)

    def _send(self, msg):
        try:
            self.io.send(msg)
        except (BrokenPipeError, OSError) as e:
            raise PipeError(f"worker unreachable: {e}")

    def notify(self, msg):
        """Fire-and-forget. Never blocks, never reads."""
        self._send(dict(msg))

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

    def call(self, msg, timeout=10.0):
        """Loopback-compatible entry point (see transport.Loopback.call)."""
        req = dict(msg)
        if "id" not in req:
            mid = next(self._ids)
            req["id"] = mid
        return self.request(req, timeout)

    def _await(self, mid, timeout):
        stash = []
        end = time.monotonic() + timeout
        try:
            while True:
                left = end - time.monotonic()
                if left <= 0:
                    raise PipeError("worker timeout")
                try:
                    rep = self._incoming.get(timeout=left)
                except queue.Empty:
                    raise PipeError("worker timeout")
                if rep is None:
                    raise PipeError("worker exited")
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
        except PipeError:
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
