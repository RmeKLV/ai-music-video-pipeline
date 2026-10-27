"""Final delivery step: measure true peak (4x oversampled) and set gain so true peak <= CEIL dBTP (default -1.0,
the YouTube/streaming norm), then report a tonal-balance table (dB per band, relative to 1-2 kHz) for
master vs reference so EQ-matching side effects (e.g. fizz coming back) are visible.
usage: finalize_master.py master.wav reference.wav out.wav [ceil_dbtp=-1.0]"""
import sys, numpy as np, soundfile as sf
from scipy.signal import resample_poly

src, ref, out = sys.argv[1:4]
ceil = float(sys.argv[4]) if len(sys.argv) > 4 else -1.0
x, sr = sf.read(src, always_2d=True)
tp = lambda y: 20 * np.log10(np.abs(resample_poly(y, 4, 1, axis=0)).max() + 1e-12)
before = tp(x)
g = min(1.0, 10 ** ((ceil - before) / 20))
y = x * g
sf.write(out, y, sr, subtype="PCM_24")
print(f"true peak {before:+.2f} dBTP -> {tp(y):+.2f} dBTP (gain {20 * np.log10(g):+.2f} dB)")

BANDS = [(30, 80), (80, 250), (250, 800), (800, 2000), (2000, 5000), (5000, 8000), (8000, 12000), (12000, 16000), (16000, 20000)]
def balance(p):
    z, s = sf.read(p, always_2d=True); m = z.mean(1)
    win = 8192; fr = np.lib.stride_tricks.sliding_window_view(m, win)[::win // 2] * np.hanning(win)
    S = (np.abs(np.fft.rfft(fr, axis=1)) ** 2).mean(0); f = np.fft.rfftfreq(win, 1 / s)
    dens = lambda a, b: S[(f >= a) & (f < b)].mean()
    r = dens(1000, 2000)
    return [10 * np.log10(dens(a, b) / r) for a, b in BANDS]
bm, br = balance(out), balance(ref)
print("band (Hz)        " + " ".join(f"{a//1000 if a>=1000 else a}{'k' if a>=1000 else ''}-{b//1000 if b>=1000 else b}{'k' if b>=1000 else ''}".rjust(9) for a, b in BANDS))
print("master           " + " ".join(f"{v:9.1f}" for v in bm))
print("reference        " + " ".join(f"{v:9.1f}" for v in br))
print("master - ref     " + " ".join(f"{a - b:+9.1f}" for a, b in zip(bm, br)))
