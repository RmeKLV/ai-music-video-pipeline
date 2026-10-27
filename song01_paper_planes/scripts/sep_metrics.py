"""Reference-free separation quality for analysis/sepbench/<song>/<model>/{vocals,instrumental}.flac
- vocal_acc  : Whisper lyric accuracy on the vocal stem (same settings as the pipeline's whisper_score.py). Higher = cleaner vocal.
- leak_words : lyric words Whisper still finds in the INSTRUMENTAL stem. Lower = less vocal left behind.
- vocal_floor: dB between loud singing (p95 frame RMS) and the vocal stem's floor between phrases (p10).
               Higher = less instrument bleed / noise in the vocal stem.
- residual   : energy of mix - (vocals + instrumental), dB relative to the mix. Lower = stems add back up cleanly.
Run with ComfyUI stopped (one heavy job at a time)."""
import glob, json, os, re, sys
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np
import soundfile as sf
import jiwer
from faster_whisper import WhisperModel

ROOT = r"D:\Editing\Youtube\AI\song01_paper_planes"
A = r"D:\ComfyUI_windows_portable\ComfyUI\output\audio"
MIX = {"yue2": glob.glob(A + r"\YuE2_song_lyr088_s899001831_*\mix.flac")[0],
       "ace": glob.glob(A + r"\ACE15xl_1.7b_cfg2.5_*s678686318*\mix.wav")[0]}


def norm(t):
    t = re.sub(r"\[[^\]]*\]", " ", t.lower()).replace("'", "").replace("\u2019", "")
    return " ".join(re.sub(r"[^\w ]+", " ", t).split())


ref = norm(open(os.path.join(ROOT, "lyrics.txt"), encoding="utf-8").read())
vocab = set(ref.split()) - {"a", "the", "and", "in", "on", "my", "me", "you", "is", "it", "to", "of", "we"}
model = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8")


def hear(path):
    segs, _ = model.transcribe(path, language="en", beam_size=5, vad_filter=False, condition_on_previous_text=False)
    return norm(" ".join(s.text for s in segs))


def frame_rms(x, sr, ms=50):
    n = int(sr * ms / 1000)
    m = x.mean(1)[: len(x) // n * n].reshape(-1, n)
    return np.sqrt((m ** 2).mean(1) + 1e-12)


rows = []
for d in sorted(glob.glob(os.path.join(ROOT, "analysis", "sepbench", "*", "*"))):
    song, tag = d.split(os.sep)[-2:]
    if song.startswith("_") or not os.path.exists(os.path.join(d, "vocals.flac")):
        continue
    v, sr = sf.read(os.path.join(d, "vocals.flac"), always_2d=True)
    i, _ = sf.read(os.path.join(d, "instrumental.flac"), always_2d=True)
    mix, msr = sf.read(MIX[song], always_2d=True)
    n = min(len(v), len(i), len(mix))
    resid = mix[:n] - v[:n] - i[:n]
    residual = 10 * np.log10((resid ** 2).sum() / ((mix[:n] ** 2).sum() + 1e-12) + 1e-12)
    r = frame_rms(v, sr)
    floor = 20 * np.log10(np.percentile(r, 95) / np.percentile(r, 10))
    hv = hear(os.path.join(d, "vocals.flac"))
    acc = 1 - min(jiwer.wer(ref, hv), 1.0) if hv else 0.0
    hi = hear(os.path.join(d, "instrumental.flac"))
    leak = sum(1 for w in hi.split() if w in vocab)
    rows.append(dict(song=song, model=tag, vocal_acc=round(acc, 3), leak_words=leak,
                     vocal_floor_db=round(floor, 1), residual_db=round(residual, 1), sr=sr))
    print(json.dumps(rows[-1]), flush=True)

json.dump(rows, open(os.path.join(ROOT, "analysis", "sepbench", "metrics.json"), "w"), indent=1)
print("METRICS_DONE")
