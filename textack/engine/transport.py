# textack/engine/transport.py
"""Transports for protocol v1.

Two flavors, same contract (docs/PROTOCOL.md):

- MessageIO: newline-delimited JSON over any binary streams
  (socket pairs, pipes, subprocess stdio — the future worker fleet).
- Loopback: in-process transport for phase 1. Director and worker share
  a call stack, but may only exchange protocol messages, each forced
  through a full encode/decode roundtrip both ways. If the game ever
  talks to a real worker, only this class gets swapped.
"""
from textack.engine import proto


class MessageIO:
    def __init__(self, rfile, wfile):
        self.r = rfile
        self.w = wfile

    def send(self, msg):
        self.w.write(proto.encode(msg))
        self.w.flush()

    def recv(self):
        line = self.r.readline()
        if not line:
            raise EOFError("peer closed the stream")
        return proto.decode(line)


class Loopback:
    def __init__(self, worker):
        self.worker = worker

    def call(self, msg, timeout=None):
        req = proto.decode(proto.encode(msg))
        rep = self.worker.handle(req)
        return proto.decode(proto.encode(rep))

    def notify(self, msg):
        self.worker.handle(proto.decode(proto.encode(msg)))

    def close(self, timeout=None):
        return True

    @property
    def alive(self):
        return True
