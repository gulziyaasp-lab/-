#!/usr/bin/env python3
"""reel1 v3 — моушн-версия. Типографика по референсу «3 горнолыжных курорта»
(стопка капса, большая цифра слева, финальное слово строчными), палитра беж/хаки.
python3 -I motion.py <reel_dir> [--sheet] [--out name]"""
import json, subprocess, sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

R = sys.argv[1]
SHEET = "--sheet" in sys.argv
OUTNAME = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "reel1_v3.mp4"
SRC = os.path.join(R, "src.mov")
W, H, FPS = 1080, 1920, 30

FD = "/usr/share/fonts/opentype/inter/"
_fc = {}
def F(name, s):
    k = (name, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + name + ".otf", s)
    return _fc[k]
BLACK = lambda s: F("InterDisplay-Black", s)
XB = lambda s: F("InterDisplay-ExtraBold", s)
UI = lambda s: F("Inter-SemiBold", s)

# палитра (беж/хаки из референса, хаки чуть темнее — ради читаемости)
KHAKI = (112, 101, 74)
BEIGE = (235, 224, 200)
CREAM = (255, 250, 238)
DARK = (74, 66, 46)

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
def out_back(x, s=1.5):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1

# камера: склейки прикрыты зумом + медленный дрейф внутри планов
def zoom_at(t):
    seg = max(i for i, s in enumerate(starts) if t >= s - 1e-9)
    base = [1.0, 1.08, 1.0, 1.08][seg]
    if seg == 2: base = 1.0 + 0.06 * ease((t - 10.20) / (starts[3] - 10.20))
    if seg == 3 and t >= 15.24: base = 1.0
    drift = 0.015 * ease((t - starts[seg]) / 2.5)
    return base + drift
ANCHOR = (540, 560)

# ---------- типографика ----------
TR = -0.03
def tw(text, font, track=TR): return font.getlength(text) + track * font.size * max(0, len(text) - 1)
def draw_t(d, xy, text, font, fill, track=TR):
    x, y = xy
    for i, ch in enumerate(text):
        d.text((x + font.getlength(text[:i]) + track * font.size * i, y), ch, font=font, fill=fill)

def text_box(font):
    asc, desc = font.getmetrics()
    top = font.getbbox("НЙ")[1]
    return top, asc  # верх заглавной, базовая линия

STY = {"k": (KHAKI, CREAM), "b": (BEIGE, DARK)}

def label(frame, x, y, text, size, style, p, align="c", font=None, track=TR):
    """Плашка-строка. p: 0..1 — шторка плашки + выезд текста снизу.
    x — центр (align c) или левый край (align l). y — верх плашки. Возвращает (w, h)."""
    font = font or BLACK(size)
    bg, fg = STY[style]
    top, base = text_box(font)
    padx, pady = int(size * 0.30), int(size * 0.20)
    w = int(tw(text, font, track) + 2 * padx); h = int(base - top + 2 * pady)
    if p <= 0: return w, h
    x0 = int(x - w / 2) if align == "c" else int(x)
    pw = max(2, int(w * out_cubic(p / 0.55)))
    ox = (w - pw) // 2 if align == "c" else 0
    lay = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20 + ox, 28, 20 + ox + pw, 28 + h), int(h * 0.28), fill=(40, 32, 18, 80))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((ox, 0, ox + pw - 1, h - 1), int(h * 0.28), fill=bg + (246,))
    # текст выезжает снизу внутри плашки (маска = плашка)
    q = out_cubic((p - 0.08) / 0.55)
    txt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_t(ImageDraw.Draw(txt), (padx, pady - top + (1 - q) * h * 0.8), text, font, fg + (int(255 * q),), track)
    mask = box.getchannel("A")
    txt.putalpha(Image.fromarray(np.minimum(np.array(txt.getchannel("A")), np.array(mask))))
    box.alpha_composite(txt)
    lay.alpha_composite(box, (20, 20))
    fade = clamp(p * 6)
    if fade < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * fade)))
    frame.alpha_composite(lay, (x0 - 20, y - 20))
    return w, h

