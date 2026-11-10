#!/usr/bin/env python3
"""reel1: сборка по words.json + plan.md.
python3 -I build.py <reel_dir> [--sheet] [--out name]"""
import json, subprocess, sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

R = sys.argv[1]
SHEET = "--sheet" in sys.argv
OUTNAME = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "reel1_v1.mp4"
SRC = os.path.join(R, "src.mov")
W, H, FPS = 1080, 1920, 30

# ---------- шрифты ----------
FD = "/usr/share/fonts/opentype/inter/"
def F(name, s): return ImageFont.truetype(FD + name + ".otf", s)
TITLE = lambda s: F("InterDisplay-Black", s)       # плотный гротеск
ACCENT = lambda s: F("InterDisplay-LightItalic", s)  # акцент (замена рукописного)
UI = lambda s: F("Inter-SemiBold", s)
SMALL = lambda s: F("Inter-Medium", s)

CREAM = (243, 235, 221)
INK = (30, 26, 22)
ACC = (150, 104, 70)       # тёплый акцент на креме
MUTED = (120, 110, 98)

# ---------- монтаж: сегменты исходника ----------
SEGS = [(0.00, 2.71), (2.97, 5.52), (5.84, 13.55), (13.83, 18.95)]
starts, acc = [], 0.0
for a, b in SEGS: starts.append(acc); acc += b - a
DUR = acc
NF = int(round(DUR * FPS))

def src_time(t):
    for (a, b), s in zip(SEGS, starts):
        if t < s + (b - a) - 1e-9: return a + (t - s)
    return SEGS[-1][1]

def to_out(ts):
    """время исходника -> время ролика (в вырезанном куске — к началу след. сегмента)."""
    for (a, b), s in zip(SEGS, starts):
        if ts < a: return s
        if ts <= b: return s + ts - a
    return DUR

# ---------- камера ----------
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def zoom_at(t):
    if t < starts[1]: return 1.0
    if t < starts[2]: return 1.08
    if t < starts[3]:
        return 1.0 + 0.06 * ease((t - 10.20) / (starts[3] - 10.20))
    if t < 15.24: return 1.08
    return 1.0 + 0.0 * t
ANCHOR = (540, 560)  # лицо

# ---------- рисование ----------
def text_w(text, font, track):
    return font.getlength(text) + track * font.size * max(0, len(text) - 1)

def draw_t(d, xy, text, font, fill, track=-0.03):
    x, y = xy
    for i, ch in enumerate(text):
        d.text((x + font.getlength(text[:i]) + track * font.size * i, y), ch, font=font, fill=fill)

def plate(w, h, r=32, alpha=238):
    """кремовое стекло + контур + мягкая тень. Возвращает RGBA с полями 40px."""
    m = 40
    im = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((m, m + 10, m + w, m + h + 10), r, fill=(40, 30, 20, 70))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((m, m, m + w, m + h), r, fill=CREAM + (alpha,), outline=(255, 255, 255, 230), width=2)
    return im, m

def two_line(main, accent, fm=84, fa=96, pad=(56, 34), gap=6):
    mf, af = TITLE(fm), ACCENT(fa)
    mw, aw = text_w(main, mf, -0.03), text_w(accent, af, -0.01)
    w = int(max(mw, aw) + 2 * pad[0]); lh1, lh2 = int(fm * 1.12), int(fa * 1.15)
    h = int(lh1 + gap + lh2 + 2 * pad[1])
    im, m = plate(w, h)
    d = ImageDraw.Draw(im)
    draw_t(d, (m + (w - mw) / 2, m + pad[1] - fm * 0.08), main, mf, INK)
    draw_t(d, (m + (w - aw) / 2, m + pad[1] + lh1 + gap - fa * 0.12), accent, af, ACC, -0.01)
    return im, m

def chip(text):
    f = UI(44); tw = text_w(text, f, -0.01)
    w, h = int(tw + 40 + 66), 80
    im, m = plate(w, h, r=36)
    d = ImageDraw.Draw(im)
    d.ellipse((m + 32, m + 34, m + 46, m + 48), fill=ACC)
    draw_t(d, (m + 66, m + 14), text, f, INK, -0.01)
    return im, m

def post_card():
    w, h = 780, 230
    im, m = plate(w, h)
    d = ImageDraw.Draw(im)
    d.ellipse((m + 40, m + 36, m + 96, m + 92), fill=(205, 194, 178))
    draw_t(d, (m + 116, m + 34), "Пост в Threads", UI(34), INK, -0.01)
    draw_t(d, (m + 116, m + 76), "гневный · только что", SMALL(28), MUTED, 0)
    draw_t(d, (m + 40, m + 118), "«Нас кинули!»", TITLE(80), INK)
    return im, m

