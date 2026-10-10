# textack/engine/sfx_client.py
"""Director side of the sfx worker (phase 2).

Thin trigger-flavored subclass of pipe_client.PipeClient: fire-and-forget
triggers never block the game loop (notify semantic: without an id the
worker produces no reply, so the pipe can never fill up). Usage:

    with SfxClient() as sfx:
        sfx.trigger("shoot")   # never blocks
        sfx.set_on(False)
"""
import sys

from textack.engine.pipe_client import REPO_ROOT, PipeClient, PipeError

SfxError = PipeError


class SfxClient(PipeClient):
    def __init__(self, base_dir=None, cwd=None, cmd=None):
        if cmd is None:
            cmd = [sys.executable, "-m", "textack.engine.sfx_worker"]
            if base_dir is not None:
                cmd += ["--dir", str(base_dir)]
        super().__init__(cmd, cwd=cwd or REPO_ROOT)
        self.send_hello()

    def send_hello(self):
        self.notify({"v": 1, "t": "hello", "role": "director", "proto": [1]})

    def trigger(self, name):
        """Fire-and-forget sound. Never blocks, never reads."""
        self.notify({"v": 1, "t": "sfx-trigger", "name": name})

    def set_on(self, on):
        """Fire-and-forget on/off switch."""
        self.notify({"v": 1, "t": "sfx-set", "on": bool(on)})
