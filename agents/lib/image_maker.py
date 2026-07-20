import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lib.config import DRAFTS_DIR
from lib.logger import get_logger

log = get_logger("image_maker")

# Brand tokens (master plan section 2.1)
SAFFRON = "#E8590C"
INDIGO = "#1E2A4A"
IVORY = "#FBF7F0"
WHITE = "#FFFFFF"

PILLAR_ACCENT = {
    "News": SAFFRON,
    "Sarkari": INDIGO,
    "Travel": "#0F766E",
    "Tools": "#C9962E",
    "Gyaan": INDIGO,
    "Paisa": "#0F766E",
}


def make_branded_card(headline: str, pillar: str, slug: str) -> Path:
    """A8 Image Maker fallback: branded template card with pillar color + headline
    text, generated with Pillow — no external API needed, always available.
    Real AI-image / Pexels integration plugs in here in Phase 2 (image_brief -> API call).
    """
    width, height = 1200, 675
    accent = PILLAR_ACCENT.get(pillar, SAFFRON)

    img = Image.new("RGB", (width, height), IVORY)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width, 14], fill=accent)
    draw.rectangle([0, height - 90, width, height], fill=INDIGO)

    try:
        font_headline = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 56)
        font_footer = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    except OSError:
        font_headline = ImageFont.load_default()
        font_footer = ImageFont.load_default()

    wrapped = textwrap.wrap(headline, width=28)[:4]
    y = 140
    for line in wrapped:
        draw.text((80, y), line, font=font_headline, fill=INDIGO)
        y += 70

    draw.text((80, height - 62), f"BharatAo · {pillar}", font=font_footer, fill=WHITE)

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DRAFTS_DIR / f"{slug}.png"
    img.save(out_path, "PNG")  # WebP conversion happens at publish time (perf budget, section 2.6)
    log.info("Generated fallback branded image: %s", out_path)
    return out_path
