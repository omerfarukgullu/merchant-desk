"""Uygulama ikonunu (assets/app_icon.ico) üretir.

Basit, düz renkli bir rozet: köşeleri yuvarlatılmış lacivert kare üzerinde
yükselen üç beyaz çubuk (iş/rapor teması). 16-256px arası çözünürlükler tek
bir .ico dosyasında birleştirilir.

Çalıştırma:
    .venv\\Scripts\\python.exe assets\\generate_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_PATH = Path(__file__).resolve().parent / "app_icon.ico"
CANVAS = 256

BACKGROUND = (42, 65, 110, 255)   # koyu lacivert
BAR_COLOR = (255, 255, 255, 255)  # beyaz


def build_base_image() -> Image.Image:
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 10
    draw.rounded_rectangle(
        [margin, margin, CANVAS - margin, CANVAS - margin],
        radius=48, fill=BACKGROUND,
    )

    # Yükselen üç çubuk (soldan sağa: kısa, orta, uzun).
    bar_width = 34
    gap = 26
    base_y = CANVAS - 64
    heights = [70, 108, 146]
    start_x = 64

    for i, h in enumerate(heights):
        x0 = start_x + i * (bar_width + gap)
        x1 = x0 + bar_width
        y1 = base_y
        y0 = base_y - h
        draw.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=BAR_COLOR)

    return img


def main() -> None:
    img = build_base_image()
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(OUT_PATH, format="ICO", sizes=sizes)
    print(f"Ikon yazildi: {OUT_PATH}")


if __name__ == "__main__":
    main()
