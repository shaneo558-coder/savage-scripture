import os
import datetime
import textwrap
import re
import requests
from PIL import Image, ImageDraw, ImageFont

NLT_API_KEY = os.getenv("NLT_API_KEY", "").strip()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

BACKGROUND_PATH = "backgrounds/smoke.png"
OUTPUT_PATH = "verse.png"

# Curated rotation (edit these anytime)
VERSES = [
    "Psalm 23:1",
    "Proverbs 3:5-6",
    "Matthew 6:33",
    "Romans 8:28",
    "2 Timothy 1:7",
]

def today_ref() -> str:
    return VERSES[datetime.date.today().toordinal() % len(VERSES)]

def fetch_nlt_passage(reference: str) -> str:
    """
    NLT API is HTTP GET with query params including key=... and returns HTML by default.
    Docs: https://api.nlt.to/documentation
    """
    if not NLT_API_KEY:
        raise RuntimeError("Missing NLT_API_KEY")

    url = "https://api.nlt.to/api/passages"
    params = {"key": NLT_API_KEY, "ref": reference}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    html = r.text
    html = html.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def render_verse_image(reference: str, verse_text: str):
    img = Image.open(BACKGROUND_PATH).convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # Fonts available on GitHub runner
    try:
        font_big = ImageFont.truetype("DejaVuSans.ttf", 54)
        font_ref = ImageFont.truetype("DejaVuSans.ttf", 38)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 22)
    except Exception:
        font_big = font_ref = font_small = ImageFont.load_default()

    # Clean + wrap
    verse_text = verse_text.strip()
    wrap_width = 34 if W >= 1080 else 28
    lines = textwrap.wrap(verse_text, width=wrap_width)
    verse_wrapped = "\n".join(lines[:10])  # keep it readable on one image

    def shadowed_text(x, y, text, font):
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 160))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 235))

    # Center verse
    bbox = draw.multiline_textbbox((0, 0), verse_wrapped, font=font_big, spacing=10)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2
    y = (H - th) // 2 - 60
    shadowed_text(x, y, verse_wrapped, font_big)

    # Reference
    ref = f"{reference} (NLT)"
    rb = draw.textbbox((0, 0), ref, font=font_ref)
    rx = (W - (rb[2] - rb[0])) // 2
    shadowed_text(rx, y + th + 35, ref, font_ref)

    # Slogan
    slogan = "Faith. Focus. Finish."
    sb = draw.textbbox((0, 0), slogan, font=font_small)
    sx = (W - (sb[2] - sb[0])) // 2
    shadowed_text(sx, H - 70, slogan, font_small)

    # Copyright footer (small)
    footer = "Scripture taken from the Holy Bible, New Living Translation (NLT), © Tyndale House Foundation."
    draw.text((40, H - 35), footer, font=font_small, fill=(255, 255, 255, 200))

    img.save(OUTPUT_PATH, "PNG")

def post_to_discord(reference: str):
    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL")

    caption = (
        f"📖 **Scripture of the Day** — **{reference} (NLT)**\n"
        f"What word/phrase stands out today? Drop your takeaway or an **Amen**. 🙏"
    )

    with open(OUTPUT_PATH, "rb") as f:
        files = {"file": ("verse.png", f, "image/png")}
        payload = {"content": caption}
        r = requests.post(
            DISCORD_WEBHOOK_URL,
            data={"payload_json": requests.utils.json.dumps(payload)},
            files=files,
            timeout=30,
        )
        r.raise_for_status()

def main():
    ref = today_ref()
    verse = fetch_nlt_passage(ref)
    render_verse_image(ref, verse)
    post_to_discord(ref)

if __name__ == "__main__":
    main()
