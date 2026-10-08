# tests/test_guard.py
from textack.ui import guard


class FakeScr:
    def __init__(self, sizes, keys=None):
        self.sizes = list(sizes)
        self.keys = list(keys or [])
        self.i = 0

    def getmaxyx(self):
        return self.sizes[min(self.i, len(self.sizes) - 1)]

    def nodelay(self, _v):
        pass

    def timeout(self, _v):
        pass

    def erase(self):
        pass

    def addstr(self, * _a):
        pass

    def refresh(self):
        pass

    def getch(self):
        self.i += 1
        return self.keys.pop(0) if self.keys else -1


def test_too_small():
    assert guard.too_small(24, 80) is False
    assert guard.too_small(23, 200) is True
    assert guard.too_small(40, 79) is True
    assert guard.too_small(24, 80, min_w=100) is True


def test_wait_recovers_on_resize():
    f = FakeScr([(10, 30), (10, 30), (24, 80)])
    assert guard.wait_until_fit(f, {}) is None


def test_wait_quit():
    f = FakeScr([(10, 30)], keys=[ord("q")])
    assert guard.wait_until_fit(f, {}) == "quit"
