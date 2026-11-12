"""App icon in the AI Music Splitter style: indigo -> violet -> pink glossy
squircle with a white play triangle and a download arrow."""
from PIL import Image, ImageDraw, ImageFilter

S = 1024
inset, radius = 40, 250

# diagonal brand gradient
stops = [(91, 91, 247), (139, 92, 246), (255, 77, 157)]
grad = Image.new("RGBA", (S, S))
px = grad.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * (S - 1))
        a, b, u = (stops[0], stops[1], t * 2) if t < 0.5 else (stops[1], stops[2], (t - 0.5) * 2)
        px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)) + (255,)

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([inset, inset, S - inset, S - inset], radius=radius, fill=255)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
img.paste(grad, (0, 0), mask)

# soft top gloss: vertical alpha fade, clipped to the squircle
gl = Image.new("L", (S, S), 0)
gp = gl.load()
for y in range(S):
    a = max(0.0, 1 - y / (S * 0.5)) ** 1.6 * 85
    for x in range(S):
        gp[x, y] = int(a)
gloss = Image.new("RGBA", (S, S), (255, 255, 255, 0))
gloss.putalpha(Image.composite(gl, Image.new("L", (S, S), 0), mask))
img = Image.alpha_composite(img, gloss)

# glyph: plain polygons, then rounded by blur + threshold
g = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(g)
d.polygon([(420, 250), (420, 570), (712, 410)], fill=255)
cx = 512
d.rectangle([cx - 52, 650, cx + 52, 790], fill=255)
d.polygon([(cx - 165, 770), (cx + 165, 770), (cx, 925)], fill=255)
g = g.filter(ImageFilter.GaussianBlur(16)).point(lambda v: 255 if v > 120 else 0).filter(ImageFilter.GaussianBlur(1.2))
glyph = Image.new("RGBA", (S, S), (255, 255, 255, 0))
glyph.putalpha(g)

shadow = glyph.filter(ImageFilter.GaussianBlur(18))
shadow = Image.composite(Image.new("RGBA", (S, S), (40, 10, 90, 150)), Image.new("RGBA", (S, S), (0, 0, 0, 0)), shadow.split()[3])
shadow = shadow.transform(shadow.size, Image.AFFINE, (1, 0, 0, 0, 1, -14))
img = Image.alpha_composite(img, shadow)
img = Image.alpha_composite(img, glyph)

img.save("icon_combo.png")
img.save("app_icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save("app_icon.icns")
