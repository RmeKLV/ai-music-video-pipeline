"""Blind A/B listening pack: for each pair (two renders of the SAME take, e.g. two decoders), cut the same loudest
chorus window from both, master both identically, level-match, and save them as <n>_X / <n>_Y in random order.
The answer key goes to _key.json (do not show the user before they answer).
usage: blind_ab.py reference.wav out_dir name=fileA,fileB [name=fileA,fileB ...]
       (fileA/fileB labels in the key are 'A' and 'B' as given)"""
import json, os, random, subprocess, sys, tempfile
import numpy as np
import soundfile as sf

CLIP = 25.0
ref, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
master = r"D:\Editing\Youtube\AI\song01_paper_planes\scripts\master_ref.py"
tmp = tempfile.mkdtemp(prefix="blind_")
key, rng = {}, random.Random()
for n, arg in enumerate(sys.argv[3:], 1):
    name, files = arg.split("=", 1)
    fa, fb = files.split(",")
    rendered = []
    for tag, f in (("A", fa), ("B", fb)):
        mp = os.path.join(tmp, f"{n}_{tag}.wav")
        subprocess.run([sys.executable, master, f, ref, mp], check=True, capture_output=True)
        rendered.append(sf.read(mp, always_2d=True))
    (xa, sr), (xb, _) = rendered
    m = min(len(xa), len(xb)); xa, xb = xa[:m], xb[:m]
    win, hop = int(CLIP * sr), sr // 2
    e = np.array([np.mean(xa[i:i + win] ** 2) for i in range(0, m - win, hop)])
    s = int(np.argmax(e)) * hop  # same window for both renders
    fade = int(0.5 * sr); ramp = np.linspace(0, 1, fade)[:, None]
    clips = {}
    for tag, x in (("A", xa), ("B", xb)):
        c = x[s:s + win].copy(); c[:fade] *= ramp; c[-fade:] *= ramp[::-1]
        clips[tag] = c
    target = np.mean([np.sqrt(np.mean(c ** 2)) for c in clips.values()])
    order = ["A", "B"]; rng.shuffle(order)
    key[f"{n}_{name}"] = {"X": order[0], "Y": order[1], "A": fa, "B": fb, "start_s": s / sr}
    for label, tag in zip(("X", "Y"), order):
        c = clips[tag] * target / np.sqrt(np.mean(clips[tag] ** 2))
        pk = np.abs(c).max()
        if pk > 0.89:
            c *= 0.89 / pk
        sf.write(os.path.join(out, f"{n}_{name}_{label}.flac"), c, sr, subtype="PCM_24")
    print(f"{n}_{name}: window from {int(s / sr // 60)}:{s / sr % 60:04.1f}")
json.dump(key, open(os.path.join(out, "_key.json"), "w"), indent=1)
print("key ->", os.path.join(out, "_key.json"))
