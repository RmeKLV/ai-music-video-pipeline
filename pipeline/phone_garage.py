"""'Garage recorded on an old phone' meters.
  bw_low / bw_high : -30 dB points of the long-term spectrum relative to its 200-2000 Hz plateau (Hz).
                     Phone-like = narrow (high cutoff low, low end thin).
  sub_db           : 40-100 Hz vs 200-2000 Hz (thin low end = negative)
  air_db           : 10-16 kHz vs 200-2000 Hz
  room_ms          : median energy-decay time after note offsets (60 ms windows; dB/s -> ms to fall 20 dB). Larger = roomier.
usage: phone_garage.py file1 [file2 ...]"""
import sys, numpy as np, soundfile as sf
from scipy.signal import welch
print(f"{'file':52s} bw_low  bw_high  sub_db  air_db  room_ms")
for p in sys.argv[1:]:
    x, sr = sf.read(p, always_2d=True); m = x.mean(1)[: sr * 150]
    f, P = welch(m, sr, nperseg=16384); D = 10 * np.log10(P + 1e-20)
    plateau = D[(f >= 200) & (f < 2000)].mean()
    above = f[(D > plateau - 30)]
    lo = above[above > 20].min() if len(above) else 0; hi = above.max() if len(above) else 0
    band = lambda a, b: D[(f >= a) & (f < b)].mean() - plateau
    hop = int(0.01 * sr); e = 10 * np.log10(np.convolve(m ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    slopes = []
    for i in range(10, len(e) - 30):
        if e[i] - e[i + 3] > 6 and e[i] > np.percentile(e, 70):      # a note offset
            seg = e[i + 3: i + 30]; t = np.arange(len(seg)) * 0.01
            s = np.polyfit(t, seg, 1)[0]
            if s < 0: slopes.append(s)
    room = 20 / -np.median(slopes) * 1000 if slopes else float("nan")
    name = (p.replace("\\", "/").split("/")[-2][:26] + "/" if "mix" in p.split("/")[-1] else "") + p.replace("\\", "/").split("/")[-1]
    print(f"{name[:52]:52s} {lo:6.0f}  {hi:7.0f}  {band(40, 100):+6.1f}  {band(10000, 16000):+6.1f}  {room:7.0f}")
