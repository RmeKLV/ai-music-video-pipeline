"""Objective checks for 'muffled / static / robotic': bandwidth, HF energy, clicks, clipping, tile-seam periodicity.
usage: analyze_audio.py file1.flac [file2 ...]"""
import sys
import numpy as np
import soundfile as sf


def analyze(path):
    x, sr = sf.read(path, always_2d=True)
    m = x.mean(1)
    n = len(m)
    # spectrum averaged over 4096-sample frames
    hop, win = 2048, 4096
    frames = np.lib.stride_tricks.sliding_window_view(m, win)[::hop]
    spec = (np.abs(np.fft.rfft(frames * np.hanning(win), axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(win, 1 / sr)
    cum = np.cumsum(spec) / spec.sum()
    roll95, roll99 = f[np.searchsorted(cum, 0.95)], f[np.searchsorted(cum, 0.99)]
    band = lambda a, b: 10 * np.log10(spec[(f >= a) & (f < b)].sum() / spec.sum() + 1e-20)
    # highest frequency with energy within 60 dB of the 1-4 kHz level
    ref = spec[(f >= 1000) & (f < 4000)].mean()
    above = f[spec > ref * 1e-6]
    cutoff = above.max() if len(above) else 0
    # clicks: sample-to-sample jumps far above local norm
    d = np.abs(np.diff(m))
    thr = np.median(d) * 40 + 1e-9
    clicks = np.where(d > thr)[0]
    # merge clicks closer than 5 ms
    if len(clicks):
        keep = [clicks[0]]
        for c in clicks[1:]:
            if c - keep[-1] > sr * 0.005:
                keep.append(c)
        clicks = np.array(keep)
    # periodicity of clicks (tile seams would repeat at a fixed interval)
    period = ""
    if len(clicks) > 4:
        gaps = np.diff(clicks) / sr
        vals, counts = np.unique(np.round(gaps, 2), return_counts=True)
        top = counts.argmax()
        period = f"most common gap {vals[top]}s x{counts[top]}"
    clip = (np.abs(x) >= 0.999).mean() * 100
    peak = 20 * np.log10(np.abs(x).max() + 1e-12)
    print(f"{path.split('/')[-2][:46]:46s} {path.split('/')[-1]:16s} sr={sr} dur={n/sr:6.1f}s "
          f"roll95={roll95:6.0f}Hz roll99={roll99:6.0f}Hz cutoff={cutoff:6.0f}Hz "
          f">8k={band(8000, 16000):6.1f}dB >16k={band(16000, sr/2):6.1f}dB "
          f"clicks={len(clicks):4d} {period:24s} clip%={clip:.3f} peak={peak:+.1f}dBFS")


for p in sys.argv[1:]:
    analyze(p.replace("\\", "/"))
