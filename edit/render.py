#!/usr/bin/env python3
"""Монтаж вертикального ролика по брендбуку (positioning_and_style.md).
python3 render.py config.json out.mp4"""
import json, subprocess, sys, os, math, wave, struct, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
BLUE, NAVY, SKY, ORANGE, WHITE = (30,136,229), (13,35,74), (125,200,255), (255,170,30), (255,255,255)
FD = "/usr/share/fonts/opentype/inter/"
F = lambda w, s: ImageFont.truetype(FD + f"Inter-{w}.otf", s)

cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
tmp = tempfile.mkdtemp(prefix="reel_")
T0 = cfg["trim_start"]
dur_src = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",cfg["source"]]))
D = dur_src - T0                      # длина основной части
EC = cfg["end_card"]["duration"]
rt = lambda t: max(0.0, t - T0)       # время исходника -> время ролика

def words_line(d, x, y, words, font, accents, fill=WHITE, stroke=None):
    for i, w in enumerate(words):
        clean = w.strip(".,!?—:;«»")
        col = ORANGE if clean in accents else fill
        d.text((x, y), w, font=font, fill=col, stroke_width=stroke[0] if stroke else 0, stroke_fill=stroke[1] if stroke else None)
        x += d.textlength(w + " ", font=font)

def canvas(): return Image.new("RGBA", (W, H), (0,0,0,0))

