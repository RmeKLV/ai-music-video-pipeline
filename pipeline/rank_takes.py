"""Rank generated takes automatically (ComfyUI STOPPED; tools venv).
  lyric  : Whisper lyric score the generation tail wrote into the folder name (lyrNNN = NN.N %)
  songeval: SongEval mean of 5 axes (only with --research; matched the user's ears on song01)
  aes    : Audiobox Aesthetics CE + PQ (tie-breaker)
Takes with lyric < MIN_LYRIC are ranked last (wrong/garbled words are not fixable in post).
usage: rank_takes.py "<glob of take folders>" [min_lyric=0.80] [--research]  -> table + ranking.json in cwd
DEFAULT (commercial-safe): rank by lyric accuracy (Whisper/MIT; YuE2 authors' standard selection), tie-break by
Audiobox CE+PQ (CC BY 4.0). SongEval is CC BY-NC-SA 4.0 (non-commercial): only with --research."""
import glob, json, os, re, shutil, subprocess, sys, tempfile
import soundfile as sf, torch
import paths

RESEARCH = "--research" in sys.argv
args = [a for a in sys.argv[1:] if a != "--research"]
pattern = args[0]
MIN_LYRIC = float(args[1]) if len(args) > 1 else 0.80
takes = sorted(d for d in glob.glob(pattern) if os.path.isdir(d))
tmp = tempfile.mkdtemp(prefix="rank_")
safe = lambda d: os.path.basename(d).replace(".", "p")  # SongEval cuts file ids at the first dot (cfg2.5)
for d in takes:
    src = paths.find_mix(d)
    x, sr = sf.read(src, always_2d=True)
    sf.write(os.path.join(tmp, safe(d) + ".wav"), x, sr, subtype="PCM_16")

se = {}
if RESEARCH:  # SongEval is CC BY-NC-SA 4.0: research comparisons only
    se_dir = paths.need(paths.SONGEVAL, "SongEval", "AI_SONGEVAL")
    subprocess.run([sys.executable, "eval.py", "-i", tmp, "-o", os.path.join(tmp, "se")], cwd=se_dir,
                   check=True, capture_output=True)
    se = json.load(open(os.path.join(tmp, "se", "result.json")))

from audiobox_aesthetics.infer import initialize_predictor
pred = initialize_predictor()
rows = []
for d in takes:
    name = os.path.basename(d)
    m = re.search(r"lyr(\d{3})", name)
    lyric = int(m.group(1)) / 100 if m else 0.0
    x, sr = sf.read(os.path.join(tmp, safe(d) + ".wav"), always_2d=True, dtype="float32")
    a = pred.forward([{"path": torch.from_numpy(x.T.copy()), "sample_rate": sr}])[0]
    s = se.get(safe(d), {})
    rows.append(dict(take=name, path=d, lyric=lyric, songeval=round(sum(s.values()) / 5, 3) if s else None,
                     aes=round(a["CE"] + a["PQ"], 3), CE=round(a["CE"], 3), PQ=round(a["PQ"], 3),
                     **{k[:4]: v for k, v in s.items()}))
if RESEARCH:
    rows.sort(key=lambda r: (r["lyric"] >= MIN_LYRIC, r["songeval"], r["aes"]), reverse=True)
else:  # lyric accuracy in 2-point bands (Whisper noise), then Audiobox
    rows.sort(key=lambda r: (r["lyric"] >= MIN_LYRIC, round(r["lyric"] / 0.02), r["aes"]), reverse=True)
for i, r in enumerate(rows, 1):
    flag = "" if r["lyric"] >= MIN_LYRIC else "  (lyrics below threshold)"
    se_txt = f"  SongEval {r['songeval']:.3f}" if r["songeval"] is not None else ""
    print(f"{i}. {r['take']:52s} lyric {r['lyric']:.2f}  CE {r['CE']:.2f}  PQ {r['PQ']:.2f}{se_txt}{flag}")
json.dump(rows, open("ranking.json", "w"), indent=1)
shutil.rmtree(tmp, ignore_errors=True)
