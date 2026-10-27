"""'Sounds like a low-bitrate YouTube video' meters — fingerprints of lossy/neural-codec damage.
  holes_pct   : % of time-frequency cells in 3-12 kHz more than 30 dB below their local (1/3-oct, 100 ms)
                neighbourhood median, in loud frames. Lossy codecs and neural decoders leave blinking spectral
                holes ('birdies', 'underwater' sound). Higher = worse.
  hf_flux     : frame-to-frame spectral change in 3-12 kHz vs 300-3000 Hz (swirl/watery modulation). Higher = worse.
  side_mid_hf : side/mid energy ratio 4-12 kHz (dB). Collapsed (very low) or phasey (near 0) stereo both sound cheap.
  corr_hf     : L/R correlation 4-12 kHz (1 = mono, 0 = unrelated, <0 = phasey)
usage: codec_artifacts.py file1 [file2 ...]   (first 120 s)"""
import sys
import numpy as np
import soundfile as sf
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfiltfilt, stft

print(f"{'file':58s} holes_pct  hf_flux  side_mid_hf  corr_hf")
for p in sys.argv[1:]:
    x, sr = sf.read(p, always_2d=True)
    x = x[: sr * 120]
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    m = x.mean(1)
    f, t, Z = stft(m, sr, nperseg=2048, noverlap=1536)
    P = np.abs(Z) ** 2 + 1e-20
    D = 10 * np.log10(P)
    loud = D.mean(0) > np.percentile(D.mean(0), 40)
    band = (f >= 3000) & (f < 12000)
    ref = median_filter(D[band][:, loud], size=(9, 9))
    holes = np.mean((D[band][:, loud] < ref - 30)) * 100
    flux = lambda b: np.mean(np.abs(np.diff(D[b][:, loud], axis=1)))
    hf_flux = flux(band) / flux((f >= 300) & (f < 3000))
    sos = butter(6, [4000, 12000], "bp", fs=sr, output="sos")
    l, r = sosfiltfilt(sos, x[:, 0]), sosfiltfilt(sos, x[:, 1])
    side_mid = 10 * np.log10(np.mean((l - r) ** 2) / (np.mean((l + r) ** 2) + 1e-20) + 1e-20)
    corr = np.corrcoef(l, r)[0, 1]
    name = (p.replace("\\", "/").split("/")[-2][:30] + "/" if p.replace("\\", "/").split("/")[-1].startswith("mix") else "") + p.replace("\\", "/").split("/")[-1]
    print(f"{name[:58]:58s} {holes:8.2f}  {hf_flux:7.3f}  {side_mid:+10.1f}  {corr:7.3f}", flush=True)
