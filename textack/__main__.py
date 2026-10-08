import os
import sys


def _eprint(*a):
    print(*a, file=sys.stderr)


def main():
    if not sys.stdin.isatty():
        print("Jalankan di terminal asli: textack")
        sys.exit(1)
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
        from textack.ui.screens.loop import game_loop
        curses.wrapper(game_loop)
    except KeyboardInterrupt:
        pass
    print("made by rewsaqy • 2026")


if __name__ == "__main__":
    main()
