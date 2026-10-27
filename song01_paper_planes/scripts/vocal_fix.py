"""Vocal fixer DSP + remix. ACE vocals carry a voice-locked 8-12 kHz fizz ~10-15 dB above YuE2
(metallic/robotic). This applies a dynamic EQ: per STFT frame, the 7.5-12.5 kHz band is pulled down
only when its energy relative to the voice body (200-4000 Hz) exceeds a target ratio.
Gains are smoothed in time and frequency and applied to the magnitude (original phase kept).

usage:
  vocal_fix.py tame  in_vocals out_vocals [--target -24] [--max-cut 15]
  vocal_fix.py tame  mix.wav out.wav --detector vocals.flac ...   (sidechain: vocal decides, full mix is cut)
  vocal_fix.py repair in out [--mode vocal_hard|vocal|instrument|percussive]   (de-cricket node, standalone)
  vocal_fix.py remix mix vocals_orig instrumental_orig vocals_new out.wav [--inst-new instr.flac]
    (fits gains so a*vocals_orig + b*instrumental_orig ~= mix, then writes a*vocals_new + b*instrumental)
"""
import argparse
import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import istft, stft

N, HOP = 2048, 512


def band_gain_curve(f, lo=7500, hi=12500, fade=1000):
    """0..1 weight: 1 inside [lo, hi], cosine fades of `fade` Hz on both sides."""
    w = np.zeros_like(f)
    w[(f >= lo) & (f <= hi)] = 1
    up = (f > lo - fade) & (f < lo)
    w[up] = 0.5 - 0.5 * np.cos(np.pi * (f[up] - (lo - fade)) / fade)
    dn = (f > hi) & (f < hi + fade)
    w[dn] = 0.5 + 0.5 * np.cos(np.pi * (f[dn] - hi) / fade)
    return w


def tame(x, sr, target_db=-24.0, max_cut_db=15.0, hi_hz=12500, detector=None):
    """detector: optional vocal stem used only to decide the cut (sidechain); the cut is applied to x.
    That way the full mix is processed without a separate -> remix round trip."""
    f, _, Z = stft(x.T, sr, nperseg=N, noverlap=N - HOP)  # Z: (ch, freq, time)
    if detector is not None:
        d = np.zeros_like(x); m = min(len(x), len(detector)); d[:m] = detector[:m, : x.shape[1]] if detector.shape[1] >= x.shape[1] else detector[:m, :1]
        P = (np.abs(stft(d.T, sr, nperseg=N, noverlap=N - HOP)[2]) ** 2).mean(0)
    else:
        P = (np.abs(Z) ** 2).mean(0)  # power summed over channels -> same gain on L and R
    voice = P[(f >= 200) & (f < 4000)].sum(0) + 1e-12
    band = P[(f >= 7500) & (f < 12500)].sum(0) + 1e-12
    excess = 10 * np.log10(band / voice) - target_db  # dB above target
    excess = uniform_filter1d(excess, size=int(0.03 * sr / HOP) or 1)  # ~30 ms smoothing
    cut = np.clip(excess, 0, max_cut_db)
    cut = np.maximum(cut, uniform_filter1d(cut, size=5))  # fast attack, slower release
    w = band_gain_curve(f, hi=hi_hz)[:, None]
    g = 10 ** (-(w * cut[None, :]) / 20)
    _, y = istft(Z * g[None], sr, nperseg=N, noverlap=N - HOP)
    y = y.T[: len(x)]
    return y, cut


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tame")
    t.add_argument("src"); t.add_argument("dst")
    t.add_argument("--target", type=float, default=-24.0)
    t.add_argument("--max-cut", type=float, default=15.0)
    t.add_argument("--hi", type=float, default=12500, help="top of the cut band; 20000 also covers the >12.5 kHz ticks")
    t.add_argument("--detector", help="vocal stem to detect fizz on; the cut is then applied to src (e.g. the full mix)")
    h = sub.add_parser("repair")  # HFArtifactRepair (de-cricket) from comfyui-hybrid-hf-blend, no ComfyUI needed
    h.add_argument("src"); h.add_argument("dst")
    h.add_argument("--mode", default="vocal_hard", choices=["vocal", "vocal_hard", "instrument", "percussive"])
    r = sub.add_parser("remix")
    for a in ("mix", "voc", "inst", "voc_new", "dst"):
        r.add_argument(a)
    r.add_argument("--inst-new", help="replacement instrumental (default: the original)")
    a = ap.parse_args()

    if a.cmd == "tame":
        x, sr = sf.read(a.src, always_2d=True)
        det = None
        if a.detector:
            det, dsr = sf.read(a.detector, always_2d=True)
            assert dsr == sr, "detector sample rate differs"
        y, cut = tame(x, sr, a.target, a.max_cut, a.hi, det)
        sf.write(a.dst, y, sr, subtype="PCM_24")
        print(f"{a.dst}: mean cut {cut.mean():.1f} dB, p95 {np.percentile(cut, 95):.1f} dB, frames cut {np.mean(cut > 0.5) * 100:.0f}%")
    elif a.cmd == "repair":
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "hfblend", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "comfyui", "nodes", "hybrid_hf_blend.py"))
        hb = importlib.util.module_from_spec(spec); spec.loader.exec_module(hb)
        protect, headroom, tilt, max_cut = hb.HFArtifactRepair.PRESETS[a.mode]
        x, sr = sf.read(a.src, always_2d=True)
        y, st = hb._hf_repair_core(x.T, sr, protect, tilt, headroom, 14.0, False, max_cut, 0.7, 0.0, False)
        sf.write(a.dst, y.T, sr, subtype="PCM_24")
        print(f"{a.dst}: [{a.mode}] deepest cut {st['worst_cut_db']:.1f} dB, frames touched {st['frames_touched']}/{st['frames_total']}")
    else:
        mix, sr = sf.read(a.mix, always_2d=True)
        parts = [sf.read(p, always_2d=True) for p in (a.voc, a.inst, a.voc_new)]
        if parts[2][1] != sr:  # restorers may output 44.1 kHz and/or mono
            import librosa
            y = librosa.resample(parts[2][0].T, orig_sr=parts[2][1], target_sr=sr).T
            parts[2] = (y, sr)
        assert all(s == sr for _, s in parts), "sample rates differ"
        n = min(len(mix), *(len(p) for p, _ in parts))
        v, i, vn = (p[:n] for p, _ in parts)
        A = np.stack([v.ravel(), i.ravel()], 1)
        (gv, gi), *_ = np.linalg.lstsq(A, mix[:n].ravel(), rcond=None)
        if a.inst_new:
            inew, isr = sf.read(a.inst_new, always_2d=True)
            assert isr == sr, "instrumental sample rate differs"
            i = inew[:n]
        out = gv * vn + gi * i
        peak = np.abs(out).max()
        if peak > 0.98:
            out *= 0.98 / peak
        sf.write(a.dst, out, sr, subtype="PCM_16")
        print(f"{a.dst}: gains voc {gv:.3f} inst {gi:.3f}, peak {peak:.3f}")


if __name__ == "__main__":
    main()
