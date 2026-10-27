"""Robotic-pitch check: how 'alive' the sung pitch is. Measures, on voiced frames (pyin, 10 ms hop):
  jitter_c   : median |frame-to-frame pitch change| in cents (very low = quantised/robotic)
  micro_c    : std of pitch around a 150 ms smoothed contour, cents (natural singing ~15-40)
  flat_pct   : % of voiced time inside notes held within +-5 cents for >=200 ms (autotune-like plateaus)
usage: pitch_naturalness.py file1 [file2 ...]   (first 90 s analysed)"""
import sys, numpy as np, soundfile as sf, librosa
from scipy.ndimage import uniform_filter1d
for p in sys.argv[1:]:
    x, sr = sf.read(p, always_2d=True); y = librosa.resample(x.mean(1)[: sr * 90], orig_sr=sr, target_sr=16000)
    f0, vflag, _ = librosa.pyin(y, fmin=80, fmax=1000, sr=16000, frame_length=1024, hop_length=160)
    c = 1200 * np.log2(f0 / 440.0)
    v = vflag & np.isfinite(c)
    d = np.abs(np.diff(c)); dv = v[1:] & v[:-1]
    jitter = np.median(d[dv])
    cs = c.copy(); cs[~v] = np.nan
    # smooth only within voiced runs
    micro, flat, tot = [], 0, 0
    run = []
    for i in range(len(cs) + 1):
        if i < len(cs) and v[i]:
            run.append(cs[i]); continue
        if len(run) >= 15:
            r = np.array(run); sm = uniform_filter1d(r, 15)
            micro.append(r - sm); tot += len(r)
            # plateaus: windows of 20 frames with range < 10 cents
            if len(r) < 20:
                run = []; continue
            w = np.lib.stride_tricks.sliding_window_view(r, 20)
            ok = (w.max(1) - w.min(1)) < 10
            mark = np.zeros(len(r), bool)
            for j in np.where(ok)[0]: mark[j:j + 20] = True
            flat += mark.sum()
        run = []
    micro = np.concatenate(micro)
    print(f"{p.split('/')[-1]:32s} jitter_c {jitter:5.1f}  micro_c {micro.std():5.1f}  flat_pct {100 * flat / max(tot, 1):5.1f}  voiced_s {tot / 100:.0f}", flush=True)
