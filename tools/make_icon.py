"""Генерация иконки VoiceM (чёрно-зелёная)."""
from pathlib import Path

from PIL import Image, ImageDraw

BLACK = (5, 10, 7, 255)
GREEN = (43, 224, 122, 255)
GREEN_DIM = (27, 154, 85, 255)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

SIZE = 512
image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=110, fill=BLACK, outline=GREEN_DIM, width=8)

# микрофон
draw.rounded_rectangle([206, 96, 306, 288], radius=50, fill=GREEN)
draw.arc([166, 196, 346, 356], start=0, end=180, fill=GREEN_DIM, width=22)
draw.rounded_rectangle([246, 340, 266, 396], radius=10, fill=GREEN_DIM)
draw.rounded_rectangle([196, 396, 316, 416], radius=10, fill=GREEN_DIM)

# волна
heights = [26, 52, 84, 52, 26]
for index, height in enumerate(heights):
    x = 96 + index * 20
    if index >= 2:
        x = 356 + (index - 2) * 20
    draw.rounded_rectangle([x, 240 - height // 2, x + 10, 240 + height // 2], radius=5, fill=GREEN_DIM)

image.save(ASSETS / "icon.png")
image.save(
    ASSETS / "icon.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("icon written to", ASSETS)
