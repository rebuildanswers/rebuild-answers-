"""Generate the 1200x630 Open Graph card. Re-run after a rename."""
from PIL import Image, ImageDraw, ImageFont
import sys, pathlib

NAME  = sys.argv[1] if len(sys.argv) > 1 else "Rebuild Answers"
DOM   = sys.argv[2] if len(sys.argv) > 2 else "rebuildanswers.com"
OUT   = sys.argv[3] if len(sys.argv) > 3 else "og.png"

BG, INK, INK2, ACCENT, LINE = "#121110", "#f2efe8", "#b8b3a8", "#e08a54", "#2c2a26"
W, H = 1200, 630

S = "/System/Library/Fonts/Supplemental/"
def f(name, size):
    for p in (S + name, "/System/Library/Fonts/" + name):
        try: return ImageFont.truetype(p, size)
        except OSError: continue
    return ImageFont.load_default()

bold  = f("Arial Bold.ttf", 66)
bold2 = f("Arial Bold.ttf", 30)
reg   = f("Arial.ttf", 29)
mono  = f("Courier New Bold.ttf", 22)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# accent rule down the left edge
d.rectangle([0, 0, 10, H], fill=ACCENT)

M = 82
# wordmark
d.text((M, 62), NAME.split()[0], font=bold2, fill=INK)
wm = d.textlength(NAME.split()[0], font=bold2)
if len(NAME.split()) > 1:
    d.text((M + wm + 9, 62), " ".join(NAME.split()[1:]), font=bold2, fill=ACCENT)

d.line([(M, 118), (W - M, 118)], fill=LINE, width=1)

# headline
d.text((M, 168), "Everyone scores", font=bold, fill=INK)
d.text((M, 244), "your HTML.", font=bold, fill=INK)
d.text((M, 320), "We ask the engines.", font=bold, fill=ACCENT)

# supporting line
d.text((M, 430), "We run your buyers' real questions through live AI", font=reg, fill=INK2)
d.text((M, 468), "answer engines and write down what came back.", font=reg, fill=INK2)

# footer strip
d.line([(M, 536), (W - M, 536)], fill=LINE, width=1)
d.text((M, 562), DOM, font=mono, fill=INK2)
tag = "GENERATIVE ENGINE OPTIMIZATION"
d.text((W - M - d.textlength(tag, font=mono), 562), tag, font=mono, fill=ACCENT)

img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  {img.size[0]}x{img.size[1]}  {pathlib.Path(OUT).stat().st_size//1024}KB")
