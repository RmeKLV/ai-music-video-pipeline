"""Reference mastering with Matchering 2 (GPL-3 tool; output audio is ours): matches the target's loudness,
tonal balance (frequency response) and stereo width to a professionally mastered reference, then applies
Matchering's own brickwall limiter. Writes 24-bit WAV and prints loudness / peak / crest of input, output, reference.
usage: master.py target.wav reference.wav out.wav"""
import sys
import numpy as np
import soundfile as sf
import matchering as mg

target, reference, out = sys.argv[1:4]
mg.log(print)
mg.process(target=target, reference=reference, results=[mg.pcm24(out)])


def stats(p):
    x, sr = sf.read(p, always_2d=True)
    m = x.mean(1)
    win = int(0.4 * sr)  # momentary-style RMS, top 10% = loud passages
    fr = np.sqrt(np.mean(m[: len(m) // win * win].reshape(-1, win) ** 2, 1))
    loud = 20 * np.log10(np.mean(np.sort(fr)[-max(1, len(fr) // 10):]) + 1e-12)
    peak = 20 * np.log10(np.abs(x).max() + 1e-12)
    rms = 20 * np.log10(np.sqrt(np.mean(m ** 2)) + 1e-12)
    side = x[:, 0] - x[:, 1] if x.shape[1] == 2 else np.zeros(1)
    width = 20 * np.log10(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean((x[:, 0] + x[:, 1]) ** 2)) + 1e-12) + 1e-12)
    return f"loud-RMS {loud:6.1f} dBFS  avg-RMS {rms:6.1f}  peak {peak:5.1f}  crest {peak - rms:4.1f} dB  side/mid {width:5.1f} dB"


for name, p in (("input", target), ("master", out), ("reference", reference)):
    print(f"{name:9s} {stats(p)}")
