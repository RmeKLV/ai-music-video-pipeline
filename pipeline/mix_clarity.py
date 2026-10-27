"""Mix clarity meters (what a listener calls 'buried vocal', 'mush', 'noisy', 'too bright', 'can't tell instruments').
Needs the mix and its vocal + instrumental stems (same separator for every song you compare).
  vox_over_band_db : vocal RMS minus instrumental RMS in frames where the voice is active (commercial rock ~ -3..+3)
  vox_presence_db  : same, only 1-5 kHz (intelligibility band; masking by guitars shows up here)
  mid_flatness     : spectral flatness of the MIX in 300-4000 Hz (0 = tonal/clean, 1 = white noise). Higher = mushier
  transient_def    : onset-strength peak/median ratio (higher = drums and attacks stand out = instruments separable)
  bright_db        : 5-12 kHz energy vs 200-2000 Hz in the mix (higher = brighter/harsher)
usage: mix_clarity.py <label> <mix> <vocals> <instrumental> [<label> <mix> <vocals> <instr> ...]"""
import sys
import numpy as np
import soundfile as sf
import librosa


def load(p, sr=44100):
    x, s = sf.read(p, always_2d=True)
    return librosa.resample(x.mean(1), orig_sr=s, target_sr=sr) if s != sr else x.mean(1)


def meters(mix, voc, ins, sr=44100):
    n = min(len(mix), len(voc), len(ins)); mix, voc, ins = mix[:n], voc[:n], ins[:n]
    N, H = 2048, 512
    V = np.abs(librosa.stft(voc, n_fft=N, hop_length=H)) ** 2
    I = np.abs(librosa.stft(ins, n_fft=N, hop_length=H)) ** 2
    M = np.abs(librosa.stft(mix, n_fft=N, hop_length=H)) ** 2
    f = librosa.fft_frequencies(sr=sr, n_fft=N)
    ve = V.sum(0); active = ve > np.percentile(ve, 60)          # voice clearly present
    db = lambda a: 10 * np.log10(a + 1e-20)
    vox = db(ve[active].mean()) - db(I.sum(0)[active].mean())
    pb = (f >= 1000) & (f < 5000)
    pres = db(V[pb][:, active].sum(0).mean()) - db(I[pb][:, active].sum(0).mean())
    mb = (f >= 300) & (f < 4000)
    flat = np.exp(np.mean(np.log(M[mb] + 1e-20), 0)) / (M[mb].mean(0) + 1e-20)
    loud = M.sum(0) > np.percentile(M.sum(0), 30)
    onset = librosa.onset.onset_strength(y=mix, sr=sr, hop_length=H)
    tdef = np.percentile(onset, 95) / (np.median(onset) + 1e-9)
    bright = db(M[(f >= 5000) & (f < 12000)].sum(0).mean()) - db(M[(f >= 200) & (f < 2000)].sum(0).mean())
    return vox, pres, float(np.median(flat[loud])), tdef, bright


args = sys.argv[1:]
print(f"{'song':34s} vox_over_band  vox_presence  mid_flatness  transient_def  bright")
for i in range(0, len(args), 4):
    lab, m, v, ins = args[i:i + 4]
    vox, pres, flat, tdef, br = meters(load(m), load(v), load(ins))
    print(f"{lab:34s} {vox:+9.1f} dB  {pres:+9.1f} dB  {flat:11.3f}  {tdef:12.2f}  {br:+6.1f} dB", flush=True)
