"""Debug: does the RoFormer produce real vocals? usage: sep_debug.py <clip> <outdir> [autocast 0/1]"""
import sys, os, glob, numpy as np, soundfile as sf, torch
from audio_separator.separator import Separator
clip, out = sys.argv[1], sys.argv[2]; ac = len(sys.argv) > 3 and sys.argv[3] == "1"
os.makedirs(out, exist_ok=True)
print("cuda visible:", torch.cuda.is_available(), "autocast:", ac, flush=True)
s = Separator(output_dir=out, model_file_dir=r"D:\Editing\Youtube\AI\tools\models", output_format="FLAC", sample_rate=48000, use_autocast=ac)
s.load_model(model_filename="vocals_mel_band_roformer.ckpt")
for f in s.separate(clip):
    p = f if os.path.isabs(f) else os.path.join(out, f); x, sr = sf.read(p)
    print(os.path.basename(p), "rms dB", round(20*np.log10(np.sqrt((x**2).mean())+1e-12), 1), flush=True)
