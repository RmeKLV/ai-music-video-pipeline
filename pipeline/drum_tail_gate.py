"""Gate the hum BETWEEN drum hits without losing any hit (song03 "Porch Light", 2026-10-18).
The AI drum stem carries a "flickering static hum" in each hit's tail (user, 1:29). A gate driven by a simple
envelope detector missed ~20 real hits (dips). Here every hit is found with spectral-flux onset detection
(librosa, backtracked to the true start, low threshold), the gate opens 5 ms before each onset and decays
with TAIL seconds; between hits the stem is FLOOR dB down. Sustained real content (crescendos, crash swells)
keeps the gate open via a second rule: the gate never drops below the stem's own short-term level relative to
the loudest recent hit (HOLD dB window). Reduction only: instrumental' = instrumental - drums + gated(drums).
usage: drum_tail_gate.py <take folder with soft drums> <out take folder> [floor_db=-40] [tail_s=0.07]"""
import glob, os, shutil, sys
import numpy as np, soundfile as sf, librosa
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfiltfilt

take, out = sys.argv[1:3]
FLOOR = float(sys.argv[3]) if len(sys.argv) > 3 else -40.0
TAIL = float(sys.argv[4]) if len(sys.argv) > 4 else 0.07
rd = lambda n: sf.read(sorted(glob.glob(os.path.join(take, n + ".*")))[0], always_2d=True)
(inst, sr), (d, _) = rd("instrumental"), rd("drums")
n = min(len(inst), len(d)); inst, d = inst[:n], d[:n]
mono = d.mean(1)

hop = 128
y = librosa.resample(mono, orig_sr=sr, target_sr=24000)
oenv = librosa.onset.onset_strength(y=y, sr=24000, hop_length=hop // 2, aggregate=np.median, lag=1, max_size=3)
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=24000, hop_length=hop // 2, backtrack=True, delta=0.03, wait=2, units="time")
fr = sr / hop; m = len(mono) // hop
gate = np.zeros(m)
t_idx = np.arange(m) / fr
for t0 in on:
    a = max(0, int((t0 - 0.005) * fr))
    seg = np.arange(m - a) / fr
    env = np.exp(-seg / TAIL); env[seg > 8 * TAIL] = 0
    gate[a:] = np.maximum(gate[a:], env)
# sustained content rule: 50 ms level within 18 dB of the loudest level in the last 1.5 s -> keep open
lv = 10 * np.log10(uniform_filter1d((mono[: m * hop].reshape(m, hop) ** 2).mean(1), int(0.05 * fr)) + 1e-14)
ref = maximum_filter1d(lv, int(1.5 * fr), origin=int(0.7 * fr) - 1)
sustain = np.clip((lv - (ref - 18)) / 6, 0, 1) * (lv > -50)
gate = np.maximum(gate, sustain)
g = 10 ** (FLOOR / 20) + (1 - 10 ** (FLOOR / 20)) * gate
g = np.repeat(g, hop); g = np.pad(g, (0, max(0, n - len(g))), mode="edge")[:n]
g = sosfiltfilt(butter(1, 80, fs=sr, output="sos"), g)
new_d = d * g[:, None]
os.makedirs(out, exist_ok=True)
for f in glob.glob(os.path.join(take, "*.*")): shutil.copy(f, out)
sf.write(os.path.join(out, "instrumental.flac"), inst - d + new_d, sr, subtype="PCM_24")
sf.write(os.path.join(out, "drums.flac"), new_d, sr, subtype="PCM_24")
print(f"{len(on)} onsets; floor {FLOOR} dB, tail {TAIL} s, gate avg {20*np.log10(g.mean()):.1f} dB -> {out}")
