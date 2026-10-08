# Custom waifu art — pakai gambarmu sendiri

Game membaca art sebagai **teks biasa**, jadi gambar apapun harus
dikonversi dulu ke ASCII/karakter. Spec:

- File teks `.txt`, maksimal **34 kolom × 24 baris** (lebih = dipotong otomatis)
- Baris `#` di paling atas = komen/header, diabaikan. Tapi `#` di tengah
  art = piksel gelap, **ikut tampil** (aman dipakai)
- Encoding UTF-8 (boleh pakai karakter `♡ ✿ ⌖ ─` dsb)
- Art tampil penuh di terminal **lebar (≥102 kolom)**. Makin besar
  terminal = makin besar art yang muat. Terminal kekecilan (< 80×24)
  otomatis pause + muncul panduan zoom (lihat bawah).

## Cara 0: web (paling gampang, tanpa install)

Buka **text-image.com/convert/ascii.html** → upload foto →
atur **Image width 30–34 characters** → convert → copy hasilnya
ke `~/.config/textack/waifus/aika.txt` (tambah baris `# artku` di atas).

Tips biar jelas: crop wajah/dada dulu sebelum upload, nyalakan
opsi *Extra contrast*, dan pilih foto kontras tinggi (manga B&W
paling bersih). Jujur: di 30-an kolom, yang kebaca = bentuk +
arsiran, bukan detail foto. Itu batas wajar ASCII art.

## Mode HD: wajah berwarna (disarankan!)

ASCII satu warna memang mentok. Game mendukung **wajah berwarna
(half-block `▄`)** — 2× lebih tajam, jalan di **semua terminal**
(Linux, Windows Terminal, dll) **tanpa install apa-apa**:

- File: `~/.config/textack/waifus/<id>.rgb.txt`
  (Windows: `%APPDATA%\textack\waifus\<id>.rgb.txt`)
- Format: baris 1 = `LEBAR TINGGI` (mis. `48 48`), lalu TINGGI baris
  hex RGB tanpa spasi (`ff0000` = merah). Game otomatis menyesuaikan
  ukuran + palet 16 warna ke terminalmu. Kalau gagal = balik ke ASCII.

## Mode FOTO ASLI (terminal modern)

Punya Ghostty / WezTerm / kitty? Game bisa menampilkan **foto
beneran** di panel (protokol gambar kitty, terverifikasi probe —
bukan tebak-tebakan):

```bash
# 1. cek terminalmu lolos apa tidak (di terminal beneran, bukan IDE):
textack --gfx-test
# 2. kalau "resolved: kitty", taruh foto:
cp fotomu.png ~/.config/textack/waifus/aika.png   # .png/.jpg/.webp oke
# 3. main seperti biasa — foto tampil di menu + samping game
```

- Butuh Pillow sekali: `pip install textack[hd]`
  (Linux tool install: sudah termasuk otomatis). Tanpa Pillow,
  hanya `.png` mentah yang bisa ditampilkan.
- Paksa mode: `textack --gfx=kitty|half|ascii` atau `TEXTACK_GFX=...`
- Terminal lain (Konsole, GNOME Terminal, Alacritty) otomatis
  pakai half-block — game tetap jalan, tetap berwarna.

Bikin `.rgb.txt` dari foto (butuh Pillow sekali saja):

```bash
pip install pillow
python3 - <<'EOF'
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
src = Image.open("foto.png").convert("RGB")
W, H = src.size
# crop wajah: sesuaikan 0.xx dengan fotomu (kiri, atas, kanan, bawah)
crop = src.crop((int(W*0.33), int(H*0.21), int(W*0.67), int(H*0.45)))
g = crop.filter(ImageFilter.GaussianBlur(1))
g = ImageEnhance.Contrast(ImageOps.autocontrast(g, cutoff=2)).enhance(1.15)
g = g.resize((48, 48), Image.LANCZOS)
px = g.load()
rows = ["".join(f"{px[x, y][0]:02x}{px[x, y][1]:02x}{px[x, y][2]:02x}" for x in range(48)) for y in range(48)]
out = Path.home() / ".config" / "textack" / "waifus" / "aika.rgb.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("48 48\n" + "\n".join(rows) + "\n")
print("saved:", out)
EOF
```

## Lokasi file

| Waifu | Path custom |
|---|---|
| AIKA | `~/.config/textack/waifus/aika.txt` (Windows: `%APPDATA%\textack\waifus\aika.txt`) |
| RIN | `.../waifus/rin.txt` |
| SORA | `.../waifus/sora.txt` |

