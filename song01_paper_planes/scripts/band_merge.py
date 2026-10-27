"""Merge two versions of the same stem by frequency: LOW from one file, HIGH from another, linear-phase FIR
crossover (complementary, so a file merged with itself is unchanged). Checks and fixes time offset first.
Use: take a restorer's clean body (e.g. Smule below 3 kHz) without its HF hallucinations / blurred consonants.
usage: band_merge.py low_src.flac high_src.flac out.flac [crossover_hz=3000]"""
import sys, numpy as np, soundfile as sf
from scipy.signal import firwin, fftconvolve, correlate

lo_p, hi_p, out = sys.argv[1:4]
xo = float(sys.argv[4]) if len(sys.argv) > 4 else 3000.0
a, sr = sf.read(lo_p, always_2d=True); b, sr2 = sf.read(hi_p, always_2d=True)
assert sr == sr2
n = min(len(a), len(b)); a, b = a[:n], b[:n]
# time alignment on 20 s of mono, +-50 ms search
seg = slice(sr * 30, sr * 50)
c = correlate(a[seg].mean(1), b[seg].mean(1), mode="full", method="fft")
mid = len(c) // 2; w = int(0.05 * sr)
lag = int(np.argmax(c[mid - w: mid + w + 1]) - w)
if lag:
    a = np.roll(a, -lag, axis=0)
# level match low source to high source in the crossover region (least squares on the full signal)
g = np.sum(a * b) / np.sum(a * a)
a = a * g
taps = firwin(2049, xo, fs=sr)                      # linear-phase low-pass
delay = (len(taps) - 1) // 2
lp = lambda x: np.stack([fftconvolve(x[:, ch], taps)[delay: delay + n] for ch in range(x.shape[1])], 1)
y = lp(a) + (b - lp(b))                             # low of a + complementary high of b
sf.write(out, y, sr, subtype="PCM_24")
print(f"{out}: lag {lag} samples, low gain {g:.3f}, crossover {xo:.0f} Hz, peak {np.abs(y).max():.2f}")
