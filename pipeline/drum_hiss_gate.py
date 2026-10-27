"""Remove the AI hiss BETWEEN drum hits (user, song02: "hi-hats are mostly hiss"; spectrogram: a constant 4-16 kHz
wash under the drum stem). Above CUT_HZ the drum stem is only allowed through for a natural decay after each
detected hit (hihat 0.12 s, kick 0.08 s, snare 0.25 s, crash 1.2 s); in between it is pulled down by FLOOR_DB.
Only the REDUCTION is applied to the mix (mix += gated_drums - drums), so no other track is touched and nothing
is amplified. The gate opens 5 ms before each hit and fades with an exponential decay (no clicks).
usage: drum_hiss_gate.py <take folder> hits.json out_take_folder [floor_db=-14] [cut_hz=4000]"""
import glob, json, os, shutil, sys
import numpy as np
import soundfile as sf
from scipy.ndimage import maximum_filter1d
from scipy.signal import istft, stft

take, hits_p, out = sys.argv[1:4]
FLOOR = float(sys.argv[4]) if len(sys.argv) > 4 else -14.0
CUT = float(sys.argv[5]) if len(sys.argv) > 5 else 4000.0
DECAY = {"kick": 0.08, "snare": 0.25, "hihat": 0.12, "hihat_open": 0.5, "crash": 1.2}
rd = lambda n: sf.read(sorted(glob.glob(os.path.join(take, n + ".*")))[0], always_2d=True)
(v, sr), (i, _), (d, _) = rd("vocals"), rd("instrumental"), rd("drums")
n = min(len(v), len(i), len(d)); v, i, d = v[:n], i[:n], d[:n]
N, H = 2048, 256
f, t, Z = stft(d.T, sr, nperseg=N, noverlap=N - H)
gate = np.zeros(len(t))
for h in json.load(open(hits_p)):
    tau = DECAY.get(h["inst"], 0.15)
    a = np.searchsorted(t, h["t"] - 0.005)
    seg = t[a:] - (h["t"] - 0.005)
    env = np.exp(-np.clip(seg, 0, None) / tau) * min(1.0, 0.4 + h["vel"])
    env[seg > 6 * tau] = 0
    gate[a:a + len(env)] = np.maximum(gate[a:a + len(env)], env[: len(gate) - a])
gate = maximum_filter1d(gate, 3)
floor = 10 ** (FLOOR / 20)
g = floor + (1 - floor) * np.clip(gate, 0, 1)                 # 1 near hits, floor in between
w = np.clip((f - CUT * 0.7) / (CUT * 0.3), 0, 1)[:, None]      # fade the effect in from 0.7*CUT to CUT
G = 1 - w * (1 - g[None, :])
dg = istft(Z * G[None], sr, nperseg=N, noverlap=N - H)[1].T[:n]
os.makedirs(out, exist_ok=True)
sf.write(os.path.join(out, "vocals.flac"), v, sr, subtype="PCM_24")
sf.write(os.path.join(out, "instrumental.wav"), i + (dg - d), sr, subtype="FLOAT")
sf.write(os.path.join(out, "drums.wav"), dg, sr, subtype="FLOAT")
for s in ("bass", "other"):
    src = sorted(glob.glob(os.path.join(take, s + ".*")))
    if src:
        shutil.copy(src[0], out)
r = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
print(f"drum stem: {r(d):.1f} -> {r(dg):.1f} dBFS overall; gate open (>50 %) {np.mean(gate > 0.5) * 100:.0f}% of the time; floor {FLOOR} dB above {CUT:.0f} Hz")
