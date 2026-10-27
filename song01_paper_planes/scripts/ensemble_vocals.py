"""Ensemble vocal stems from several separators (UVR-style). Each stem is first gain-matched to the first
one (audio-separator peak-normalises outputs). Methods:
  avg  : mean of waveforms (errors that differ between models partly cancel)
  min  : per STFT bin, keep the stem with the smallest magnitude (removes bleed/noise any model rejects)
  softmin: min magnitude used as a smoothed mask on the average (no musical-noise clicks)
usage: ensemble_vocals.py avg|min|softmin out.flac stem1 stem2 [stem3 ...]"""
import sys, numpy as np, soundfile as sf
from scipy.signal import stft, istft

method, out, paths = sys.argv[1], sys.argv[2], sys.argv[3:]
xs = [sf.read(p, always_2d=True) for p in paths]
sr = xs[0][1]; assert all(s == sr for _, s in xs)
n = min(len(x) for x, _ in xs); xs = [x[:n] for x, _ in xs]
ref = xs[0]
xs = [ref] + [x * (np.sum(x * ref) / np.sum(x * x)) for x in xs[1:]]  # least-squares gain match
if method == "avg":
    y = np.mean(xs, 0)
elif method == "softmin":
    # min magnitude as a mask on the averaged complex spectrum, mask smoothed over time/frequency:
    # keeps the min ensemble's noise rejection without the per-bin switching that causes musical noise/clicks
    from scipy.ndimage import uniform_filter
    N = 2048
    Z = np.stack([stft(x.T, sr, nperseg=N, noverlap=N * 3 // 4)[2] for x in xs])
    avg = Z.mean(0)
    mask = np.abs(Z).min(0) / (np.abs(avg) + 1e-9)
    mask = np.clip(uniform_filter(mask, size=(1, 3, 5)), 0, 1)  # 3 bins x 5 frames
    y = istft(avg * mask, sr, nperseg=N, noverlap=N * 3 // 4)[1].T[:n]
else:
    N = 2048
    Z = [stft(x.T, sr, nperseg=N, noverlap=N * 3 // 4)[2] for x in xs]
    M = np.stack([np.abs(z) for z in Z])                  # (model, ch, f, t)
    idx = M.argmin(0)
    Zo = np.take_along_axis(np.stack(Z), idx[None], 0)[0]
    y = istft(Zo, sr, nperseg=N, noverlap=N * 3 // 4)[1].T[:n]
sf.write(out, y, sr, subtype="PCM_24")
print(out, "peak %.2f" % np.abs(y).max())
