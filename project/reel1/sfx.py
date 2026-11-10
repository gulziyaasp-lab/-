"""Синтез SFX в numpy: pop, tick, whoosh, riser. 48 кГц моно wav."""
import numpy as np, wave, sys, os
SR = 48000
def save(p, x):
    x = np.clip(x, -1, 1); w = wave.open(p, "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype("<i2").tobytes()); w.close()
def t(d): return np.arange(int(SR * d)) / SR
def pop():
    tt = t(0.09); f = 900 * np.exp(-tt * 30) + 250
    return 0.6 * np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt * 45)
def tick():
    tt = t(0.04); rng = np.random.default_rng(1)
    return 0.4 * (np.sin(2*np.pi*3200*tt) + 0.3*rng.standard_normal(tt.size)) * np.exp(-tt * 160)
def whoosh(d=0.45):
    tt = t(d); rng = np.random.default_rng(2); n = rng.standard_normal(tt.size)
    # полосовой шум со сдвигом частоты: простая IIR одной точкой с меняющимся коэф.
    y = np.zeros_like(n); a = np.linspace(0.97, 0.80, tt.size); s = 0
    for i in range(n.size): s = a[i]*s + (1-a[i])*n[i]; y[i] = s
    y = y - np.convolve(y, np.ones(40)/40, "same")
    env = np.sin(np.pi * tt / d) ** 2
    return 0.9 * y / (np.abs(y).max()+1e-9) * env
def riser(d=0.8):
    tt = t(d); rng = np.random.default_rng(3); n = rng.standard_normal(tt.size)
    tone = np.sin(2*np.pi*np.cumsum(np.linspace(300, 900, tt.size))/SR)
    env = (tt/d) ** 2 * np.exp(-np.maximum(0, tt-d+0.08)*40)
    return 0.25 * (tone + 0.15*n) * env
if __name__ == "__main__":
    o = sys.argv[1]; os.makedirs(o, exist_ok=True)
    for name, fn in [("pop", pop), ("tick", tick), ("whoosh", whoosh), ("riser", riser)]: save(f"{o}/{name}.wav", fn())
    print("sfx ok")
