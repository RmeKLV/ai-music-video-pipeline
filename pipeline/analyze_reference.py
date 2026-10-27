"""Measure a reference song so a new, original song can match its *style* (never its melody/lyrics):
tempo, key/mode, tuning offset, section boundaries with energy per section, tonal balance, dynamics.
Run with the tools venv.  usage: analyze_reference.py song.wav [--json out.json]"""
import json, sys
import numpy as np
import soundfile as sf
import librosa

path = sys.argv[1]
x, sr = sf.read(path, always_2d=True)
y = librosa.resample(x.mean(1), orig_sr=sr, target_sr=22050); sr2 = 22050
dur = len(y) / sr2

tempo, beats = librosa.beat.beat_track(y=y, sr=sr2)
tempo = float(np.atleast_1d(tempo)[0])
tuning = float(librosa.estimate_tuning(y=y, sr=sr2))  # fraction of a semitone (-0.5..0.5)
chroma = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(y), sr=sr2, tuning=tuning).mean(1)
# Krumhansl-Schmuckler key estimate
maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
scores = [(np.corrcoef(np.roll(maj, k), chroma)[0, 1], f"{names[k]} major") for k in range(12)] + \
         [(np.corrcoef(np.roll(mnr, k), chroma)[0, 1], f"{names[k]} minor") for k in range(12)]
scores.sort(reverse=True)

# sections: agglomerative segmentation on beat-synced chroma+mfcc, ~ one boundary per 15-20 s
hop = 512
feat = np.vstack([librosa.feature.chroma_cqt(y=y, sr=sr2, hop_length=hop),
                  librosa.util.normalize(librosa.feature.mfcc(y=y, sr=sr2, n_mfcc=13, hop_length=hop), axis=1)])
sync = librosa.util.sync(feat, beats, aggregate=np.median)
k = max(4, int(round(dur / 18)))
bounds = librosa.segment.agglomerative(sync, k)
btimes = librosa.frames_to_time(beats, sr=sr2, hop_length=hop)
sec_t = [0.0] + [float(btimes[b]) for b in bounds[1:] if b < len(btimes)] + [dur]
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr2, hop_length=hop)
sections = []
for a, b in zip(sec_t[:-1], sec_t[1:]):
    m = (rt >= a) & (rt < b)
    sections.append({"start": round(a, 1), "end": round(b, 1), "bars": round((b - a) * tempo / 60 / 4, 1),
                     "energy_db": round(float(20 * np.log10(rms[m].mean() + 1e-9)), 1)})
emax = max(s["energy_db"] for s in sections)
for s in sections:
    s["energy_rel"] = round(s["energy_db"] - emax, 1)

# tonal balance relative to 1-2 kHz
f, S = np.fft.rfftfreq(8192, 1 / sr), None
fr = np.lib.stride_tricks.sliding_window_view(x.mean(1), 8192)[::4096] * np.hanning(8192)
S = (np.abs(np.fft.rfft(fr, axis=1)) ** 2).mean(0)
band = lambda a, b: S[(f >= a) & (f < b)].mean()
r = band(1000, 2000)
balance = {f"{a}-{b}": round(float(10 * np.log10(band(a, b) / r)), 1) for a, b in
           [(30, 80), (80, 250), (250, 800), (800, 2000), (2000, 5000), (5000, 10000), (10000, 16000)]}
m = x.mean(1)
crest = 20 * np.log10(np.abs(x).max() / np.sqrt(np.mean(m ** 2)))

res = {"file": path.split("/")[-1].split("\\")[-1], "duration_s": round(dur, 1), "tempo_bpm": round(tempo, 1),
       "key": scores[0][1], "key_alternatives": [s[1] for s in scores[1:3]],
       "tuning_offset_semitones": round(tuning, 2), "crest_db": round(float(crest), 1),
       "tonal_balance_db_vs_1-2k": balance, "sections": sections}
print(json.dumps(res, indent=1))
if "--json" in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
