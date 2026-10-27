"""Objective, reference-free checks for a set of stems or mixes. One row per file, printed as JSON
and saved next to the inputs as eval.json. Run with ComfyUI stopped if --whisper is used.

  fizz_db     8-12 kHz energy vs voice body (200-4000 Hz), loud frames. YuE2 vocal = -26.7 (benchmark),
              raw ACE vocal = -12.1 (metallic). Lower = less fizz; far below -30 = dull.
  hf_flag%    % of frames where HF energy is unsupported by the band below it (HFArtifactRepair detector,
              the de-cricket node from the SUNO chain). <15 clean, 15-40 mild, >40 severe.
  clicks      isolated impulses (2nd difference > 6x its +-5 ms RMS and > -60 dBFS), merged within 5 ms, per minute.
  roll99      frequency below which 99% of energy lies.  cutoff: highest bin within 60 dB of 1-4 kHz.
  lyric_acc   Whisper lyric accuracy (only with --whisper).

usage: eval_audio.py [--whisper] file1 [file2 ...]"""
import importlib.util, json, os, re, sys
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np
import soundfile as sf

_spec = importlib.util.spec_from_file_location(
    "hfblend", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "comfyui", "nodes", "hybrid_hf_blend.py"))
hfblend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hfblend)


def spectral(m, sr):
    win, hop = 4096, 2048
    fr = np.lib.stride_tricks.sliding_window_view(m, win)[::hop] * np.hanning(win)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(win, 1 / sr)
    spec = S.mean(0)
    cum = np.cumsum(spec) / spec.sum()
    roll99 = f[np.searchsorted(cum, 0.99)]
    ref = spec[(f >= 1000) & (f < 4000)].mean()
    cutoff = f[spec > ref * 1e-6].max()
    voice = S[:, (f >= 200) & (f < 4000)].sum(1) + 1e-20
    band = S[:, (f >= 8000) & (f < 12100)].sum(1) + 1e-20
    loud = voice > np.percentile(voice, 50)
    fizz = 10 * np.log10(band[loud].mean() / voice[loud].mean())
    return roll99, cutoff, fizz


def clicks_per_min(m, sr):
    # isolated impulses: 2nd difference far above its own +-5 ms neighbourhood (a global median threshold
    # wrongly counted more 'clicks' the cleaner the silence got) and above an absolute floor (-60 dBFS)
    from scipy.ndimage import uniform_filter1d
    d2 = np.abs(np.diff(m, 2))
    local = np.sqrt(uniform_filter1d(d2 ** 2, size=int(0.01 * sr))) + 1e-9
    c = np.where((d2 > 6 * local) & (d2 > 1e-3))[0]
    if len(c):
        keep = [c[0]]
        for x in c[1:]:
            if x - keep[-1] > sr * 0.005:
                keep.append(x)
        c = keep
    return len(c) / (len(m) / sr / 60)


def hf_flag(x, sr):
    _, st = hfblend._hf_repair_core(x.T, sr, 10000.0, 3.0, 12.0, 14.0, False, 25.0, 0.7, 0.0, True)
    return 100.0 * st["bad_frames"] / st["live_frames"]


def main():
    args = sys.argv[1:]
    whisper = "--whisper" in args
    files = [a for a in args if a != "--whisper"]
    if whisper:
        import jiwer
        from faster_whisper import WhisperModel
        norm = lambda t: " ".join(re.sub(r"[^\w ]+", " ", re.sub(r"\[[^\]]*\]", " ", t.lower()).replace("'", "")).split())
        ref = norm(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lyrics.txt"), encoding="utf-8").read())
        wm = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8")
    rows = []
    for p in files:
        x, sr = sf.read(p, always_2d=True)
        m = x.mean(1)
        roll99, cutoff, fizz = spectral(m, sr)
        row = dict(file=os.path.basename(p), sr=sr, fizz_db=round(fizz, 1), hf_flag_pct=round(hf_flag(x, sr), 1),
                   clicks_min=round(clicks_per_min(m, sr)), roll99=int(roll99), cutoff=int(cutoff))
        if whisper:
            segs, _ = wm.transcribe(p, language="en", beam_size=5, vad_filter=False, condition_on_previous_text=False)
            hyp = norm(" ".join(s.text for s in segs))
            row["lyric_acc"] = round(1 - min(jiwer.wer(ref, hyp), 1.0), 3) if hyp else 0.0
        rows.append(row)
        print(json.dumps(row), flush=True)
    out = os.path.join(os.path.dirname(os.path.abspath(files[0])), "eval.json")
    json.dump(rows, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