def hook_png(path):
    h = cfg["hook"]; im = canvas(); d = ImageDraw.Draw(im)
    font = F("Black", 92); lines = h["text"].split("\n")
    widths = [d.textlength(l, font=font) for l in lines]; lh = 112
    bw, bh = max(widths) + 90, lh*len(lines) + 70; bx, by = (W-bw)//2, 220
    sh = Image.new("RGBA", (W, H), (0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle((bx, by+12, bx+bw, by+bh+12), 36, fill=(0,0,0,110))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d.rounded_rectangle((bx, by, bx+bw, by+bh), 36, fill=BLUE+(245,))
    # плашка рубрики
    rf = F("ExtraBold", 38); r = cfg["rubric"]; rw = d.textlength(r, font=rf)
    d.rounded_rectangle(((W-rw)//2-28, by-34, (W+rw)//2+28, by+30), 30, fill=ORANGE)
    d.text(((W-rw)//2, by-25), r, font=rf, fill=NAVY)
    for i, l in enumerate(lines):
        words_line(d, (W-widths[i])/2, by+42+i*lh, l.split(" "), font, h["accent"])
    im.save(path)

def name_png(path):
    a = cfg["agent"]; im = canvas(); d = ImageDraw.Draw(im)
    nf, rf = F("ExtraBold", 50), F("Bold", 36)
    w = max(d.textlength(a["name"], font=nf), d.textlength(a["role"].upper(), font=rf)) + 70
    x, y = 60, 1150
    d.rounded_rectangle((x, y, x+w, y+150), 26, fill=WHITE+(240,))
    d.rectangle((x, y+20, x+10, y+130), fill=ORANGE)
    d.text((x+38, y+20), a["name"], font=nf, fill=NAVY)
    d.text((x+38, y+86), a["role"].upper(), font=rf, fill=BLUE)
    im.save(path)

def sub_png(path, s):
    im = canvas(); d = ImageDraw.Draw(im); font = F("Black", 84)
    words = s["text"].split(" "); lines, cur = [], []
    for w in words:
        if cur and d.textlength(" ".join(cur+[w]), font=font) > W-160: lines.append(cur); cur = []
        cur.append(w)
    lines.append(cur)
    y = 1430
    for l in lines:
        lw = d.textlength(" ".join(l), font=font)
        words_line(d, (W-lw)/2, y, l, font, s.get("accent", []), stroke=(10, NAVY))
        y += 104
    im.save(path)

def cta_png(path):
    c = cfg["cta"]; im = canvas(); d = ImageDraw.Draw(im); font = F("ExtraBold", 58)
    lines = c["text"].split("\n"); lw = max(d.textlength(l, font=font) for l in lines)
    bw, bh = lw+150, 74*len(lines)+56; bx, by = (W-bw)//2, 300
    d.rounded_rectangle((bx, by, bx+bw, by+bh), 32, fill=ORANGE+(250,))
    # иконка «закладка»
    ix, iy = bx+38, by+bh//2-30
    d.polygon([(ix,iy),(ix+44,iy),(ix+44,iy+60),(ix+22,iy+44),(ix,iy+60)], fill=NAVY)
    for i, l in enumerate(lines): d.text((bx+110, by+28+i*74), l, font=font, fill=NAVY)
    im.save(path)

def endcard_png(path):
    e = cfg["end_card"]; im = Image.new("RGB", (W, H), BLUE); d = ImageDraw.Draw(im)
    for i in range(H):  # градиент небо
        k = i/H; d.line((0,i,W,i), fill=tuple(int(SKY[j]*(1-k)+BLUE[j]*k*0.8+NAVY[j]*k*0.2) for j in range(3)))
    # самолётик + пунктирная траектория
    cx, cy = W//2, 760
    for t in range(0, 360, 12):
        a = math.radians(t); x = cx-330+t*1.6; y = cy+40*math.sin(a)
        d.ellipse((x-5,y-5,x+5,y+5), fill=WHITE)
    px, py = cx+270, cy-10
    d.polygon([(px+70,py),(px-50,py-14),(px-50,py+14)], fill=ORANGE)
    d.polygon([(px+10,py),(px-30,py-60),(px-45,py-60),(px-20,py)], fill=ORANGE)
    d.polygon([(px+10,py),(px-30,py+60),(px-45,py+60),(px-20,py)], fill=ORANGE)
    hf, tf = F("Black", 104), F("Bold", 50)
    hw = d.textlength(e["handle"], font=hf); d.text(((W-hw)/2, 900), e["handle"], font=hf, fill=WHITE)
    tw = d.textlength(e["tagline"], font=tf); d.text(((W-tw)/2, 1050), e["tagline"], font=tf, fill=NAVY)
    im.save(path)

def ding(path, sr=48000):
    """Фирменный «дзинь» как сигнал «пристегните ремни»: два тона."""
    n = int(sr*1.4); data = []
    for i in range(n):
        t = i/sr; v = 0
        for st, f in ((0.0, 1046.5), (0.32, 783.99)):
            if t >= st:
                tt = t-st; v += 0.32*math.exp(-tt*4.2)*(math.sin(2*math.pi*f*tt)+0.3*math.sin(2*math.pi*f*2*tt))
        data.append(int(max(-1,min(1,v))*32767))
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(struct.pack(f"<{n}h", *data))

P = lambda n: os.path.join(tmp, n)
hook_png(P("hook.png")); name_png(P("name.png")); cta_png(P("cta.png")); endcard_png(P("end.png")); ding(P("ding.wav"))
subs = []
for i, s in enumerate(cfg["subtitles"]):
    sub_png(P(f"sub{i}.png"), s); subs.append((P(f"sub{i}.png"), rt(s["start"]), rt(s["end"])))

# «смена плана» каждые N секунд: чередование кадрирования (жёсткие склейки-зумы)
Z, step = cfg["zooms"], cfg["zoom_every"]; segs = []; t = 0; k = 0
while t < D - 1e-3:
    e = min(D, t+step); segs.append((t, e, Z[k % len(Z)])); t, k = e, k+1
parts = []
for i, (a, b, z) in enumerate(segs):
    cw, ch = int(W/z)//2*2, int(H/z)//2*2
    parts.append(f"[base]trim={a}:{b},setpts=PTS-STARTPTS,crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})*0.3,scale={W}:{H}:flags=lanczos[s{i}]")
split = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,eq=saturation=1.08:contrast=1.04,split={len(segs)}" + "".join(f"[b{i}]" for i in range(len(segs)))
parts = [p.replace("[base]", f"[b{i}]") for i, p in enumerate(parts)]
fc = [split] + parts + ["".join(f"[s{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[v0]"]

inputs = ["-ss", str(T0), "-i", cfg["source"]]
ov = [(P("hook.png"), 0, rt(cfg["hook"]["end"])+0 if cfg["hook"]["end"] > T0 else cfg["hook"]["end"]),
      (P("name.png"), cfg["agent"]["start"], cfg["agent"]["end"]),
      (P("cta.png"), rt(cfg["cta"]["start"]), D)] + subs
# время хука/имени задаётся уже во времени ролика
ov[0] = (P("hook.png"), 0, cfg["hook"]["end"])
cur = "v0"
for j, (png, a, b) in enumerate(ov):
    inputs += ["-loop", "1", "-t", str(D), "-i", png]
    idx = j+1
    fc.append(f"[{idx}:v]format=rgba,fade=in:st={a}:d=0.12:alpha=1[o{j}]")
    fc.append(f"[{cur}][o{j}]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{j+1}]"); cur = f"v{j+1}"
ei = len(ov)+1; di = ei+1
inputs += ["-loop", "1", "-t", str(EC), "-i", P("end.png"), "-i", P("ding.wav")]
fc.append(f"[{ei}:v]fps=30,format=yuv420p,setsar=1,settb=1/30[end]")
fc.append(f"[{cur}]fps=30,format=yuv420p,setsar=1,settb=1/30[main]")
fc.append(f"[main][end]xfade=transition=slideup:duration=0.25:offset={D-0.25:.3f}[vout]")
# звук: чистка + громкость, хвост под заставку, «дзинь» в начале и на заставке
fc.append(f"[0:a]highpass=f=80,afftdn=nr=10,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000,afade=out:st={D-0.3:.3f}:d=0.3,apad=pad_dur={EC}[voice]")
fc.append(f"[{di}:a]asplit=2[d1][d2]")
fc.append(f"[d1]volume=0.35,adelay=0|0[da]")
fc.append(f"[d2]volume=0.45,adelay={int((D-0.2)*1000)}|{int((D-0.2)*1000)}[db]")
fc.append(f"[voice][da][db]amix=inputs=3:normalize=0:duration=first[aout]")

cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
       "-t", str(D - 0.25 + EC), "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
print("OK", out, f"{D-0.25+EC:.2f}s")
