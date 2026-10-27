"""Upgraded stem separation for a finished take (runs AFTER ComfyUI, never alongside it).
1) RoFormer (winner of scripts/sep_bench.py) splits the raw model output into vocals + instrumental.
2) Demucs htdemucs_ft splits that vocal-free instrumental into drums / bass / other (beat-sync for video).
Writes <take>/stems_v2/{vocals,instrumental,drums,bass,other}.flac; the pipeline's Demucs stems stay untouched.
usage (tools venv): separate_take.py <take folder> [<take folder> ...]"""
import glob, os, shutil, sys
from audio_separator.separator import Separator

VOCAL_MODEL = "mel_band_roformer_kim_ft_unwa.ckpt"  # winner of scripts/sep_bench.py, see analysis/sepbench/DECISION.md
MODELS_DIR = r"D:\Editing\Youtube\AI\tools\models"


def pick(files, name):
    hits = [f for f in files if f"({name})" in os.path.basename(f).lower()]
    return hits[0] if hits else None


def run(sep, path, tmp):
    return [f if os.path.isabs(f) else os.path.join(tmp, f) for f in sep.separate(path)]


takes = sys.argv[1:]
for stage in ("roformer", "demucs"):
    tmp = os.path.join(MODELS_DIR, "_tmp_" + stage)
    os.makedirs(tmp, exist_ok=True)
    sep = Separator(output_dir=tmp, model_file_dir=MODELS_DIR, output_format="FLAC", sample_rate=48000)
    sep.load_model(model_filename=VOCAL_MODEL if stage == "roformer" else "htdemucs_ft.yaml")
    for take in takes:
        out = os.path.join(take, "stems_v2")
        os.makedirs(out, exist_ok=True)
        if stage == "roformer":
            src = next((os.path.join(take, f) for f in ("mix.flac", "mix.wav") if os.path.exists(os.path.join(take, f))), None)
            if not src:
                print("no mix in", take); continue
            files = run(sep, src, tmp)
            shutil.move(pick(files, "vocals"), os.path.join(out, "vocals.flac"))
            shutil.move(pick(files, "instrumental") or pick(files, "other"), os.path.join(out, "instrumental.flac"))
        else:
            files = run(sep, os.path.join(out, "instrumental.flac"), tmp)
            for s in ("drums", "bass", "other"):
                shutil.move(pick(files, s), os.path.join(out, f"{s}.flac"))
        for f in glob.glob(os.path.join(tmp, "*")):
            os.remove(f)
        print(stage, "done:", take, flush=True)
    del sep
print("SEPARATE_DONE")
