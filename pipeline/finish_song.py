"""One command: raw ACE/YuE take -> finished master, using the round-4 winning chain (AUDIO_PLAYBOOK.md):
  1. separate the mix with 3 models (MelBand unwa, BS-RoFormer 1297, Demucs ft) -> softmin vocal = DETECTOR only
     (+ stems for the video: unwa vocals/instrumental, Demucs drums/bass/other of the instrumental)
  2. full mix -> de-cricket (instrument mode) -> sidechain fizz control (detector, target -16, max cut 4)
  3. reference master (EQ match 70 %, RMS match, true-peak limiter -1 dBTP)
Also writes the 'master only' baseline so every song can be A/B'd against it.
Run with the tools venv and ComfyUI STOPPED (one heavy job at a time).
usage: finish_song.py <take folder with mix.wav|mix.flac> <reference.wav>"""
import glob, os, shutil, subprocess, sys
from audio_separator.separator import Separator
import paths

PY = sys.executable
S = paths.SCRIPTS
P = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = paths.need(paths.MODELS, "separation models folder", "AI_MODELS")
VOCAL_MODELS = {"unwa": "mel_band_roformer_kim_ft_unwa.ckpt", "bsrof": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
                "demucs": "htdemucs_ft.yaml"}

take, ref = sys.argv[1], sys.argv[2]
mix = paths.find_mix(take)
stems = os.path.join(take, "stems_v3"); fin = os.path.join(take, "final"); os.makedirs(stems, exist_ok=True); os.makedirs(fin, exist_ok=True)
run = lambda *a: print(subprocess.run([PY, *a], check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1], flush=True)


def pick(files, name):
    hits = [f for f in files if f"({name})" in os.path.basename(f).lower()]
    return hits[0] if hits else None


# 1. separation (skips models already done)
for tag, model in VOCAL_MODELS.items():
    dst = os.path.join(stems, f"vocals_{tag}.flac")
    if os.path.exists(dst):
        continue
    tmp = os.path.join(MODELS_DIR, "_tmp_finish"); os.makedirs(tmp, exist_ok=True)
    sep = Separator(output_dir=tmp, model_file_dir=MODELS_DIR, output_format="FLAC", sample_rate=48000)
    sep.load_model(model_filename=model)
    files = [f if os.path.isabs(f) else os.path.join(tmp, f) for f in sep.separate(mix)]
    shutil.move(pick(files, "vocals"), dst)
    if tag == "unwa":
        shutil.move(pick(files, "instrumental") or pick(files, "other"), os.path.join(stems, "instrumental.flac"))
    for f in glob.glob(os.path.join(tmp, "*")):
        os.remove(f)
    del sep
    print("separated", tag, flush=True)
if not os.path.exists(os.path.join(stems, "drums.flac")):  # video stems from the vocal-free instrumental
    tmp = os.path.join(MODELS_DIR, "_tmp_finish")
    sep = Separator(output_dir=tmp, model_file_dir=MODELS_DIR, output_format="FLAC", sample_rate=48000)
    sep.load_model(model_filename="htdemucs_ft.yaml")
    files = [f if os.path.isabs(f) else os.path.join(tmp, f) for f in sep.separate(os.path.join(stems, "instrumental.flac"))]
    for s in ("drums", "bass", "other"):
        shutil.move(pick(files, s), os.path.join(stems, f"{s}.flac"))
    for f in glob.glob(os.path.join(tmp, "*")):
        os.remove(f)
    del sep
det = os.path.join(stems, "vocals_detector_softmin.flac")
run(os.path.join(S, "ensemble_vocals.py"), "softmin", det,
    *[os.path.join(stems, f"vocals_{t}.flac") for t in VOCAL_MODELS])

# 2. full-mix repair chain
mixwav = os.path.join(fin, "0_mix.wav")
run("-c", f"import soundfile as sf; x, sr = sf.read(r'{mix}', always_2d=True); sf.write(r'{mixwav}', x, sr, subtype='FLOAT'); print('mix', sr, x.shape)")
run(os.path.join(S, "vocal_fix.py"), "repair", mixwav, os.path.join(fin, "1_repair.wav"), "--mode", "instrument")
run(os.path.join(S, "vocal_fix.py"), "tame", os.path.join(fin, "1_repair.wav"), os.path.join(fin, "2_repair_side.wav"),
    "--detector", det, "--target", "-16", "--max-cut", "4")

# 3. masters: the chain (final) and the master-only baseline
run(os.path.join(S, "master_ref.py"), os.path.join(fin, "2_repair_side.wav"), ref, os.path.join(fin, "FINAL_master.wav"))
run(os.path.join(S, "master_ref.py"), mixwav, ref, os.path.join(fin, "baseline_master_only.wav"))
print("FINISH_DONE", fin)
