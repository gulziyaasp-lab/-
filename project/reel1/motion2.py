#!/usr/bin/env python3
"""reel1 v4 — моушн без плашек: кинетическая типографика, рисованные штрихи,
счётчик-барабан, наезды камеры на акцентах. Палитра хаки.
python3 -I motion2.py <reel_dir> [--sheet t1,t2,...] [--out name]"""
import json, subprocess, sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

R = sys.argv[1]
SHEET = "--sheet" in sys.argv
OUTNAME = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "reel1_v4.mp4"
SRC = os.path.join(R, "src.mov")
W, H, FPS = 1080, 1920, 30

FD = "/usr/share/fonts/opentype/inter/"
_fc = {}
def F(name, s):
    k = (name, int(s))
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + name + ".otf", int(s))
    return _fc[k]
BLACK = lambda s: F("InterDisplay-Black", s)

INK = (50, 44, 28)        # тёмно-хаки, основной текст
KHAKI = (102, 86, 52)    # акцент
GLOW = (255, 251, 240)    # кремовый ореол для читаемости

# ---------- монтаж ----------
SEGS = [(0.00, 2.71), (2.97, 5.52), (5.84, 13.55), (13.83, 18.95)]
starts, acc = [], 0.0
for a, b in SEGS: starts.append(acc); acc += b - a
DUR = acc; NF = int(round(DUR * FPS))
def src_time(t):
    for (a, b), s in zip(SEGS, starts):
        if t < s + (b - a) - 1e-9: return a + (t - s)
    return SEGS[-1][1]
def to_out(ts):
    for (a, b), s in zip(SEGS, starts):
        if ts < a: return s
        if ts <= b: return s + ts - a
    return DUR

