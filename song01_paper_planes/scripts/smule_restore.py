"""Smule Renaissance Small vocal restoration (MIT, singing-trained, 48 kHz), stereo-preserving: each channel
is restored separately. Model code + weights in tools/smule_rs (from huggingface smulelabs/Smule-Renaissance-Small).
usage: smule_restore.py in.flac out.flac"""
import sys, torch, numpy as np, soundfile as sf, torchaudio
sys.path.insert(0, r"D:\Editing\Youtube\AI\tools\smule_rs")
from model import Renaissance
from spectral_ops import STFT, iSTFT

src, dst = sys.argv[1], sys.argv[2]
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = Renaissance().to(dev).float()
model.load_state_dict(torch.load(r"D:\Editing\Youtube\AI\tools\smule_rs\smule-renaissance-small.pt", map_location=dev, weights_only=True))
model.eval()
stft, istft = STFT(4096, 2048, 4096), iSTFT(4096, 2048, 4096)
x, sr = sf.read(src, always_2d=True, dtype="float32")
w = torch.from_numpy(x.T.copy())
if sr != 48000:
    w = torchaudio.functional.resample(w, sr, 48000)
w = torchaudio.functional.highpass_biquad(w, 48000, 60.0)
out = []
for ch in w:
    c = ch[None].to(dev).float()
    peak = c.abs().max()
    with torch.no_grad():
        y = istft(model(stft(c / peak)).float()) * peak
    out.append(y[0, : c.shape[1]].cpu().numpy())
n = min(len(o) for o in out)
y = np.stack([o[:n] for o in out], 1)
sf.write(dst, y, 48000, subtype="PCM_24")
print("wrote", dst, y.shape, "peak %.3f" % np.abs(y).max())
