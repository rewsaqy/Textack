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
        print("Jalankan di terminal asli: textack")
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
                "curses tidak ketemu di Windows.\n"
                "Install dulu:  pip install windows-curses\n"
                "atau:          pip install textack[windows]\n"
                "lalu jalankan lagi:  textack"
            )
        else:
            _eprint(
                "curses tidak ketemu. Di Linux biasanya sudah bawaan Python.\n"
                "Coba: sudo pacman -S ncurses  /  sudo apt install libncurses6"
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
            "Terminal ini tidak bisa mode fullscreen (curses).\n"
            "Coba: Windows Terminal / Ghostty / WezTerm / Konsole / xterm."
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
