"""Re-create a drum track from transcribed hits with a real multisampled kit (Big Rusty Drums, CC0, Karoryfer).
Per hit: velocity -> velocity layer, round-robin rotation (never the same variant twice in a row), small velocity
gain curve; close mics (mono, centred) + overheads (stereo) blended like a studio recording; open hi-hat choked by
the next hi-hat (rendered only up to the next hat + 40 ms fade). Output: stereo float WAV at the song's sample rate and length.
usage: drum_render.py hits.json out.wav <sample_rate> <seconds> [kit_dir]"""
import glob, json, os, random, re, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import paths

hits_p, out, SR, DUR = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
KIT = sys.argv[5] if len(sys.argv) > 5 else paths.need(paths.DRUM_KIT, "Big Rusty Drums samples", "AI_DRUM_KIT")
# instrument -> list of (mic folder, gain dB)  (close mic first, overheads after)
MAP = {
    "kick":   [("kick_24/kick/kick", 0.0), ("kick_24/kick/oh", -9.0)],
    "snare":  [("snare_14/center/top", 0.0), ("snare_14/center/btm", -10.0), ("snare_14/center/oh", -6.0)],
    "hihat":  [("hihat_14/cl/cl", 0.0), ("hihat_14/cl/oh", -6.0)],
    "hihat_open": [("hihat_14/ho/cl", 0.0), ("hihat_14/ho/oh", -6.0)],
    "crash":  [("crash_17/cr/cl", -2.0), ("crash_17/cr/oh", -4.0)],
}
cache = {}


def sample(path):
    if path not in cache:
        x, sr = sf.read(path, always_2d=True, dtype="float32")
        if sr != SR:
            x = resample_poly(x, SR, sr, axis=0).astype(np.float32)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, 1)
        cache[path] = x
    return cache[path]


def layers(folder):
    files = glob.glob(os.path.join(KIT, folder, "*.flac"))
    by = {}
    for f in files:
        m = re.search(r"vl(\d+)_rr(\d+)", os.path.basename(f))
        if m:
            by.setdefault(int(m.group(1)), {})[int(m.group(2))] = os.path.basename(f)
    return by


LAY = {inst: layers(mics[0][0]) for inst, mics in MAP.items()}
hits = json.load(open(hits_p))
# hi-hat: closed by default; open only before a long gap (>= 0.8 s, e.g. end of a phrase)
hat_idx = [i for i, h in enumerate(hits) if h["inst"] == "hihat"]
for a, b in zip(hat_idx, hat_idx[1:] + [None]):
    if b is None or hits[b]["t"] - hits[a]["t"] >= 0.8:
        hits[a]["inst"] = "hihat_open"
y = np.zeros((int(DUR * SR) + SR * 3, 2), np.float32)
last_rr, rng = {}, random.Random(7)
for h in hits:
    inst = h["inst"]
    if inst not in MAP:
        continue
    lay = LAY[inst]
    ks = sorted(lay)
    v = min(1.0, max(0.0, (h["vel"] - 0.3) / 0.7))
    L = ks[min(len(ks) - 1, int(round(v * (len(ks) - 1))))]
    rrs = sorted(lay[L]); choices = [r for r in rrs if r != last_rr.get(inst)] or rrs
    rr = rng.choice(choices); last_rr[inst] = rr
    name = lay[L][rr]
    g = 10 ** ((-6 * (1 - v)) / 20)            # extra soft-to-loud shaping within the layer
    start = int(h["t"] * SR)
    for folder, gdb in MAP[inst]:
        x = sample(os.path.join(KIT, folder, name)) * g * 10 ** (gdb / 20)
        if inst == "hihat_open":                 # limit open hat to the next hat (choke) + 40 ms fade
            nxt = next((hh["t"] for hh in hits if hh["t"] > h["t"] + 0.01 and hh["inst"].startswith("hihat")), None)
            if nxt is not None:
                n = int((nxt - h["t"]) * SR) + int(0.04 * SR)
                x = x[:n].copy(); f = min(int(0.04 * SR), len(x)); x[-f:] *= np.linspace(1, 0, f)[:, None]
        e = min(len(y), start + len(x))
        y[start:e] += x[: e - start]
y = y[: int(DUR * SR)]
sf.write(out, y, SR, subtype="FLOAT")
from collections import Counter
print(dict(Counter(h["inst"] for h in hits)), f"peak {np.abs(y).max():.2f}", "->", out)
