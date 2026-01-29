import os, datetime, textwrap, re, requests
from PIL import Image, ImageDraw, ImageFont

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# --- Choose verses (curated rotation; easiest + stable) ---
VERSES = [
    "Psalm 23:1",
    "Proverbs 3:5-6",
    "Matthew 6:33",
    "Romans 8:28",
    "2 Timothy 1:7",
]
def today_ref():
    return VERSES[datetime.date.today().toordinal() % len(VERSES)]

# --- Verse text source (low friction): BibleGateway “text-only” endpoint via a simple fetch
# NOTE: If you later want, we can swap this to official NLT API key-based access.
def fetch_passage_text(reference: str) -> str:
    # BibleGateway has an HTML page; we fetch and strip tags.
    url = "https://www.biblegateway.com/passage/"
    params = {"search": reference, "version": "NLT"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    html = r.text

    # Pull passage text area roughly; fallback to stripping.
    # (Kept simple for reliability.)
    text = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s{3,}", " ", text)
    # Keep it readable
    return text.strip()

def render_image(reference: str, verse: str, background="backgrounds/smoke.png", out="verse.png"):
    img = Image.open(background).convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # Fonts (GitHub runner has DejaVuSans)
    try:
        big = ImageFont.truetype("DejaVuSans.ttf", 54)
        mid = ImageFont.truetype("DejaVuSans.ttf", 38)
        small = ImageFont.truetype("DejaVuSans.ttf", 22)
    except:
        big = mid = small = ImageFont.load_default()

    # Trim verse to a reasonable length (avoid giant chunks)
    # If BibleGateway strip returns too much, we just take a portion.
    verse = verse[:600].strip()

    # Wrap
    lines = textwrap.wrap(verse, width=34)
    verse_wrapped = "\n".join(lines[:10])

    def shadow_text(x,y,t,f):
        draw.text((x+2,y+2), t, font=f, fill=(0,0,0,160))
        draw.text((x,y), t, font=f, fill=(255,255,255,235))

    bbox = draw.multiline_textbbox((0,0), verse_wrapped, font=big, spacing=10)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x = (W - tw)//2
    y = (H - th)//2 - 60
    shadow_text(x, y, verse_wrapped, big)

    ref = f"{reference} (NLT)"
    rb = draw.textbbox((0,0), ref, font=mid)
    rx = (W - (rb[2]-rb[0]))//2
    shadow_text(rx, y+th+35, ref, mid)

    slogan = "Faith. Focus. Finish."
    sb = draw.textbbox((0,0), slogan, font=small)
    sx = (W - (sb[2]-sb[0]))//2
    shadow_text(sx, H-70, slogan, small)

    footer = "Scripture taken from the Holy Bible, New Living Translation (NLT), © Tyndale House Foundation."
    draw.text((40, H-35), footer, font=small, fill=(255,255,255,200))

    img.save(out, "PNG")
    return out

def post_to_discord(reference: str, image_path: str):
    caption = f"📖 **Scripture of the Day** — **{reference} (NLT)**\nWhat word/phrase stands out today? Drop your takeaway or an **Amen**. 🙏"
    with open(image_path, "rb") as f:
        files = {"file": ("verse.png", f, "image/png")}
        payload = {"content": caption}
        r = requests.post(DISCORD_WEBHOOK_URL, data={"payload_json": requests.utils.json.dumps(payload)}, files=files, timeout=30)
        r.raise_for_status()

def main():
    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL secret")
    ref = today_ref()
    verse_text = fetch_passage_text(ref)
    img = render_image(ref, verse_text)
    post_to_discord(ref, img)

if __name__ == "__main__":
    main()
