"""Generates installer/gravewait.ico: a pixel gravestone under a crescent moon.
Run once (needs Pillow); the .ico is committed so CI doesn't need to redo it."""
import os

from PIL import Image

PAL = {
    ".": (0, 0, 0, 0),
    "B": (16, 12, 30, 255),     # night sky
    "b": (30, 22, 52, 255),     # horizon glow
    "M": (238, 230, 208, 255),  # moon
    "S": (128, 122, 140, 255),  # stone
    "s": (88, 82, 102, 255),    # stone shade
    "G": (52, 96, 50, 255),     # grass
    "g": (36, 68, 38, 255),     # grass dark
    "O": (217, 119, 87, 255),   # ember accent
}

ART = """\
BBBBBBBBBBBBBBBB
BBBBBBBBBBBMMBBB
BBBBBBBBBBMMMMBB
BBBBBBBBBBMMMMBB
BBBBBBBBBBBMMBBB
BBBSSSSBBBBBBBBB
BBSSSSSSBBBBBBBB
BBSsSSsSBBBBBBBB
BBSSSSSSBBBBBBBB
BBSsOOsSBBBBBBBB
BBSSSSSSBBbbbbBB
BBSSSSSSbbbbbbbb
BGgGSSGgGgGGgGGB
GGGGGGGGGGGGGGGG
gGgGGgGGGgGGGgGg
gggggggggggggggg
"""


def main():
    rows = [r for r in ART.splitlines() if r]
    base = Image.new("RGBA", (16, 16))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            base.putpixel((x, y), PAL[ch])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "gravewait.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [base.resize((s, s), Image.NEAREST) for s in sizes]
    imgs[-1].save(out, format="ICO",
                  append_images=imgs[:-1],
                  sizes=[(s, s) for s in sizes])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