def clamp(x): return min(1.0, max(0.0, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def out_cubic(x): x = clamp(x); return 1 - (1 - x) ** 3
def out_back(x, s=1.6):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def in_out(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2

# ключевые моменты (время ролика)
T_KINULI = to_out(5.90)
T_22 = to_out(8.38)
T_Q = to_out(13.96)
T_SER = to_out(16.10)
T_NIK = to_out(17.38)

# ---------- камера ----------
PUNCH = [(to_out(4.80), 0.025), (T_KINULI, 0.06), (T_22, 0.04), (to_out(13.12), 0.03),
         (to_out(15.06), 0.05), (T_SER, 0.03), (to_out(18.04), 0.05)]
def zoom_at(t):
    seg = max(i for i, s in enumerate(starts) if t >= s - 1e-9)
    base = [1.0, 1.08, 1.0, 1.08][seg]
    if seg == 2: base = 1.0 + 0.05 * ease((t - 10.20) / (starts[3] - 10.20))
    if seg == 3 and t >= T_SER - 0.05: base = 1.0
    z = base + 0.012 * ease((t - starts[seg]) / 2.5)
    for tp, amp in PUNCH:
        if t >= tp - 0.02:
            u = t - tp
            z += amp * (out_cubic(u / 0.22) if u < 0.22 else math.exp(-(u - 0.22) / 0.9))
    return z
ANCHOR = (540, 560)

# ---------- текст ----------
TR = -0.03
def tw(text, font, track=TR): return font.getlength(text) + track * font.size * max(0, len(text) - 1)
def cap_top(font): return font.getbbox("НЙ")[1]

def glow_composite(frame, lay, pos, alpha=1.0):
    """ореол: размытая альфа текста кремовым + сам текст."""
    if alpha <= 0: return
    a = lay.getchannel("A")
    g = a.filter(ImageFilter.GaussianBlur(6)).point(lambda v: min(255, int(v * 1.4)))
    gl = Image.new("RGBA", lay.size, GLOW + (0,)); gl.putalpha(g.point(lambda v: int(v * 0.6 * alpha)))
    frame.alpha_composite(gl, pos)
    if alpha < 1: lay = lay.copy(); lay.putalpha(a.point(lambda v: int(v * alpha)))
    frame.alpha_composite(lay, pos)

def kin_line(frame, t, x, y, text, size, color, t0, mode="rise", align="c", t_out=None, track=TR):
    """кинетическая строка без подложки. x — центр/левый край, y — верх заглавных.
    mode: rise (буквы по одной снизу), slam (влетает с масштаба), left/right (въезд сбоку)."""
    f = BLACK(size); w = tw(text, f, track); top = cap_top(f); hcap = f.getbbox("Н")[3] - top
    if t < t0: return w, hcap
    o = 1.0 if t_out is None else 1 - clamp((t - t_out) / 0.2)
    if o <= 0: return w, hcap
    pad = int(size * 0.6)
    lay = Image.new("RGBA", (int(w + 2 * pad), int(hcap + size * 0.5 + 2 * pad)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    u = t - t0
    if mode == "rise":
        for i, ch in enumerate(text):
            k = out_cubic((u - i * 0.028) / 0.32)
            if k <= 0: continue
            cx = pad + f.getlength(text[:i]) + track * size * i
            d.text((cx, pad - top + (1 - k) * size * 0.55), ch, font=f, fill=color + (int(255 * k),))
    else:
        d.text((0, 0), "", font=f)
        for i, ch in enumerate(text):
            d.text((pad + f.getlength(text[:i]) + track * size * i, pad - top), ch, font=f, fill=color + (255,))
    ox = x - w / 2 if align == "c" else x
    pos = [ox - pad, y - pad - (1 - o) * 16]
    al = o
    if mode == "slam":
        k = out_back(u / 0.32, 1.3); s = 1.45 - 0.45 * k
        lay = lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))), Image.BICUBIC)
        pos = [ox + w / 2 - lay.width / 2, y + hcap / 2 - lay.height / 2 - (1 - o) * 16]
        al *= clamp(u / 0.1)
    elif mode in ("left", "right"):
        k = out_cubic(u / 0.38); sgn = -1 if mode == "left" else 1
        pos[0] += sgn * (1 - k) * 160; al *= clamp(u / 0.15)
    glow_composite(frame, lay, (int(pos[0]), int(pos[1])), al)
    return w, hcap

# ---------- рисованные штрихи ----------
def path_draw(frame, pts, prog, color, width, alpha=1.0):
    if prog <= 0 or alpha <= 0: return
    pts = np.asarray(pts, float)
    seg = np.hypot(*(pts[1:] - pts[:-1]).T); L = seg.sum(); target = L * clamp(prog)
    out, acc_ = [tuple(pts[0])], 0
    for i, s in enumerate(seg):
        if acc_ + s >= target:
            r = (target - acc_) / s if s else 0; out.append(tuple(pts[i] + (pts[i + 1] - pts[i]) * r)); break
        acc_ += s; out.append(tuple(pts[i + 1]))
    xs, ys = [p[0] for p in out], [p[1] for p in out]
    m = width * 3
    x0, y0 = int(min(xs) - m), int(min(ys) - m)
    lay = Image.new("RGBA", (int(max(xs) - x0 + m), int(max(ys) - y0 + m)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    loc = [(px - x0, py - y0) for px, py in out]
    if len(loc) > 1: d.line(loc, fill=color + (255,), width=width, joint="curve")
    for px, py in (loc[0], loc[-1]):
        d.ellipse((px - width / 2, py - width / 2, px + width / 2, py + width / 2), fill=color + (255,))
    glow_composite(frame, lay, (x0, y0), alpha)

def underline_pts(x0, x1, y, wob=7, seed=0):
    xs = np.linspace(x0, x1, 40)
    return [(x, y + wob * math.sin((x - x0) / (x1 - x0) * math.pi * 2 + seed) * 0.5 - (x - x0) / (x1 - x0) * wob)
            for x in xs]

def ellipse_pts(cx, cy, rx, ry, a0=-2.4, turn=1.12):
    n = 90
    return [(cx + rx * (1 + 0.04 * i / n) * math.cos(a0 + turn * 2 * math.pi * i / n),
             cy + ry * (1 + 0.06 * i / n) * math.sin(a0 + turn * 2 * math.pi * i / n)) for i in range(n + 1)]

def qmark_pts(cx, top, s):
    """знак вопроса одной линией: дуга + хвост."""
    pts = []
    for i in range(40):
        a = math.pi * 1.05 - i / 39 * math.pi * 1.45
        pts.append((cx + s * 0.5 * math.cos(a), top + s * 0.5 - s * 0.5 * math.sin(a)))
    ex, ey = pts[-1]
    for i in range(1, 16):
        k = i / 15
        pts.append((ex + (cx - ex) * k, ey + (top + s * 1.15 - ey) * k))
    return pts

# ---------- сцены ----------
def hook(fr, t):
    to = starts[1] - 0.2
    if t > to + 0.25: return
    kin_line(fr, t, 540, 880, "КУПИЛИ ТУР,", 112, INK, 0.02, "rise", t_out=to)
    w, h = kin_line(fr, t, 540, 1010, "а вас кинули?", 96, KHAKI, 0.38, "rise", t_out=to)
    o = 1 - clamp((t - to) / 0.2)
    path_draw(fr, underline_pts(540 - w / 2, 540 + w / 2, 1010 + h + 26), out_cubic((t - 0.95) / 0.45), KHAKI, 9, o)

def kinuli(fr, t):
    a, b = T_KINULI - 0.03, to_out(6.74) - 0.15
    if t < a or t > b + 0.25: return
    kin_line(fr, t, 540, 1090, "«НАС", 128, INK, a, "slam", t_out=b)
    kin_line(fr, t, 540, 1240, "КИНУЛИ!»", 128, KHAKI, a + 0.16, "slam", t_out=b)
    o = 1 - clamp((t - b) / 0.2)
    # штрихи-«всплеск» вокруг
    for i, (dx, dy, ang) in enumerate([(-330, 1110, -2.5), (330, 1110, -0.6), (-345, 1300, 2.6), (345, 1300, 0.5)]):
        p = out_cubic((t - a - 0.25 - i * 0.03) / 0.25)
        cx, cy = 540 + dx, dy
        x1, y1 = cx + 42 * math.cos(ang), cy + 42 * math.sin(ang)
        path_draw(fr, [(cx, cy), (x1, y1)], p, KHAKI, 9, o)

def odometer(fr, t, x, y, text, size, t0, dur=0.9):
    f = BLACK(size); top = cap_top(f); hcap = f.getbbox("0")[3] - top
    lh = int(hcap * 1.25)
    cw = [f.getlength(c) + TR * size for c in text]
    w = sum(cw) - TR * size
    pad = int(size * 0.35)
    lay = Image.new("RGBA", (int(w + 2 * pad), int(hcap + 2 * pad)), (0, 0, 0, 0))
    cx = pad
    for j, c in enumerate(text):
        target = int(c) + 10 * (len(text) - j)   # старшие крутятся меньше
        v = target * in_out((t - t0 - j * 0.08) / dur)
        dlo = int(math.floor(v)); fr_ = v - dlo
        col = Image.new("RGBA", (int(cw[j] + 20), int(hcap)), (0, 0, 0, 0)); d = ImageDraw.Draw(col)
        for dd, off in ((dlo % 10, -fr_ * lh), ((dlo + 1) % 10, (1 - fr_) * lh)):
            ch = str(dd); gx = (cw[j] - f.getlength(ch)) / 2
            d.text((gx, -top + off), ch, font=f, fill=INK + (255,))
        fm = np.ones(col.height); e = int(col.height * 0.12)
        fm[:e] = np.linspace(0, 1, e); fm[-e:] = np.linspace(1, 0, e)
        ca = (np.array(col.getchannel("A")) * fm[:, None]).astype(np.uint8); col.putalpha(Image.fromarray(ca))
        lay.alpha_composite(col, (int(cx), pad))
        cx += cw[j]
    a = clamp((t - t0) / 0.12)
    glow_composite(fr, lay, (int(x - pad), int(y - pad)), a)
    return w, hcap

def stat(fr, t):
    a, b = T_22 - 0.05, 10.30
    if t < a or t > b + 0.25: return
    o = 1 - clamp((t - b) / 0.2)
    nf = BLACK(300); nw = tw("22", nf); f1, f2 = BLACK(100), BLACK(86)
    lw = max(tw("ГОДА", f1), tw("в туризме", f2))
    gx = 540 - (nw + 34 + lw) / 2; y = 1330 - (1 - o) * 16
    if o >= 1: odometer(fr, t, gx, y, "22", 300, a)
    else:
        lay = Image.new("RGBA", (W, 400), (0, 0, 0, 0)); odometer(lay, t, gx, 60, "22", 300, a)
        fr_al = lay.getchannel("A").point(lambda v: int(v * o)); lay.putalpha(fr_al); fr.alpha_composite(lay, (0, int(y - 60)))
    lx = gx + nw + 34
    kin_line(fr, t, lx, y + 18, "ГОДА", 100, INK, a + 0.35, "left", "l", t_out=b)
    w2, h2 = kin_line(fr, t, lx, y + 150, "в туризме", 86, KHAKI, a + 0.55, "left", "l", t_out=b)
    path_draw(fr, underline_pts(lx, lx + w2, y + 150 + h2 + 24, 6, 1), out_cubic((t - a - 0.95) / 0.4), KHAKI, 8, o)

def qmark(fr, t):
    a, b = to_out(11.68), starts[3] - 0.15
    if t < a or t > b + 0.25: return
    o = 1 - clamp((t - b) / 0.2)
    p = in_out((t - a) / 0.75)
    sway = 6 * math.sin((t - a) * 2.2)
    pts = [(px + sway * 0.3, py + sway) for px, py in qmark_pts(865, 420, 150)]
    path_draw(fr, pts, p, KHAKI, 16, o)
    if p >= 1:
        k = out_back((t - a - 0.75) / 0.25)
        r = 13 * k
        path_draw(fr, [(865 + sway * 0.3 - 0.1, 420 + 150 * 1.42 + sway), (865 + sway * 0.3 + 0.1, 420 + 150 * 1.42 + sway)],
                  1, KHAKI, max(2, int(2 * r)), o)

def question(fr, t):
    if t < T_Q - 0.05 or t > 15.45: return
    to = 15.20
    kin_line(fr, t, 540, 1060, "ГДЕ ВЫ", 120, INK, T_Q - 0.03, "left", t_out=to)
    kin_line(fr, t, 540, 1195, "ИХ ВСЕХ", 120, INK, to_out(14.58) - 0.03, "right", t_out=to)
    t3 = to_out(15.06) - 0.03
    w, h = kin_line(fr, t, 540, 1330, "находите?", 108, KHAKI, t3, "slam", t_out=to)
    o = 1 - clamp((t - to) / 0.2)
    path_draw(fr, ellipse_pts(540, 1330 + h / 2 + 4, w / 2 + 46, h / 2 + 40), in_out((t - t3 - 0.25) / 0.55), KHAKI, 8, o)

def statement(fr, t):
    if t < T_NIK - 0.05: return
    kin_line(fr, t, 540, 1060, "НИКОМУ", 124, INK, T_NIK - 0.03, "rise")
    kin_line(fr, t, 540, 1200, "НЕЛЬЗЯ", 124, INK, to_out(17.80) - 0.03, "rise")
    t3 = to_out(18.04) - 0.03
    w, h = kin_line(fr, t, 540, 1340, "доверять", 112, KHAKI, t3, "slam")
    path_draw(fr, underline_pts(540 - w / 2 - 10, 540 + w / 2 + 10, 1340 + h + 30, 8, 2), out_cubic((t - t3 - 0.25) / 0.4), KHAKI, 10)

# ---------- субтитры: капс без плашки, слова влетают, говоримое — акцентом ----------
words = json.load(open(os.path.join(R, "words.json")))
FIX = {"Трец": "Threads,", "серьезно,": "серьёзно,"}
ws = []
for w in words:
    txt = FIX.get(w["w"], w["w"])
    if txt in ("–", "-", "—") or w["start"] >= SEGS[-1][1]: continue
    ws.append(dict(w=txt, a=to_out(w["start"]), b=to_out(w["end"])))
m2 = []
for w in ws:
    if w["w"].startswith("-") and m2: m2[-1]["w"] += w["w"]; m2[-1]["b"] = w["b"]
    else: m2.append(w)
ws = [w for w in m2 if not (w["w"] == "всех" and w["a"] > 17)]
LAYOUT = [1, 3, 4, 1, 3, 3, 2, 2, 2, 2, 3, 3, 3, 2, 4, 2, 3, 4, 1, 2]
assert sum(LAYOUT) == len(ws)
groups, i = [], 0
for n in LAYOUT: groups.append(ws[i:i + n]); i += n
for g in groups:
    for w in g: w["w"] = w["w"].rstrip(".").upper()
SUB_OFF = [(T_KINULI - 0.06, to_out(6.74) + 0.06), (T_Q - 0.06, 15.30), (T_NIK - 0.06, DUR + 1)]
SUBF = BLACK(70)

def subs(fr, t):
    for a, b in SUB_OFF:
        if a <= t <= b: return
    g, end = None, 0
    for i, gr in enumerate(groups):
        end = groups[i + 1][0]["a"] if i + 1 < len(groups) else gr[-1]["b"] + 0.4
        end = min(end, gr[-1]["b"] + 0.6)
        if gr[0]["a"] - 0.02 <= t < end: g = gr; break
    if not g: return
    SUBF = BLACK(70); sz = 70
    while True:
        sp = SUBF.getlength(" ")
        widths = [tw(w["w"], SUBF) for w in g]
        full = sum(widths) + sp * (len(g) - 1)
        if full <= 840 or sz <= 44: break
        sz -= 2; SUBF = BLACK(sz)
    top = cap_top(SUBF); hcap = SUBF.getbbox("Н")[3] - top
    pad = 40
    lay = Image.new("RGBA", (int(full + 2 * pad), int(hcap + 2 * pad + 30)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = pad
    active = max((w for w in g if w["a"] - 0.02 <= t), key=lambda w: w["a"])
    for j, w in enumerate(g):
        u = t - w["a"] + 0.02
        if u < 0: x += widths[j] + sp; continue
        for ci, ch in enumerate(w["w"]):
            k = out_cubic((u - ci * 0.012) / 0.18)
            if k <= 0: continue
            col = (KHAKI if w is active and len(g) > 1 else INK) + (int(255 * k),)
            d.text((x + SUBF.getlength(w["w"][:ci]) + TR * sz * ci, pad - top + (1 - k) * sz * 0.48), ch, font=SUBF, fill=col)
        x += widths[j] + sp
    o = 1 - clamp((t - (end - 0.08)) / 0.08)
    sy = 1265 if t < starts[1] else 1165
    glow_composite(fr, lay, (int(540 - lay.width / 2), int(sy - pad)), o)

def frame_at(src_img, t):
    z = zoom_at(t)
    if z > 1.0005:
        cw, ch = W / z, H / z
        x0 = ANCHOR[0] - ANCHOR[0] / z; y0 = ANCHOR[1] - ANCHOR[1] / z
        src_img = src_img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    fr = src_img.convert("RGBA")
    hook(fr, t); kinuli(fr, t); stat(fr, t); qmark(fr, t); question(fr, t); statement(fr, t)
    subs(fr, t)
    return fr.convert("RGB")

def decode():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"scale={W}:{H},fps={FPS}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        yield i, Image.frombuffer("RGB", (W, H), b, "raw", "RGB", 0, 1); i += 1
    p.stdout.close(); p.wait()

out_dir = os.path.join(R, "out"); os.makedirs(out_dir, exist_ok=True)

if SHEET:
    arg = sys.argv[sys.argv.index("--sheet") + 1] if len(sys.argv) > sys.argv.index("--sheet") + 1 else ""
    ts = [float(x) for x in arg.split(",")] if "," in arg else list(np.linspace(0.05, DUR - 0.1, 16))
    need = {}
    for t in ts: need.setdefault(int(round(src_time(t) * FPS)), []).append(t)
    thumbs = {}
    for i, im in decode():
        for t in need.get(i, []): thumbs[t] = frame_at(im, t).resize((270, 480))
    cols = 8; rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (270 * cols, 480 * rows)); dd = ImageDraw.Draw(sheet)
    for k, t in enumerate(sorted(thumbs)):
        sheet.paste(thumbs[t], ((k % cols) * 270, (k // cols) * 480))
        dd.text(((k % cols) * 270 + 6, (k // cols) * 480 + 6), f"{t:.2f}", fill=(255, 0, 0), font=BLACK(22))
    sheet.save(os.path.join(out_dir, "sheet_v4.jpg"), quality=85); print("sheet ok"); sys.exit()

# ---------- аудио ----------
tmp = os.path.join(R, "tmp"); os.makedirs(tmp, exist_ok=True)
fc, labs = [], []
for i, (a, b) in enumerate(SEGS):
    d = b - a
    fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={d-0.012:.3f}:d=0.012[s{i}]")
    labs.append(f"[s{i}]")
fc.append("".join(labs) + f"concat=n={len(SEGS)}:v=0:a=1,aresample=48000,highpass=f=70,"
          "loudnorm=I=-13.3:TP=-1.5:LRA=11[voice]")
SFX = [("pop", 0.02, 0.12), ("whoosh", starts[1] - 0.22, 0.12), ("pop", T_KINULI - 0.03, 0.15),
       ("pop", T_KINULI + 0.13, 0.11)]
SFX += [("tick", T_22 - 0.05 + k * 0.09, 0.10) for k in range(8)]
SFX += [("whoosh", to_out(11.68) - 0.05, 0.08), ("riser", starts[3] - 0.8, 0.08),
        ("whoosh", T_Q - 0.15, 0.10), ("whoosh", to_out(14.58) - 0.15, 0.09), ("pop", to_out(15.06), 0.14),
        ("whoosh", T_SER - 0.22, 0.10), ("pop", T_NIK, 0.11), ("pop", to_out(17.80), 0.11),
        ("pop", to_out(18.04), 0.15)]
ins = ["-i", SRC]; mix = ["[voice]"]
for j, (n, t, v) in enumerate(SFX):
    ins += ["-i", os.path.join(R, "sfx", n + ".wav")]
    ms = int(max(0, t) * 1000)
    fc.append(f"[{j+1}:a]aresample=48000,volume={v},adelay={ms}|{ms},apad[x{j}]"); mix.append(f"[x{j}]")
fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
          f"afade=t=out:st={DUR-0.25:.3f}:d=0.25,alimiter=limit=0.89:level=false,atrim=0:{DUR:.3f}[aout]")
wav = os.path.join(tmp, "audio_v4.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(fc), "-map", "[aout]",
                "-ac", "2", "-ar", "48000", wav], check=True)

out = os.path.join(out_dir, OUTNAME)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", wav, "-vf", "noise=alls=3:allf=t,format=yuv420p",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-b:a", "192k",
                        "-ar", "48000", "-t", f"{DUR:.3f}", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
src_iter = decode(); cur_i, cur_im = -1, None
for k in range(NF):
    t = k / FPS
    need = int(round(src_time(t) * FPS))
    while cur_i < need:
        try: cur_i, cur_im = next(src_iter)
        except StopIteration: break
    enc.stdin.write(frame_at(cur_im, t).tobytes())
enc.stdin.close(); enc.wait()
print("OK", out, f"{DUR:.2f}s", NF, "frames")
