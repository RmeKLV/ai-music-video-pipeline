"""Level wobble inside sung notes: pyin-voiced runs >= 300 ms; within each, 20 ms level vs a 200 ms smoothed level.
  wobble_db : median per-note std of the level deviation (natural singing ~1-2 dB)
  drops     : count of in-note dips >= 6 dB below the note's smoothed level (volume 'drops and comes back')
Prints the worst drop timestamps.  usage: note_wobble.py vocals.flac [more...]"""
import sys, numpy as np, soundfile as sf, librosa
from scipy.ndimage import uniform_filter1d
for p in sys.argv[1:]:
    x, sr = sf.read(p, always_2d=True); y = librosa.resample(x.mean(1), orig_sr=sr, target_sr=16000)
    hop = 320  # 20 ms
    f0, vf, _ = librosa.pyin(y, fmin=80, fmax=1000, sr=16000, frame_length=1024, hop_length=hop)
    rms = librosa.feature.rms(y=y, frame_length=640, hop_length=hop, center=True)[0][: len(vf)]
    db = 20 * np.log10(rms + 1e-9)
    stds, drops, i = [], [], 0
    while i < len(vf):
        if vf[i]:
            j = i
            while j < len(vf) and vf[j]: j += 1
            if j - i >= 15:
                seg = db[i:j]; sm = uniform_filter1d(seg, 10)
                dev = seg - sm; stds.append(dev.std())
                for k in np.where(dev < -6)[0]:
                    drops.append(((i + k) * 0.02, -dev[k]))
            i = j
        else:
            i += 1
    # merge drops within 100 ms
    merged = []
    for t, d in drops:
        if merged and t - merged[-1][0] < 0.1: merged[-1] = (merged[-1][0], max(merged[-1][1], d))
        else: merged.append((t, d))
    worst = sorted(merged, key=lambda e: -e[1])[:12]
    print(f"{p.split('/')[-1]:36s} notes {len(stds):3d}  wobble_db {np.median(stds):.2f}  drops>=6dB {len(merged):3d}  ({len(merged) / (len(y) / 16000 / 60):.1f}/min)")
    print("   worst:", ", ".join(f"{int(t // 60)}:{t % 60:04.1f}(-{d:.0f})" for t, d in sorted(worst)))