Legacy `waifu.txt` / `~/.config/textack/waifu.txt` masih dibaca
sebagai override AIKA. Tanpa file custom = art bawaan.

## Cara 1: `jp2a` (cepat, tanpa coding)

```bash
sudo pacman -S jp2a   # atau: sudo apt install jp2a
jp2a --width=30 --colors foto.png > ~/.config/textack/waifus/aika.txt
```

Tips: foto portrait + background polos hasilnya paling bersih.
Kecilkan dulu ke ~200px kalau art-nya terlalu ramai.

## Cara 2: `chafa` (berwarna, bagus di terminal modern)

```bash
chafa --symbols block --width 30 foto.png
# kalau cocok, simpan:
chafa --symbols block --width 30 foto.png > ~/.config/textack/waifus/aika.txt
```

## Cara 3: Python + Pillow (kontrol penuh)

```bash
pip install pillow
python3 - <<'EOF'
from pathlib import Path
from PIL import Image
img = Image.open("foto.png").convert("L").resize((30, 14))
chars = " .:-=+*#%@"
px = img.load()
lines = ["".join(chars[px[x, y] * len(chars) // 256] for x in range(30)) for y in range(14)]
out = Path.home() / ".config" / "textack" / "waifus" / "aika.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("# custom aika\n" + "\n".join(lines) + "\n")
print("saved:", out)
EOF
```

## Cek hasil

Jalankan `textack` di terminal **≥102 kolom** — panel kanan
menampilkan art barumu. Kalau rusak/lebih lebar, game otomatis
memotong (tidak crash).

## Layar kekecilan? (sensor ukuran terminal)

Game butuh minimal **80×24**. Kalau jendela lebih kecil, game
**pause otomatis** + layar gelap + pesan:

```text
!! JENDELA TERLALU KECIL !!
butuh >= 80x24  kini 60x15
gedein jendela, atau zoom out:
  Shift + -  (font kecil)
```

- **Gedein jendela**: drag / maximize — art waifu ikut lega
- **Zoom out `Shift + -`**: font mengecil → kolom muat lebih banyak
  (art 34 kolom butuh zoom cukup jauh di jendela kecil)
- **Balikin: `Shift + +`** · keluar: `q`

## Yang perlu di-download (ringkas)

| Buat apa | Download | Wajib? |
|---|---|---|
| Main + wajah berwarna | — (bawaan game, stdlib only) | — |
| Foto langsung (.jpg/.webp) | `pip install textack[hd]` (= Pillow) | opsional |
| Foto ASLI di panel | Ghostty / WezTerm / kitty + cek `textack --gfx-test` | opsional |
| Convert/preview ASCII | `chafa` (`sudo pacman -S chafa`) | opsional |

Kenapa tidak langsung foto asli? Protokol gambar (kitty/sixel)
cuma jalan di terminal tertentu (Konsole bisa sixel, GNOME Terminal
tidak, Alacritty tidak). Half-block berwarna jalan di **mana saja**
termasuk Windows — makanya game pakai itu biar stabil ekspansi.

## Matriks kompatibilitas (dijamin per terminal)

| Terminal | Foto asli | Wajah warna | ASCII | Suara | Keterangan |
|---|---|---|---|---|---|
| kitty / Ghostty / WezTerm | ✅ | ✅ | ✅ | ✅ | semua fitur, verifikasi `textack --gfx-test` |
| Konsole / foot / contour | ➖ | ✅ | ✅ | ✅ | sixel belum dipakai game (nanti); half-block penuh |
| GNOME Terminal / VTE | ➖ | ✅ | ✅ | ✅ | half-block penuh |
| Alacritty | ➖ | ✅ | ✅ | ✅ | half-block penuh |
| Windows Terminal | ➖ | ✅ | ✅ | ✅ | via `windows-curses` + PowerShell audio |
| CMD / conhost lawas | ➖ | ⚠️ | ✅ | ✅ | warna turun ke 16, ASCII selalu aman |
| Dumb / IDE panel | ➖ | ➖ | ➖ | ➖ | pesan ramah, disuruh buka terminal asli |

Prinsip: **tidak ada terminal yang crash** — fitur terbaik yang
didukung yang tampil, sisanya fallback otomatis. Paksa manual:
`textack --gfx=kitty|half|ascii`.
