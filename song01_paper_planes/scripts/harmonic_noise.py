"""Static/hiss inside the voice: on voiced frames, energy ON the harmonics (k*f0 +- 20% of f0) vs BETWEEN them,
per band. Higher hnr_db = cleaner voice; static/grain fills the gaps between harmonics and lowers it.
usage: harmonic_noise.py vocals1 [vocals2 ...]   (first 120 s)"""
import sys, numpy as np, soundfile as sf, librosa
BANDS = [(300, 1500), (1500, 3000), (3000, 5000), (5000, 8000)]
for p in sys.argv[1:]:
    x, sr = sf.read(p, always_2d=True); y = librosa.resample(x.mean(1)[: sr * 120], orig_sr=sr, target_sr=24000)
    hop, nfft = 240, 4096
    f0, vf, _ = librosa.pyin(y, fmin=80, fmax=1000, sr=24000, frame_length=2048, hop_length=hop)
    S = np.abs(librosa.stft(y, n_fft=nfft, hop_length=hop)) ** 2
    f = librosa.fft_frequencies(sr=24000, n_fft=nfft)
    T = min(S.shape[1], len(vf)); res = {b: [] for b in BANDS}
    loud = 10 * np.log10(S[:, :T].sum(0) + 1e-12); thr = np.percentile(loud, 40)
    for t in range(T):
        if not vf[t] or not np.isfinite(f0[t]) or loud[t] < thr: continue
        h = f / f0[t]; dist = np.abs(h - np.round(h))
        on, off = dist < 0.2, (dist > 0.3) & (h > 0.7)
        for b in BANDS:
            m = (f >= b[0]) & (f < b[1])
            e_on, e_off = S[m & on, t].mean(), S[m & off, t].mean()
            res[b].append(10 * np.log10(e_on / (e_off + 1e-20)))
    print(f"{p.split('/')[-2] + '/' + p.split('/')[-1]:44s} " + "  ".join(f"{a // 1000 if a >= 1000 else a / 1000:.1f}-{b // 1000}k {np.median(v):5.1f}" for (a, b), v in res.items()) + " dB")