def stack(frame, t, x, y, lines, align="c", gap=10, t_out=None):
    """lines: [(text, size, style, t_in)] — строки стопкой, каждая со своим временем."""
    out = 1.0 if t_out is None else 1 - clamp((t - t_out) / 0.18)
    if out <= 0: return
    cy = y
    for text, size, style, t_in in lines:
        p = clamp((t - t_in) / 0.38) * out if out < 1 else clamp((t - t_in) / 0.38)
        lift = int((1 - out) * 20)
        w, h = label(frame, x, cy - lift, text, size, style, p, align)
        cy += h + gap

def icon_btn(frame, x, y, s, kind, p):
    """квадратная хаки-кнопка с белым значком (как на скрине)."""
    if p <= 0: return
    sc = 0.6 + 0.4 * out_back(p)
    ss = int(s * sc)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, s - 1, s - 1), int(s * 0.3), fill=KHAKI + (246,))
    c, k = s / 2, s * 0.22; wl = max(3, int(s * 0.06))
    if kind == "arrow":
        d.line((c - k, c + k, c + k, c - k), fill=CREAM, width=wl)
        d.line((c - k * 0.2, c - k, c + k, c - k, c + k, c + k * 0.2), fill=CREAM, width=wl, joint="curve")
    elif kind == "dots":
        for dx in (-k, 0, k): d.ellipse((c + dx - wl, c - wl, c + dx + wl, c + wl), fill=CREAM)
    else:
        f = BLACK(int(s * 0.5)); gw = f.getlength(kind); tb = f.getbbox(kind)
        d.text((c - gw / 2, c - (tb[1] + tb[3]) / 2), kind, font=f, fill=CREAM)
    im = im.resize((ss, ss), Image.BICUBIC)
    a = clamp(p * 4)
    if a < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(x + (s - ss) / 2), int(y + (s - ss) / 2)))

def chip(frame, t, kind, text, a, b):
    """верхний чип: кнопка-значок + бежевая плашка капсом."""
    if t < a or t > b + 0.2: return
    p = clamp((t - a) / 0.4); o = 1 - clamp((t - b) / 0.2)
    if o <= 0: return
    p = p * o
    f = BLACK(46); s = 84
    w = tw(text, f) + 2 * 12 + s + 12
    x0 = int(540 - w / 2); y0 = 232 - int((1 - out_cubic(p)) * 30)
    icon_btn(frame, x0, y0, s, kind, p)
    label(frame, x0 + s + 12, y0 + 7, text, 46, "b", clamp((p - 0.15) / 0.85), "l")

# ---------- сцены ----------
def hook(frame, t):
    if t > starts[1] + 0.2: return
    stack(frame, t, 540, 860, [("КУПИЛИ ТУР,", 96, "k", 0.02), ("а вас кинули?", 88, "b", 0.30)],
          t_out=starts[1] - 0.18)

def post_card(frame, t):
    a, b, hit = 4.18, 6.55, 5.32
    if t < a or t > b + 0.25: return
    pin = out_back((t - a) / 0.45, 1.2); po = 1 - out_cubic((t - b) / 0.25)
    w, h = 800, 250
    x = int(140 + (1 - pin) * 700 - (1 - po) * 0) ; y = 1335 + int((1 - po) * 30)
    lay = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + w, 40 + h), 40, fill=(40, 32, 18, 90))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((30, 30, 30 + w, 30 + h), 40, fill=BEIGE + (248,))
    d.ellipse((66, 64, 66 + 64, 64 + 64), fill=KHAKI)
    draw_t(d, (150, 66), "THREADS · ПОСТ", BLACK(34), KHAKI, -0.01)
    draw_t(d, (150, 106), "только что", UI(28), (140, 128, 100), 0)
    if t < hit - 0.05:  # печатает…
        for i in range(3):
            ph = (t * 3 + i * 0.33) % 1
            r = 9 + 4 * math.sin(ph * math.pi)
            cx = 90 + i * 40
            d.ellipse((cx - r, 30 + 190 - r, cx + r, 30 + 190 + r), fill=KHAKI + (200,))
    else:
        q = out_back((t - hit + 0.05) / 0.3, 2.0)
        f = BLACK(int(84 * (0.85 + 0.15 * q)))
        draw_t(d, (66, 30 + 140 + (1 - q) * 20), "«НАС КИНУЛИ!»", f, DARK + (int(255 * clamp(q * 2)),))
    a_ = clamp(pin * 3) * po
    if a_ < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a_)))
    frame.alpha_composite(lay, (x - 30, y - 30))

