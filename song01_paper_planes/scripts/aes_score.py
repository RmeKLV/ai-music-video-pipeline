"""Meta Audiobox Aesthetics (facebook/audiobox-aesthetics, CC BY 4.0): 4 axes on ~1-10.
  PQ production quality (clarity, fidelity, dynamics)   PC production complexity
  CE content enjoyment                                    CU content usefulness
Complements SongEval, which is blind to HF artifacts. Run with the tools venv, ComfyUI stopped.
usage: aes_score.py file_or_dir [...]  -> table sorted by PQ, saved as aes.json next to the first input"""
import glob, json, os, sys
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
from audiobox_aesthetics.infer import initialize_predictor

files = []
for a in sys.argv[1:]:
    files += sorted(glob.glob(os.path.join(a, "*.wav")) + glob.glob(os.path.join(a, "*.flac"))) if os.path.isdir(a) else [a]
import soundfile as sf, torch
pred = initialize_predictor()
res = []
for f in files:  # load with soundfile: torchaudio.load needs torchcodec, which is broken in this torch build
    x, sr = sf.read(f, always_2d=True, dtype="float32")
    res += pred.forward([{"path": torch.from_numpy(x.T.copy()), "sample_rate": sr}])
rows = sorted(zip(files, res), key=lambda r: -r[1]["PQ"])
for f, r in rows:
    print(f"{(os.path.basename(os.path.dirname(f))[:40] + '/' if os.path.basename(f).startswith('mix') else '') + os.path.basename(f):60s} PQ {r['PQ']:.3f}  PC {r['PC']:.3f}  CE {r['CE']:.3f}  CU {r['CU']:.3f}", flush=True)
first = sys.argv[1] if os.path.isdir(sys.argv[1]) else os.path.dirname(sys.argv[1])
json.dump({os.path.basename(f): r for f, r in rows}, open(os.path.join(first, "aes.json"), "w"), indent=1)
