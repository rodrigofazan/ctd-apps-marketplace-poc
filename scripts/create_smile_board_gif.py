from math import cos, pi, sin
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "assets/apps/smile-board-tablet-base.png"
OUTPUT_PATH = ROOT / "assets/apps/smile-board-reviews.gif"

SCREEN_BOX = (140, 116, 1396, 906)
SCREEN_SIZE = (SCREEN_BOX[2] - SCREEN_BOX[0], SCREEN_BOX[3] - SCREEN_BOX[1])
OUTPUT_SIZE = (900, 600)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def ease(value: float) -> float:
    return value * value * (3 - 2 * value)


def star_points(cx: float, cy: float, outer: float, inner: float):
    points = []
    for index in range(10):
        radius = outer if index % 2 == 0 else inner
        angle = -pi / 2 + index * pi / 5
        points.append((cx + cos(angle) * radius, cy + sin(angle) * radius))
    return points


def draw_review_card(review: dict) -> Image.Image:
    card = Image.new("RGBA", (900, 500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((8, 8, 892, 492), radius=38, fill="#ffffff", outline="#dbe4f0", width=3)

    avatar_color = review["avatar"]
    draw.ellipse((62, 62, 158, 158), fill=avatar_color)
    initials_font = font(33, bold=True)
    initials_box = draw.textbbox((0, 0), review["initials"], font=initials_font)
    initials_width = initials_box[2] - initials_box[0]
    initials_height = initials_box[3] - initials_box[1]
    draw.text((110 - initials_width / 2, 110 - initials_height / 2 - 3), review["initials"], font=initials_font, fill="#ffffff")

    draw.text((184, 64), review["name"], font=font(34, bold=True), fill="#172b4d")
    draw.text((184, 111), "Verified patient", font=font(22), fill="#6b7c93")

    start_x = 62
    for index in range(5):
        cx = start_x + index * 58 + 22
        draw.polygon(star_points(cx, 210, 23, 10), fill="#f5b522")
    draw.text((365, 190), "5.0", font=font(28, bold=True), fill="#274f8e")

    quote_font = font(31)
    lines = wrap(review["quote"], width=46)
    y = 270
    for line in lines:
        draw.text((62, y), line, font=quote_font, fill="#344563")
        y += 43

    draw.rounded_rectangle((666, 407, 832, 457), radius=25, fill="#edf4ff")
    draw.text((704, 420), "Review", font=font(20, bold=True), fill="#155eef")
    return card


def draw_screen(slide_offset: float, reviews: list[dict]) -> Image.Image:
    screen = Image.new("RGBA", SCREEN_SIZE, "#f3f6fb")
    draw = ImageDraw.Draw(screen)

    draw.rectangle((0, 0, SCREEN_SIZE[0], 112), fill="#102a4c")
    draw.ellipse((44, 29, 98, 83), fill="#2f6fed")
    draw.text((116, 35), "Smile Board", font=font(34, bold=True), fill="#ffffff")
    draw.text((995, 40), "Patient reviews", font=font(24), fill="#c8d6ed")

    viewport_x, viewport_y = 112, 176
    viewport_w, viewport_h = 1032, 500
    viewport = Image.new("RGBA", (viewport_w, viewport_h), (0, 0, 0, 0))
    card_gap = 70
    card_width = 900
    track_x = -slide_offset * (card_width + card_gap)
    for index, review in enumerate(reviews):
        card = draw_review_card(review)
        viewport.alpha_composite(card, (round(track_x + index * (card_width + card_gap)), 0))
    screen.alpha_composite(viewport, (viewport_x, viewport_y))

    dot_y = 724
    for index in range(2):
        selected = abs(slide_offset - index) < 0.5
        color = "#155eef" if selected else "#b8c6db"
        radius = 9 if selected else 7
        cx = SCREEN_SIZE[0] / 2 - 18 + index * 36
        draw.ellipse((cx - radius, dot_y - radius, cx + radius, dot_y + radius), fill=color)
    return screen


def slide_position(frame: int) -> float:
    if frame < 14:
        return 0.0
    if frame < 24:
        return ease((frame - 14) / 9)
    if frame < 38:
        return 1.0
    return 1.0 - ease((frame - 38) / 9)


def gif_palette_frame(frame: Image.Image) -> Image.Image:
    """Reserve palette index 255 for transparent pixels in every GIF frame."""
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    palette_frame = rgba.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    palette = palette_frame.getpalette()[: 255 * 3] + [0, 0, 0]
    palette_frame.putpalette(palette)
    pixels = bytearray(palette_frame.tobytes())
    for index, opacity in enumerate(alpha.tobytes()):
        if opacity < 48:
            pixels[index] = 255
    palette_frame.frombytes(bytes(pixels))
    palette_frame.info["transparency"] = 255
    palette_frame.info["disposal"] = 2
    return palette_frame


def build_gif():
    base = Image.open(BASE_PATH).convert("RGBA")
    reviews = [
        {
            "name": "Sarah M.",
            "initials": "SM",
            "avatar": "#4169a8",
            "quote": "The team made me feel welcome from the moment I arrived.",
        },
        {
            "name": "Michael R.",
            "initials": "MR",
            "avatar": "#2f7d73",
            "quote": "Clear explanations, a smooth visit, and wonderful care.",
        },
    ]

    frames = []
    for frame_index in range(48):
        frame = base.copy()
        screen = draw_screen(slide_position(frame_index), reviews)
        frame.alpha_composite(screen, (SCREEN_BOX[0], SCREEN_BOX[1]))
        frame = frame.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
        frames.append(frame)

    gif_frames = [gif_palette_frame(frame) for frame in frames]
    gif_frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=gif_frames[1:],
        duration=85,
        loop=0,
        disposal=2,
        optimize=True,
        transparency=255,
    )

    with Image.open(OUTPUT_PATH) as result:
        print(f"created {OUTPUT_PATH.relative_to(ROOT)}: {result.size}, {result.n_frames} frames")


if __name__ == "__main__":
    build_gif()
