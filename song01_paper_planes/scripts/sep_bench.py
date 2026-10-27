"""Separate each test song with each candidate model -> analysis/sepbench/<song>/<model>/{vocals,instrumental}.flac
Runs models one at a time (one heavy job at a time). usage: sep_bench.py"""
import glob, os, shutil, time
from audio_separator.separator import Separator

A = r"D:\ComfyUI_windows_portable\ComfyUI\output\audio"
OUT = r"D:\Editing\Youtube\AI\song01_paper_planes\analysis\sepbench"
MODELS_DIR = r"D:\Editing\Youtube\AI\tools\models"
SONGS = {
    "yue2": glob.glob(A + r"\YuE2_song_lyr088_s899001831_*\mix.flac")[0],
    "ace": glob.glob(A + r"\ACE15xl_1.7b_cfg2.5_*s678686318*\mix.wav")[0],
}
MODELS = {
    "demucs_ft": "htdemucs_ft.yaml",
    "melrof_kim": "vocals_mel_band_roformer.ckpt",
    "bsrof_1297": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "melrof_kim_unwa": "mel_band_roformer_kim_ft_unwa.ckpt",
}

for tag, model in MODELS.items():
    tmp = os.path.join(OUT, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    sep = Separator(output_dir=tmp, model_file_dir=MODELS_DIR, output_format="FLAC", sample_rate=48000)
    sep.load_model(model_filename=model)
    for song, path in SONGS.items():
        dst = os.path.join(OUT, song, tag)
        if os.path.exists(os.path.join(dst, "vocals.flac")):
            continue
        os.makedirs(dst, exist_ok=True)
        t = time.time()
        files = [os.path.join(tmp, f) if not os.path.isabs(f) else f for f in sep.separate(path)]
        stems = {}
        for f in files:
            low = os.path.basename(f).lower()
            for s in ("vocals", "instrumental", "other", "drums", "bass", "no_vocals"):
                if f"({s})" in low:
                    stems[s] = f
        if "vocals" in stems:
            shutil.move(stems.pop("vocals"), os.path.join(dst, "vocals.flac"))
        if "instrumental" in stems:
            shutil.move(stems.pop("instrumental"), os.path.join(dst, "instrumental.flac"))
        elif "other" in stems and "drums" in stems:  # demucs: instrumental = drums + bass + other
            import soundfile as sf
            parts = [sf.read(stems[s]) for s in ("drums", "bass", "other") if s in stems]
            sf.write(os.path.join(dst, "instrumental.flac"), sum(p[0] for p in parts), parts[0][1])
        elif "other" in stems:  # vocal-only roformers name the remainder "other"
            shutil.move(stems.pop("other"), os.path.join(dst, "instrumental.flac"))
        for f in glob.glob(os.path.join(tmp, "*")):
            os.remove(f)
        print(f"{song:5s} {tag:16s} {time.time() - t:6.1f}s -> {sorted(os.listdir(dst))}", flush=True)
    del sep
print("SEP_DONE", flush=True)
