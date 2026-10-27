"""Rebalance a song from its vocal + instrumental stems so the lyrics cut through ('instruments blend together,
can't hear the lyrics'). Pro mixing move: vocal gain + sidechain-style dynamic EQ that dips the instrumental's
intelligibility band (1-5 kHz) only while the voice is singing, in proportion to how loud the voice is there.
usage: unmask_mix.py vocals instrumental out.wav [vocal_db=2] [dip_db=0] [lo=1000] [hi=5000]"""
import sys
import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import istft, stft

vp, ip, out = sys.argv[1:4]
vdb = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
dip = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
lo = float(sys.argv[6]) if len(sys.argv) > 6 else 1000.0
hi = float(sys.argv[7]) if len(sys.argv) > 7 else 5000.0
v, sr = sf.read(vp, always_2d=True); i, sr2 = sf.read(ip, always_2d=True)
assert sr == sr2
n = min(len(v), len(i)); v, i = v[:n], i[:n]
v = v * 10 ** (vdb / 20)
if dip > 0:
    N, H = 2048, 512
    f, _, Zi = stft(i.T, sr, nperseg=N, noverlap=N - H)
    _, _, Zv = stft(v.T, sr, nperseg=N, noverlap=N - H)
    band = (f >= lo) & (f < hi)
    ev = (np.abs(Zv[:, band]) ** 2).mean(0).sum(0)            # vocal energy in the band per frame
    ei = (np.abs(Zi[:, band]) ** 2).mean(0).sum(0) + 1e-12
    act = np.clip((10 * np.log10(ev / ei + 1e-12) + 12) / 12, 0, 1)  # 0 when voice is >12 dB under the band, 1 at parity
    act = uniform_filter1d(act, int(0.08 * sr / H) or 1)            # ~80 ms smoothing, no pumping
    w = np.zeros_like(f); w[band] = 1
    fade = (f >= lo * 0.7) & (f < lo); w[fade] = (f[fade] - lo * 0.7) / (lo * 0.3)
    fade = (f >= hi) & (f < hi * 1.4); w[fade] = 1 - (f[fade] - hi) / (hi * 0.4)
    g = 10 ** (-(dip * w[:, None] * act[None, :]) / 20)
    i = istft(Zi * g[None], sr, nperseg=N, noverlap=N - H)[1].T[:n]
    print(f"dip {dip} dB on {lo:.0f}-{hi:.0f} Hz, active (>50 %) on {np.mean(act > 0.5) * 100:.0f}% of frames")
y = v + i
sf.write(out, y, sr, subtype="FLOAT")
print(out, f"vocal {vdb:+.1f} dB, peak {np.abs(y).max():.2f}")