def stat_card():
    nf = TITLE(200); a1, a2 = TITLE(64), ACCENT(72)
    nw = text_w("22", nf, -0.03)
    w, h = int(56 + nw + 40 + max(text_w("года", a1, -0.03), text_w("в туризме", a2, 0)) + 56), 240
    im, m = plate(w, h)
    d = ImageDraw.Draw(im)
    draw_t(d, (m + 56, m + h / 2 - 125), "22", nf, INK)
    x = m + 56 + nw + 40
    draw_t(d, (x, m + 44), "года", a1, INK)
    draw_t(d, (x, m + 118), "в туризме", a2, ACC, 0)
    return im, m

# элементы: (img, m, cx, cy_top, t_in, t_out)
EL = []
def add(img_m, cx, y, t_in, t_out, kind="card"):
    img, m = img_m; EL.append(dict(img=img, m=m, cx=cx, y=y, a=t_in, b=t_out, kind=kind))

add(two_line("Купили тур,", "а вас кинули?", 92, 100), 540, 870, 0.00, 2.71, "hook")
add(chip("Threads"), 540, 228, 0.10, 6.10, "chip")
add(post_card(), 540, 1330, 4.18, 6.60)
add(chip("Эксперт в туризме"), 540, 228, 6.22, 10.10, "chip")
add(stat_card(), 540, 1330, 7.80, 10.30)
add(chip("Один вопрос"), 540, 228, 10.20, 15.10, "chip")
Q_IN, Q_OUT = 13.10, 15.20
add(two_line("Где вы их всех", "находите?"), 540, 1110, Q_IN, Q_OUT, "big")
add(chip("Если серьёзно"), 540, 228, 15.24, DUR, "chip")
S_IN = 16.52
add(two_line("Никому нельзя", "доверять"), 540, 1110, S_IN, DUR + 1, "big")
SUB_OFF = [(Q_IN - 0.05, 15.24), (S_IN - 0.05, DUR + 1)]

def el_state(e, t):
    """alpha, dy, scale"""
    if t < e["a"] or t > e["b"] + 0.16: return None
    i = (t - e["a"]) / 0.20; o = (e["b"] + 0.16 - t) / 0.16
    k = ease(min(i, 1)); ko = ease(min(o, 1))
    al = k * ko
    if e["kind"] == "big":
        return al, (1 - k) * 18, 0.94 + 0.06 * k
    return al, (1 - k) * 16, 0.97 + 0.03 * k

def paste(frame, e, t):
    st = el_state(e, t)
    if not st: return
    al, dy, sc = st
    img = e["img"]
    if sc < 0.999:
        img = img.resize((int(img.width * sc), int(img.height * sc)), Image.BICUBIC)
    if al < 0.999:
        a = img.getchannel("A").point(lambda v: int(v * al)); img = img.copy(); img.putalpha(a)
    m = int(e["m"] * sc)
    x = int(e["cx"] - img.width / 2)
    y = int(e["y"] - m + dy + (e["img"].height - img.height) / 2 * 0)
    frame.alpha_composite(img, (max(0, x), max(0, y)))

# ---------- субтитры (Экспертный крем) ----------
words = json.load(open(os.path.join(R, "words.json")))
FIX = {"Трец": "Threads,", "серьезно,": "серьёзно,"}
ws = []
for w in words:
    txt = FIX.get(w["w"], w["w"])
    if txt in ("–", "-", "—") or w["start"] >= SEGS[-1][1]: continue
    ws.append(dict(w=txt, a=to_out(w["start"]), b=to_out(w["end"])))
# склейка «22» + «-летним»
m2 = []
for w in ws:
    if w["w"].startswith("-") and m2: m2[-1]["w"] += w["w"]; m2[-1]["b"] = w["b"]
    else: m2.append(w)