def stat(frame, t):
    a, b = 7.80, 10.25
    if t < a or t > b + 0.2: return
    o = 1 - clamp((t - b) / 0.2)
    p = clamp((t - a) / 0.35)
    n = int(round(22 * out_cubic((t - a) / 0.7)))
    nf = BLACK(280)
    y = 1290 + int((1 - out_cubic(p)) * 40) + int((1 - o) * 20)
    lay = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    top, base = text_box(nf)
    num = f"{n}"
    lw = max(label(None, 0, 0, "ГОДА", 84, "k", 0)[0], label(None, 0, 0, "в туризме", 72, "b", 0)[0])
    nx = int(540 - (tw("22", nf) + 26 + lw) / 2)
    # цифра — кремовая с хаки-обводкой, читается и на футболке, и на ноутбуке
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    draw_t(ImageDraw.Draw(sh), (nx, 20 - top + 10), num, nf, (40, 32, 18, 120))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    for dx, dy in [(-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)]:
        draw_t(d, (nx + dx, 20 - top + dy), num, nf, KHAKI)
    draw_t(d, (nx, 20 - top), num, nf, CREAM)
    a_ = clamp(p * 3) * o
    if a_ < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a_)))
    frame.alpha_composite(lay, (0, y))
    lx = nx + tw("22", nf) + 26
    stack(frame, t, lx, y + 40, [("ГОДА", 84, "k", a + 0.25), ("в туризме", 72, "b", a + 0.45)],
          align="l", gap=12, t_out=b)

Q_IN, S_IN = 13.10, 16.52
def question(frame, t):
    if t < Q_IN or t > 15.45: return
    stack(frame, t, 540, 1080, [("ГДЕ ВЫ", 104, "k", Q_IN), ("ИХ ВСЕХ", 104, "k", to_out(14.58)),
                                ("находите?", 96, "b", to_out(15.06))], gap=12, t_out=15.22)

def statement(frame, t):
    if t < S_IN: return
    stack(frame, t, 540, 1080, [("НИКОМУ", 104, "k", S_IN), ("НЕЛЬЗЯ", 104, "k", to_out(17.80)),
                                ("доверять", 96, "b", to_out(18.04))], gap=12)

# ---------- субтитры: капс на хаки, слово за словом ----------
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
SUB_OFF = [(Q_IN - 0.05, 15.30), (S_IN - 0.05, DUR + 1)]
SUBF = BLACK(66)

def subs(frame, t):
    for a, b in SUB_OFF:
        if a <= t <= b: return
    g = None
    for i, gr in enumerate(groups):
        end = groups[i + 1][0]["a"] if i + 1 < len(groups) else gr[-1]["b"] + 0.4
        end = min(end, gr[-1]["b"] + 0.6)
        if gr[0]["a"] - 0.02 <= t < end: g = gr; break
    if not g: return
    vis = [w for w in g if w["a"] - 0.02 <= t]
    sp = SUBF.getlength(" ")
    widths = [tw(w["w"], SUBF) for w in vis]
    last_k = out_cubic((t - vis[-1]["a"] + 0.02) / 0.14)
    full_w = sum(widths) + sp * (len(vis) - 1)
    prev_w = full_w - widths[-1] - (sp if len(vis) > 1 else 0)
    cw = prev_w + (full_w - prev_w) * last_k
    top, base = text_box(SUBF)
    padx, pady = 26, 16
    bw, bh = int(cw + 2 * padx), int(base - top + 2 * pady)
    gk = out_back((t - g[0]["a"] + 0.02) / 0.22, 1.6)  # «pop» группы
    x0 = int(540 - bw / 2); y0 = 1190 - bh // 2
    lay = Image.new("RGBA", (bw + 40, bh + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 28, 20 + bw, 28 + bh), int(bh * 0.28), fill=(40, 32, 18, 80))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((20, 20, 20 + bw, 20 + bh), int(bh * 0.28), fill=KHAKI + (246,))
    x = 20 + padx
    for j, w in enumerate(vis):
        k = out_cubic((t - w["a"] + 0.02) / 0.14)
        col = (BEIGE if j == len(vis) - 1 and len(vis) > 1 else CREAM) + (int(255 * k),)
        draw_t(d, (x, 20 + pady - top + (1 - k) * 22), w["w"], SUBF, col)
        x += widths[j] + sp
    sc = 0.9 + 0.1 * gk
    if sc < 0.999:
        lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.BICUBIC)
    frame.alpha_composite(lay, (int(540 - lay.width / 2), int(y0 - 20 + (bh + 40) * (1 - sc) / 2)))

