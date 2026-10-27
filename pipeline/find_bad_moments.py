"""Find the moments in each track that 'don't sound right' — local anomalies, not averages.
For every stem, 50 ms frames get feature vectors; a frame is suspicious when it deviates strongly from the same
stem's typical behaviour at a similar loudness:
  vocals : noise-likeness (spectral flatness 1-8 kHz), HF burst (>6 kHz vs body), sudden spectral jump (flux),
           crest drop (squashed/clipped-sounding)
  drums  : per hit (onset): spectral shape vs the median hit of its loudness class -> odd/artificial hits
  bass, other : flatness + flux outliers
Scores are robust z-scores (median/MAD) within loudness bands, so loud notes are compared with loud notes.
Outputs <out>/<stem>_suspects.json (top N, merged within 0.5 s), spectrogram PNGs around each suspect with the
event marked, and 3 s listening clips (stem solo + full mix) — for user confirmation.
usage: find_bad_moments.py <take folder> <out_dir> [top_n=5]"""
import glob, json, os, sys
import numpy as np
import soundfile as sf
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

take, out = sys.argv[1], sys.argv[2]
TOP = int(sys.argv[3]) if len(sys.argv) > 3 else 5
os.makedirs(out, exist_ok=True)
SR = 44100
HOP = 1024          # ~23 ms
N_FFT = 4096


def load(name):
    f = sorted(glob.glob(os.path.join(take, name + ".*")))[0]
    x, sr = sf.read(f, always_2d=True)
    return librosa.resample(x.mean(1), orig_sr=sr, target_sr=SR), x, sr


def robust_z(v, groups):
    z = np.zeros_like(v)
    for g in np.unique(groups):
        m = groups == g
        if m.sum() < 20:
            continue
        med = np.median(v[m]); mad = np.median(np.abs(v[m] - med)) * 1.4826 + 1e-9
        z[m] = (v[m] - med) / mad
    return z


def frame_features(y):
    S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP)) ** 2
    f = librosa.fft_frequencies(sr=SR, n_fft=N_FFT)
    db = lambda a: 10 * np.log10(a + 1e-20)
    lvl = db(S.sum(0))
    mid = (f >= 1000) & (f < 8000)
    flat = np.exp(np.mean(np.log(S[mid] + 1e-20), 0)) / (S[mid].mean(0) + 1e-20)
    hfr = db(S[f >= 6000].sum(0)) - db(S[(f >= 200) & (f < 3000)].sum(0))
    L = np.log(S + 1e-12)
    flux = np.r_[0, np.mean(np.maximum(0, np.diff(L, axis=1)), 0)]
    return S, f, lvl, flat, hfr, flux


def merge(times, scores, gap=0.5):
    order = np.argsort(-scores); picked = []
    for i in order:
        if all(abs(times[i] - t) > gap for t, _ in picked):
            picked.append((times[i], scores[i]))
        if len(picked) >= TOP:
            break
    return sorted(picked)


mix_mono, mix, msr = None, None, None
v, i_ = None, None
vs, vsr = sf.read(sorted(glob.glob(os.path.join(take, "vocals.*")))[0], always_2d=True)
ins, _ = sf.read(sorted(glob.glob(os.path.join(take, "instrumental.*")))[0], always_2d=True)
n = min(len(vs), len(ins)); mix = vs[:n] + ins[:n]; msr = vsr

report = {}
for stem in ("vocals", "drums", "bass", "other"):
    y, raw, rsr = load(stem)
    S, f, lvl, flat, hfr, flux = frame_features(y)
    t = librosa.frames_to_time(np.arange(len(lvl)), sr=SR, hop_length=HOP)
    active = lvl > np.percentile(lvl, 35)
    groups = np.digitize(lvl, np.percentile(lvl[active], [33, 66]))   # quiet / mid / loud bands
    if stem == "drums":
        on = librosa.onset.onset_detect(y=y, sr=SR, hop_length=HOP, units="frames", backtrack=False)
        on = on[on < S.shape[1] - 4]
        # per hit: averaged log-spectrum over 4 frames, compared with the median hit of the same loudness band
        F = np.stack([np.log(S[:, o:o + 4].mean(1) + 1e-12) for o in on])
        F = F - F.mean(1, keepdims=True)
        g = groups[on]
        score = np.zeros(len(on))
        for k in np.unique(g):
            m = g == k
            if m.sum() < 8:
                continue
            ref = np.median(F[m], 0)
            d = np.sqrt(np.mean((F[m] - ref) ** 2, 1))
            score[m] = (d - np.median(d)) / (np.median(np.abs(d - np.median(d))) * 1.4826 + 1e-9)
        times, scores, why = t[on], score, ["odd drum hit (spectrum unlike other hits)"] * len(on)
    else:
        zf = robust_z(flat, groups); zh = robust_z(hfr, groups)
        # v2: ignore +-80 ms around note/hit onsets (normal transients were flagged as 'jumps'); score only what
        # happens INSIDE sustained sound: noise-likeness and HF bursts relative to the same loudness band
        on = librosa.onset.onset_detect(y=y, sr=SR, hop_length=HOP, units="frames")
        near = np.zeros(len(lvl), bool)
        for o in on:
            near[max(0, o - 4): o + 5] = True
        comb = np.maximum(zf, zh) * (active & ~near)
        times, scores = t, comb
        why = ["noise / grain inside a note" if a >= b else "fizz / HF burst inside a note" for a, b in zip(zf, zh)]
    picks = merge(times, scores)
    items = []
    for k, (tt, sc) in enumerate(picks, 1):
        idx = int(np.argmin(np.abs(times - tt)))
        # spectrogram +-1.5 s, event marked
        s0, s1 = max(0, tt - 1.5), tt + 1.5
        fr = (t >= s0) & (t <= s1)
        fig, ax = plt.subplots(figsize=(8, 3.6))
        ax.imshow(10 * np.log10(S[:, fr][f < 16000] + 1e-12), origin="lower", aspect="auto", cmap="magma",
                  extent=[t[fr][0], t[fr][-1], 0, 16], vmin=None)
        ax.axvline(tt, color="cyan", lw=1.5, ls="--")
        ax.set_xlabel("time (s)"); ax.set_ylabel("kHz"); ax.set_title(f"{stem} suspect {k} @ {tt:.2f}s  z={sc:.1f}  ({why[idx]})")
        png = os.path.join(out, f"{stem}_{k}_{tt:.1f}s.png"); fig.tight_layout(); fig.savefig(png, dpi=90); plt.close(fig)
        # 3 s clips: stem solo and full mix
        a, b = int(max(0, tt - 1.5) * rsr), int((tt + 1.5) * rsr)
        fade = int(0.05 * rsr); ramp = np.linspace(0, 1, fade)[:, None]
        for lab, src in (("solo", raw), ("mix", mix)):
            c = src[a:b].copy(); c[:fade] *= ramp; c[-fade:] *= ramp[::-1]
            pk = np.abs(c).max()
            if pk > 0.95: c *= 0.95 / pk
            sf.write(os.path.join(out, f"{stem}_{k}_{tt:.1f}s_{lab}.flac"), c, rsr, subtype="PCM_24")
        items.append({"rank": k, "time_s": round(float(tt), 2), "z": round(float(sc), 1), "why": why[idx], "png": png})
    report[stem] = items
    print(stem, [(it["time_s"], it["z"], it["why"]) for it in items], flush=True)
json.dump(report, open(os.path.join(out, "suspects.json"), "w"), indent=1)
