"""Transcribe a (separated) drum stem into hits: kick / snare / hihat / crash, with time and velocity.
v2: every hit is detected ONCE (full-band onsets), then classified by which bands jump at that moment
(energy 0-40 ms after vs 40-0 ms before, per band, normalised by that band's 95th percentile jump):
  kick  : 35-120 Hz jump        snare : 150-400 Hz + 1.5-5 kHz jump        hihat : 7-16 kHz jump
  crash : hihat-band jump that stays up (broadband sustain ~0.4 s)
A hit can be kick+snare (both strong) and can carry a hihat. Velocity = the instrument's normalised jump.
Also writes a check spectrogram PNG (first 12 s of busy drums) with the hits marked.
usage: drum_transcribe.py drums.wav out.json"""
import json, sys
from collections import Counter
import numpy as np
import soundfile as sf
import librosa

src, out = sys.argv[1], sys.argv[2]
x, sr0 = sf.read(src, always_2d=True)
SR, HOP = 44100, 256
y = librosa.resample(x.mean(1), orig_sr=sr0, target_sr=SR)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP)) ** 2
f = librosa.fft_frequencies(sr=SR, n_fft=2048)
times = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=HOP)
on = librosa.onset.onset_detect(y=y, sr=SR, hop_length=HOP, units="frames", backtrack=False,
                                pre_max=2, post_max=2, pre_avg=6, post_avg=6, delta=0.05, wait=int(0.045 * SR / HOP))
W = int(0.04 * SR / HOP)


def jump(lo, hi):
    e = S[(f >= lo) & (f < hi)].sum(0) + 1e-12
    return np.array([10 * np.log10(e[o: o + W].mean() / e[max(0, o - W): o].mean()) if o > W else 0 for o in on]), e


jk, _ = jump(35, 120)
js1, _ = jump(150, 400); js2, _ = jump(1500, 5000); js = 0.5 * js1 + 0.5 * js2
jh, eh = jump(7000, 16000)
norm = lambda j: np.clip(j / (np.percentile(j[j > 0], 95) + 1e-9), 0, 1.5)
nk, ns, nh = norm(jk), norm(js), norm(jh)
hits = []
for o, k, s, h in zip(on, nk, ns, nh):
    t = round(float(times[o]), 4)
    if k > 0.35 and k >= 0.8 * s:
        hits.append({"t": t, "inst": "kick", "vel": round(float(min(1, 0.3 + 0.7 * k)), 3)})
    if s > 0.35 and s >= 0.8 * k:
        hits.append({"t": t, "inst": "snare", "vel": round(float(min(1, 0.3 + 0.7 * s)), 3)})
    if h > 0.3:
        sustain = eh[o + 30: o + 70].mean() / (eh[o: o + 6].mean() + 1e-12) if o + 70 < len(eh) else 0
        inst = "crash" if sustain > 0.45 and h > 0.8 else "hihat"
        hits.append({"t": t, "inst": inst, "vel": round(float(min(1, 0.3 + 0.7 * h)), 3)})
hits.sort(key=lambda h: h["t"])
json.dump(hits, open(out, "w"), indent=0)
c = Counter(h["inst"] for h in hits)
print(f"onsets {len(on)} -> {dict(c)}  -> {out}")

# visual check: busiest 12 s
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
dens = np.convolve(np.isin(np.arange(len(times)), on).astype(float), np.ones(int(12 * SR / HOP)), "valid")
s0 = times[int(np.argmax(dens))]; s1 = s0 + 12
fr = (times >= s0) & (times <= s1)
fig, ax = plt.subplots(figsize=(13, 4))
ax.imshow(10 * np.log10(S[:, fr][f < 16000] + 1e-12), origin="lower", aspect="auto", cmap="magma",
          extent=[s0, s1, 0, 16])
col = {"kick": "cyan", "snare": "lime", "hihat": "white", "crash": "red"}
ypos = {"kick": 0.5, "snare": 2.5, "hihat": 12, "crash": 14.5}
for h in hits:
    if s0 <= h["t"] <= s1:
        ax.plot(h["t"], ypos[h["inst"]], "v", color=col[h["inst"]], ms=4 + 5 * h["vel"])
ax.set_title("drum transcription check: cyan=kick lime=snare white=hihat red=crash"); ax.set_xlabel("s"); ax.set_ylabel("kHz")
fig.tight_layout(); fig.savefig(out.replace(".json", "_check.png"), dpi=85)