CHIPS = [("dots", "THREADS", 0.10, 6.05), ("arrow", "ЭКСПЕРТ В ТУРИЗМЕ", 6.22, 10.05),
         ("?", "ОДИН ВОПРОС", 10.20, 15.05), ("!", "ЕСЛИ СЕРЬЁЗНО", 15.24, DUR + 1)]

def frame_at(src_img, t):
    z = zoom_at(t)
    if z > 1.0005:
        cw, ch = W / z, H / z
        x0 = ANCHOR[0] - ANCHOR[0] / z; y0 = ANCHOR[1] - ANCHOR[1] / z
        src_img = src_img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    fr = src_img.convert("RGBA")
    for c in CHIPS: chip(fr, t, *c)
    hook(fr, t); post_card(fr, t); stat(fr, t); question(fr, t); statement(fr, t)
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
    ts = [float(x) for x in sys.argv[sys.argv.index("--sheet") + 1].split(",")] \
        if len(sys.argv) > sys.argv.index("--sheet") + 1 and "," in sys.argv[sys.argv.index("--sheet") + 1] \
        else list(np.linspace(0.05, DUR - 0.1, 16))
    need = {}
    for t in ts: need.setdefault(int(round(src_time(t) * FPS)), []).append(t)
    thumbs = {}
    for i, im in decode():
        for t in need.get(i, []): thumbs[t] = frame_at(im, t).resize((270, 480))
    cols = 8; rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (270 * cols, 480 * rows)); dd = ImageDraw.Draw(sheet)
    for k, t in enumerate(sorted(thumbs)):
        sheet.paste(thumbs[t], ((k % cols) * 270, (k // cols) * 480))
        dd.text(((k % cols) * 270 + 6, (k // cols) * 480 + 6), f"{t:.2f}", fill=(255, 0, 0), font=UI(22))
    sheet.save(os.path.join(out_dir, "sheet_v3.jpg"), quality=85); print("sheet ok"); sys.exit()

# ---------- аудио ----------
tmp = os.path.join(R, "tmp"); os.makedirs(tmp, exist_ok=True)
fc, labs = [], []
for i, (a, b) in enumerate(SEGS):
    d = b - a
    fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={d-0.012:.3f}:d=0.012[s{i}]")
    labs.append(f"[s{i}]")
fc.append("".join(labs) + f"concat=n={len(SEGS)}:v=0:a=1,aresample=48000,highpass=f=70,"
          "loudnorm=I=-13.3:TP=-1.5:LRA=11[voice]")
SFX = [("pop", 0.02, 0.14), ("pop", 0.30, 0.10), ("whoosh", starts[1] - 0.22, 0.13),
       ("whoosh", 4.18 - 0.1, 0.11), ("pop", 5.27, 0.14), ("tick", 6.22, 0.16),
       ("tick", 7.80, 0.14), ("pop", 8.10, 0.12), ("riser", starts[3] - 0.8, 0.09),
       ("pop", Q_IN, 0.14), ("pop", to_out(14.58), 0.10), ("pop", to_out(15.06), 0.12),
       ("whoosh", 15.24 - 0.22, 0.12), ("pop", S_IN, 0.14), ("pop", to_out(17.80), 0.10),
       ("pop", to_out(18.04), 0.12)]
ins = ["-i", SRC]; mix = ["[voice]"]
for j, (n, t, v) in enumerate(SFX):
    ins += ["-i", os.path.join(R, "sfx", n + ".wav")]
    ms = int(max(0, t) * 1000)
    fc.append(f"[{j+1}:a]aresample=48000,volume={v},adelay={ms}|{ms},apad[x{j}]"); mix.append(f"[x{j}]")
fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
          f"afade=t=out:st={DUR-0.25:.3f}:d=0.25,alimiter=limit=0.89:level=false,atrim=0:{DUR:.3f}[aout]")
wav = os.path.join(tmp, "audio_v3.wav")
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
