"""Short A/B listening clips: master each take (master_ref.py, master-only path) and cut its loudest
CLIP-second window (usually a chorus), with 0.5 s fades, all at equal average loudness.
Keeps listening sessions short for the user. env CLIP_START=<seconds> uses one fixed window for all clips.  usage: make_clips.py reference.wav out_dir label=mix_or_take_folder [label=mix_path ...]"""
import os, subprocess, sys, tempfile
import numpy as np
import soundfile as sf
from paths import MASTER as master, find_mix

CLIP = 25.0
START = float(os.environ['CLIP_START']) if os.environ.get('CLIP_START') else None  # same window for every clip
ref, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="clips_")
clips = []
for arg in sys.argv[3:]:
    label, mix = arg.split("=", 1)
    if os.path.isdir(mix):  # a take folder: the generation tail saves mix.wav or mix.flac
        mix = find_mix(mix)
    mpath = os.path.join(tmp, label + ".wav")
    subprocess.run([sys.executable, master, mix, ref, mpath], check=True, capture_output=True)
    x, sr = sf.read(mpath, always_2d=True)
    win, hop = int(CLIP * sr), sr // 2
    e = np.array([np.mean(x[i:i + win] ** 2) for i in range(0, max(1, len(x) - win + 1), hop)])
    s = int(START * sr) if START is not None else int(np.argmax(e)) * hop
    c = x[s:s + win].copy()
    fade = int(0.5 * sr); ramp = np.linspace(0, 1, fade)[:, None]
    c[:fade] *= ramp; c[-fade:] *= ramp[::-1]
    clips.append((label, c, sr, s / sr))
target = np.mean([np.sqrt(np.mean(c ** 2)) for _, c, _, _ in clips])
for label, c, sr, start in clips:
    c = c * target / np.sqrt(np.mean(c ** 2))
    pk = np.abs(c).max()
    if pk > 0.89:  # keep -1 dB headroom after level matching
        c *= 0.89 / pk
    sf.write(os.path.join(out, f"{label}.flac"), c, sr, subtype="PCM_24")
    print(f"{label:40s} from {int(start // 60)}:{start % 60:04.1f}")
