"""Transparent reference mastering (our own; replaces Matchering, whose match landed 3-5 dB off the reference's
long-term balance on song01, with or without its limiter).
 1. match EQ: long-term mid spectrum of mix vs reference, 1/3-octave smoothed, clipped to +-MAXDB, scaled by
    STRENGTH, applied with a linear-phase FIR (same curve on L and R; stereo image untouched)
 2. gain to the reference's average RMS (loudness target)
 3. look-ahead limiter, peak detection on 4x oversampled signal, ceiling CEIL dBTP
usage: master_ref.py mix.wav reference.wav out.wav [strength=0.7] [maxdb=6] [ceil=-1.0]
env MASTER_LOW_DB / MASTER_BODY_DB / MASTER_HIGH_DB / MASTER_LP_HZ: tone stage; MASTER_SUB_CAP=0 caps match boost <90 Hz; MASTER_LUFS=-14 loudness target; after the match (warmer/darker), before the limiter"""
import os, sys
import numpy as np
import soundfile as sf
from scipy.ndimage import maximum_filter1d, minimum_filter1d
from scipy.signal import fftconvolve, firwin2, resample_poly, welch

mix_p, ref_p, out = sys.argv[1:4]
STRENGTH = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
MAXDB = float(sys.argv[5]) if len(sys.argv) > 5 else 6.0
CEIL = float(sys.argv[6]) if len(sys.argv) > 6 else -1.0

x, sr = sf.read(mix_p, always_2d=True)
r, rsr = sf.read(ref_p, always_2d=True)
if rsr != sr:
    r = resample_poly(r, sr, rsr, axis=0)


def spectrum(z):
    f, p = welch(z.mean(1), sr, nperseg=8192)
    return f, p


f, pm = spectrum(x)
_, pr = spectrum(r)
# 1/3-octave smoothing in dB, then normalise both at 1-2 kHz (match shape, not level)
def smooth(p):
    out = np.empty_like(p)
    for i, fi in enumerate(f):
        lo, hi = fi / 2 ** (1 / 6), fi * 2 ** (1 / 6)
        out[i] = p[(f >= lo) & (f <= hi)].mean() if fi > 0 else p[0]
    return 10 * np.log10(out + 1e-20)
dm, dr = smooth(pm), smooth(pr)
band = (f >= 1000) & (f < 2000)
diff = (dr - dr[band].mean()) - (dm - dm[band].mean())
diff = np.clip(diff, -MAXDB, MAXDB) * STRENGTH
if os.environ.get("MASTER_SUB_CAP"):  # never let the reference match boost the sub-bass (boom/'bomb' risk)
    diff[f < 90] = np.minimum(diff[f < 90], float(os.environ["MASTER_SUB_CAP"]))
diff[f < 25] = diff[np.searchsorted(f, 25)]          # no sub-25 Hz boosting
diff[f > 19000] = diff[np.searchsorted(f, 19000)]
taps = firwin2(4097, f / (sr / 2), 10 ** (diff / 20))
delay = (len(taps) - 1) // 2
y = np.stack([fftconvolve(x[:, c], taps)[delay: delay + len(x)] for c in range(x.shape[1])], 1)

# optional tone stage after the match, before loudness/limiter (user, song02: "deeper, less bright").
# env MASTER_LOW_DB (low shelf @120 Hz), MASTER_HIGH_DB (high shelf @7 kHz), MASTER_LP_HZ (12 dB/oct roll-off)
_low, _high, _lp, _body = (float(os.environ.get(k, 0)) for k in ("MASTER_LOW_DB", "MASTER_HIGH_DB", "MASTER_LP_HZ", "MASTER_BODY_DB"))
if _low or _high or _lp or _body:
    import pedalboard as pb
    chain = []
    if _low: chain.append(pb.LowShelfFilter(cutoff_frequency_hz=120, gain_db=_low))
    if _body: chain.append(pb.PeakFilter(cutoff_frequency_hz=180, gain_db=_body, q=0.8))  # depth without sub boom
    if _high: chain.append(pb.HighShelfFilter(cutoff_frequency_hz=7000, gain_db=_high))
    if _lp: chain.append(pb.LowpassFilter(cutoff_frequency_hz=_lp))
    y = pb.Pedalboard(chain)(y.T.astype(np.float32).copy(), sr).T.astype(np.float64)
    print(f"tone: low {_low:+.1f} dB, body {_body:+.1f} dB @180 Hz, high {_high:+.1f} dB, lowpass {_lp:.0f} Hz")

# loudness: env MASTER_LUFS (e.g. -14 = YouTube/streaming norm) or else match the reference's average RMS
rms = lambda z: np.sqrt(np.mean(z.mean(1) ** 2))
if os.environ.get("MASTER_LUFS"):
    import pyloudnorm
    meter = pyloudnorm.Meter(sr)
    y *= 10 ** ((float(os.environ["MASTER_LUFS"]) - meter.integrated_loudness(y)) / 20)
else:
    y *= rms(r) / rms(y)

# look-ahead limiter on 4x oversampled peaks
ceil = 10 ** (CEIL / 20)
peak = np.abs(resample_poly(y, 4, 1, axis=0)).max(1).reshape(-1, 4).max(1)[: len(y)]
need = np.minimum(1.0, ceil / (peak + 1e-12))
la = int(0.0015 * sr)                                  # 1.5 ms look-ahead
g = minimum_filter1d(need, size=2 * la + 1)            # gain reaches target before the peak
rel = np.exp(-1 / (0.08 * sr))                         # 80 ms release
env = np.empty_like(g); prev = 1.0
for i, gi in enumerate(g):                             # instant attack (already looked ahead), smooth release
    prev = gi if gi < prev else rel * prev + (1 - rel) * gi
    env[i] = prev
# smooth attack edge (avoid clicks): short moving average, then never above the required gain
k = la
env = np.minimum(np.convolve(env, np.ones(k) / k, mode="same"), maximum_filter1d(env, k))
env = np.minimum(env, g)
y = y * env[:, None]
tp = 20 * np.log10(np.abs(resample_poly(y, 4, 1, axis=0)).max() + 1e-12)
if tp > CEIL:                                          # safety trim for residual overs
    y *= 10 ** ((CEIL - tp) / 20)
    tp = CEIL
sf.write(out, y, sr, subtype="PCM_24")
try:
    import pyloudnorm
    print(f"integrated loudness {pyloudnorm.Meter(sr).integrated_loudness(y):.1f} LUFS")
except ImportError:
    pass
gr = 20 * np.log10(env.min())
print(f"{out}: EQ max boost {diff.max():+.1f} dB / cut {diff.min():+.1f} dB, limiter max GR {gr:.1f} dB "
      f"(>3 dB on {np.mean(env < 10 ** (-3 / 20)) * 100:.1f}% of samples), true peak {tp:+.2f} dBTP")
