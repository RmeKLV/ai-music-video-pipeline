"""'Premium feel' moves on a full mix (before mastering). Each move can be switched on separately:
  width : mid/side — side channel above 4 kHz +2.5 dB (airy, wide), everything below 120 Hz summed to mono (tight)
  tape  : subtle tape-style saturation: tanh soft-clip at ~-12 dB drive, pre-emphasis/de-emphasis so the
          highs don't fizz, blended 35 % parallel (warmth + density, 'analog glow')
  low   : low-end control — 30 Hz high-pass, -2 dB dynamic-ish shelf at 60 Hz (tames boom), mono bass (with width)
  hats  : TDR Nova dynamic EQ (user's VST3): bell 8.5 kHz, Q 0.8, threshold -14 dB (calibrated song02: ~-1.6 dB average, ~-4.4 dB on the loudest 5 %
          of hi-hat moments), ratio 3:1, 1 ms / 50 ms — tames hi-hat spikes, leaves the rest alone
  space : one shared short room on the whole mix (~0.3 s, high-passed 300 Hz, -24 dB send) = 'recorded in one room'
usage: premium.py in.wav out.wav moves   (moves = comma list, e.g. width,tape,low,space)"""
import sys
import numpy as np
import soundfile as sf
import pedalboard as pb
from scipy.signal import butter, sosfiltfilt

src, dst, moves = sys.argv[1], sys.argv[2], set(sys.argv[3].split(","))
x, sr = sf.read(src, always_2d=True)
x = x.astype(np.float64)
L, R = x[:, 0], x[:, 1]
bp = lambda sig, kind, f: sosfiltfilt(butter(4, f, kind, fs=sr, output="sos"), sig)

if "low" in moves:
    x = pb.Pedalboard([pb.HighpassFilter(30), pb.LowShelfFilter(cutoff_frequency_hz=60, gain_db=-2.0)])(
        x.T.astype(np.float32).copy(), sr).T.astype(np.float64)
    L, R = x[:, 0], x[:, 1]

if "width" in moves or "low" in moves:
    M, S = (L + R) / 2, (L - R) / 2
    S_low = bp(S, "lowpass", 120)
    S = S - S_low                                   # mono below 120 Hz (tight, translates on phones/clubs)
    if "width" in moves:
        S = S + bp(S, "highpass", 4000) * (10 ** (2.5 / 20) - 1)   # +2.5 dB side above 4 kHz
    L, R = M + S, M - S
    x = np.stack([L, R], 1)

if "tape" in moves:
    pre = pb.Pedalboard([pb.HighShelfFilter(cutoff_frequency_hz=3000, gain_db=-4.0)])
    post = pb.Pedalboard([pb.HighShelfFilter(cutoff_frequency_hz=3000, gain_db=4.0)])
    drive = 10 ** (12 / 20)
    w = pre(x.T.astype(np.float32).copy(), sr).T.astype(np.float64)
    w = np.tanh(w * drive) / drive                  # soft saturation, unity small-signal gain
    w = post(w.T.astype(np.float32).copy(), sr).T.astype(np.float64)
    x = 0.65 * x + 0.35 * w

if "hats" in moves:
    nova = pb.load_plugin(r"C:\Program Files\Common Files\VST3\TDR Nova.vst3")
    for k, v in dict(band_1_active=True, band_1_type="Bell", band_1_frequency_hz=8500.0, band_1_q=0.8,
                     band_1_gain_db=0.0, band_1_dyn="On", band_1_threshold_db=-14.0, band_1_ratio=3.0,
                     band_1_attack_ms=1.0, band_1_release_ms=50.0, eq_auto_gain=False).items():
        setattr(nova, k, v)
    y = nova(x.T.astype(np.float32).copy(), sr).T.astype(np.float64)
    from scipy.signal import correlate  # re-align (plugin latency)
    seg = slice(len(x) // 3, len(x) // 3 + sr * 10)
    c = correlate(y[seg].mean(1), x[seg].mean(1), mode="full", method="fft"); mid = len(c) // 2
    lag = int(np.argmax(c[mid - 4800: mid + 4801]) - 4800)
    x = np.roll(y, -lag, axis=0) if lag else y
    print("hats: TDR Nova dynamic band, latency", lag)

if "hats_drums" in moves:
    # Drums-only hi-hat tamer (user: the whole-mix tamer also tames vocals/guitars). Nova runs on the separated
    # drum stem; only the DIFFERENCE it makes (pure reduction) is added to the mix, so nothing else is touched and
    # the stem's separation noise is never amplified. env PREMIUM_DRUMS=<drum stem path>.
    import os
    from scipy.signal import correlate
    dr, dsr = sf.read(os.environ["PREMIUM_DRUMS"], always_2d=True)
    assert dsr == sr, "drum stem sample rate differs"
    n = min(len(x), len(dr)); dr = dr[:n]
    nova = pb.load_plugin(r"C:\Program Files\Common Files\VST3\TDR Nova.vst3")
    for k, v in dict(band_1_active=True, band_1_type="Bell", band_1_frequency_hz=8500.0, band_1_q=0.8,
                     band_1_gain_db=0.0, band_1_dyn="On", band_1_threshold_db=-16.0, band_1_ratio=3.0,
                     band_1_attack_ms=1.0, band_1_release_ms=50.0, eq_auto_gain=False).items():
        setattr(nova, k, v)
    y = nova(dr.T.astype(np.float32).copy(), sr).T.astype(np.float64)[:n]
    seg = slice(n // 3, n // 3 + sr * 10)
    c = correlate(y[seg].mean(1), dr[seg].mean(1), mode="full", method="fft"); mid = len(c) // 2
    lag = int(np.argmax(c[mid - 4800: mid + 4801]) - 4800)
    if lag:
        y = np.roll(y, -lag, axis=0)
    x = x[:n] + (y - dr)
    print("hats_drums: Nova on drum stem (thr -16, calibrated song02: ~-0.6 dB avg / ~-6 dB on hat spikes), latency", lag)

if "space" in moves:
    room = pb.Pedalboard([pb.HighpassFilter(300), pb.LowpassFilter(9000),
                          pb.Reverb(room_size=0.18, damping=0.7, wet_level=1.0, dry_level=0.0, width=1.0)])
    x = x + room(x.T.astype(np.float32).copy(), sr).T.astype(np.float64) * 10 ** (-24 / 20)

sf.write(dst, x, sr, subtype="FLOAT")
print(dst, sorted(moves), "peak %.2f" % np.abs(x).max())