ws = m2
ws = [w for w in ws if not (w["w"] == "всех" and w["a"] > 17)]
LAYOUT = [1, 3, 4, 1, 3, 3, 2, 2, 2, 2, 3, 3, 3, 2, 4, 2, 3, 4, 1, 2]
assert sum(LAYOUT) == len(ws), (sum(LAYOUT), len(ws))
groups, i = [], 0
for n in LAYOUT: groups.append(ws[i:i+n]); i += n
for g in groups: g[-1]["w"] = g[-1]["w"].rstrip(".")
SF = F("Inter-SemiBold", 62)
def sub_layer(frame, t):
    for off in SUB_OFF:
        if off[0] <= t <= off[1]: return
    g = None
    for i, gr in enumerate(groups):
        end = groups[i + 1][0]["a"] if i + 1 < len(groups) else gr[-1]["b"] + 0.4
        end = min(end, gr[-1]["b"] + 0.6)
        if gr[0]["a"] - 0.02 <= t < end: g = gr; break
    if not g: return
    vis = [w for w in g if w["a"] - 0.02 <= t]
    full = " ".join(w["w"] for w in g)
    txt = " ".join(w["w"] for w in vis)
    tw_full = text_w(full, SF, -0.01); tw = text_w(txt, SF, -0.01)
    # плашка растёт к ширине видимого текста
    last = vis[-1]; k = ease((t - last["a"] + 0.02) / 0.12)
    prev = text_w(" ".join(w["w"] for w in vis[:-1]), SF, -0.01) if len(vis) > 1 else 0
    cw = prev + (tw - prev) * k
    pw, ph = int(cw + 64), 96
    d = ImageDraw.Draw(frame)
    x0 = int(540 - pw / 2); y0 = 1200 - ph // 2
    sh = Image.new("RGBA", (pw + 60, ph + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 38, 30 + pw, 38 + ph), 30, fill=(40, 30, 20, 60))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), (x0 - 30, y0 - 30))
    d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), 30, fill=CREAM + (240,), outline=(255, 255, 255, 230), width=2)
    # текст: слова проявляются
    tx = 540 - tw / 2 + (tw - cw) / 2 * 0
    tx = x0 + 32
    for i, w in enumerate(vis):
        a = ease((t - w["a"] + 0.02) / 0.12)
        col = INK + (int(255 * a),)
        draw_t(d, (tx, y0 + 12), w["w"], SF, col, -0.01)
        tx += text_w(w["w"] + " ", SF, -0.01)

# ---------- рендер кадров ----------
def frame_at(src_img, t):
    z = zoom_at(t)
    if z > 1.0005:
        cw, ch = W / z, H / z
        x0 = ANCHOR[0] - ANCHOR[0] / z; y0 = ANCHOR[1] - ANCHOR[1] / z
        src_img = src_img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    fr = src_img.convert("RGBA")
    for e in EL: paste(fr, e, t)
    sub_layer(fr, t)
    return fr.convert("RGB")

def decode():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"scale={W}:{H},fps={FPS}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        yield i, Image.frombuffer("RGB", (W, H), b, "raw", "RGB", 0, 1); i += 1

out_dir = os.path.join(R, "out"); os.makedirs(out_dir, exist_ok=True)

if SHEET:
    ts = list(np.linspace(0.05, DUR - 0.1, 16))
    need = {int(round(src_time(t) * FPS)): t for t in ts}
    thumbs = {}
    for i, im in decode():
        if i in need: thumbs[need[i]] = frame_at(im, need[i]).resize((270, 480))
    sheet = Image.new("RGB", (270 * 8, 480 * 2 + 0), (0, 0, 0))
    dd = ImageDraw.Draw(sheet)
    for k, t in enumerate(sorted(thumbs)):
        sheet.paste(thumbs[t], ((k % 8) * 270, (k // 8) * 480))
        dd.text(((k % 8) * 270 + 6, (k // 8) * 480 + 6), f"{t:.2f}", fill=(255, 0, 0), font=SMALL(22))
    sheet.save(os.path.join(out_dir, "sheet.jpg"), quality=85); print("sheet ok"); sys.exit()

# ---------- аудио ----------
tmp = os.path.join(R, "tmp"); os.makedirs(tmp, exist_ok=True)
fc, labs = [], []
for i, (a, b) in enumerate(SEGS):
    d = b - a
    fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={d-0.012:.3f}:d=0.012[s{i}]")
    labs.append(f"[s{i}]")
fc.append("".join(labs) + f"concat=n={len(SEGS)}:v=0:a=1,aresample=48000,highpass=f=70,"
          "loudnorm=I=-13.3:TP=-1.5:LRA=11[voice]")
SFX = [("pop", 0.05, 0.16), ("whoosh", starts[1] - 0.22, 0.14), ("tick", 4.18, 0.20), ("pop", 5.32, 0.13),
       ("tick", 6.22, 0.18), ("pop", 7.80, 0.15), ("riser", starts[3] - 0.8, 0.10), ("pop", Q_IN, 0.16),
       ("whoosh", 15.24 - 0.22, 0.13), ("pop", S_IN, 0.16)]
ins = ["-i", SRC]
mix = ["[voice]"]
for j, (n, t, v) in enumerate(SFX):
    ins += ["-i", os.path.join(R, "sfx", n + ".wav")]
    ms = int(max(0, t) * 1000)
    fc.append(f"[{j+1}:a]aresample=48000,volume={v},adelay={ms}|{ms},apad[x{j}]"); mix.append(f"[x{j}]")
fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
          f"afade=t=out:st={DUR-0.25:.3f}:d=0.25,alimiter=limit=0.89:level=false,atrim=0:{DUR:.3f}[aout]")
wav = os.path.join(tmp, "audio.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(fc), "-map", "[aout]",
                "-ac", "2", "-ar", "48000", wav], check=True)

# ---------- видео ----------
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
