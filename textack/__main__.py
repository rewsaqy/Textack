import os
import sys


def _eprint(*a):
    print(*a, file=sys.stderr)


def main():
    if not sys.stdin.isatty():
        if "--gfx-test" in sys.argv:
            from textack.ui import gfx

            print(gfx.test_report(sys.argv[1:], os.environ))
            return
        print("Run in a real terminal: textack")
        sys.exit(1)
    if "--gfx-test" in sys.argv:
        from textack.ui import gfx

        print(gfx.test_report(sys.argv[1:], os.environ))
        return
    os.environ.setdefault("ESCDELAY", "25")

    try:
        import curses
    except ImportError:
        if os.name == "nt":
            _eprint(
                "curses not found on Windows.\n"
                "Install it first:  pip install windows-curses\n"
                "or:                 pip install textack[windows]\n"
                "then run again:     textack"
            )
        else:
            _eprint(
                "curses not found. On Linux it usually ships with Python.\n"
                "Try: sudo pacman -S ncurses  /  sudo apt install libncurses6"
            )
        sys.exit(1)

    try:
        from textack.ui import gfx
        from textack.ui.screens.loop import game_loop

        gfx.resolve(sys.argv[1:], os.environ, allow_probe=True)
        curses.wrapper(game_loop)
    except KeyboardInterrupt:
        pass
    except curses.error:
        _eprint(
            "This terminal cannot do fullscreen mode (curses).\n"
            "Try: Windows Terminal / Ghostty / WezTerm / Konsole / xterm."
        )
        sys.exit(2)
    try:
        from textack.ui import gfx as _gfx

        _gfx.emit(_gfx.build_delete_visible())
    except Exception:  # noqa: BLE001, S110
        pass
    print("made by rewsaqy • 2026")


if __name__ == "__main__":
    main()
