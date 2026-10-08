# Textack v1.0.00

> Side project just for fun — have fun!

Game terminal Linux 100% open source. **Typing = damage.**

Ketik perintah Linux secepatnya + Enter untuk menyerang benteng musuh.
Makin cepat dan akurat, damage makin besar. Salah ketik = diserang balik.

Sekaligus game edukasi: melatih kecepatan mengetik + hafal perintah Linux.

## Jalankan

```bash
python3 main.py
# atau
python3 -m textack
```

Butuh hanya Python 3 standar, tanpa install tambahan. Jalan native di Linux terminal.

### Install biar tinggal ketik `textack` (Linux)

```bash
uv tool install -e .
# lalu dari mana aja:
textack
```

Alternatif klasik:

```bash
pip install -e .
textack
```

### Windows — bisa, dengan 1 tambahan

Game ini pakai `curses`. Di Linux/macOS sudah bawaan Python.
Di Windows butuh `windows-curses` (otomatis ke-install via pip):

```powershell
pip install -e .
textack
# atau: pip install -e .[windows]  (sama aja, eksplisit)
```

Catatan Windows:
- Jalankan di Windows Terminal / PowerShell / CMD (bukan IDE output panel).
- Suara `.wav` diputar via PowerShell `System.Media.SoundPlayer`, kalau tidak ada file = diam (tidak crash).
- Save data di `%LOCALAPPDATA%\textack\best.txt`, config waifu di `%APPDATA%\textack\waifu.txt`.
- Di Linux tetap: `~/.cache/textack/best.txt` dan `~/.config/textack/waifu.txt`.

## Dev

```bash
pip install -e .[dev]
python3 -m pytest -q
python3 -m ruff check textack tests
```

CI (`.github/workflows/ci.yml`) jalan di Python 3.9–3.13: pytest + ruff + compileall.
Struktur kode: `textack/core/` (logika murni) → `textack/ui/` (curses) → `textack/infra/` (storage/suara/art).
Detail: `docs/ARCHITECTURE.md`.

## Cara main
- Kata target muncul, misal `sudo apt update`
- Ketik persis sama + Enter
- Combo beruntun = critical damage
- Salah ketik = diserang balik. Diam kelamaan = dicicil musuh.
- Tiap kena = XP. Naik level = pilih 1 dari 3 upgrade (14 macam):
  ATTACK / DEFENSE / SPEED / BASE ala Survivor.io.
- Musuh per wave: SCOUT → RAIDER → GOLEM → OVERLORD, tiap 5 wave BOSS.
- Operator waifu AIKA di panel kanan (terminal ≥102 kolom).
  Ganti art: edit `waifu.txt` atau `~/.config/textack/waifu.txt`.
- Suara: `sfx/*.wav` via paplay/aplay/mpv (fallback beep, F3 on/off) — taruh file `.wav` sesukamu di `sfx/` (hilang = diam, tidak crash).
- `:q` untuk keluar

## Contribute

Mau nambah kata, upgrade, atau musuh? <10 baris saja —
lihat `CONTRIBUTING.md` (quickstart 5 menit) dan
`docs/adding-content.md` (3 resep copy-paste).
Arsitektur singkat: `docs/ARCHITECTURE.md`.
Good first issues: kata baru, rebalance musuh, upgrade baru.

## Roadmap
1. [x] MVP single-player vs benteng (ini)
2. [ ] Skor + leaderboard lokal
3. [ ] Co-op / PvP online via websocket
4. [ ] Engine C opsional kalau butuh performa

## Lisensi
GPL-3.0-or-later. Lihat `LICENSE`. Bebas dipakai, diubah, disebar.
