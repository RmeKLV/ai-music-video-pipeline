"""Per-stem production ('mixing like in an audio editing app'): each stem gets its own effect chain, every
processed stem is re-aligned to its input (plugin latency), stems are summed with the untouched residual
(mix - sum of stems, so nothing the separator missed is lost), then a bus chain glues it. Master afterwards
with song01_paper_planes/scripts/master_ref.py.

Uses Spotify Pedalboard (GPL-3 tool) + the user's own VST3 plugins (soothe2, spiff, Gullfoss, iZotope RX 11).
usage: produce.py <take folder with mix + vocals/drums/bass/other stems> out.wav [preset=rock] [--no-bus] [--bus-only] [--bus=B1|B2|B3|B4]"""
import glob, os, sys
import numpy as np
import soundfile as sf
import pedalboard as pb
from scipy.signal import correlate

V = r"C:\Program Files\Common Files\VST3"


def vst(path, **params):
    p = pb.load_plugin(os.path.join(V, path))
    for k, v in params.items():
        setattr(p, k, v)
    return p


def send(chain, wet_db):
    """Parallel effect send (reverb/delay) mixed under the dry signal."""
    return pb.Mix([pb.Gain(0.0), pb.Chain(chain + [pb.Gain(wet_db)])])


PRESETS = {
    "rock": {
        "vocals": lambda: [
            pb.HighpassFilter(90),
            vst(r"iZotope\RX 11 De-ess.vst3"),
            vst(r"oeksound\soothe2_x64.vst3", depth=4.0),
            pb.Compressor(threshold_db=-20, ratio=3.0, attack_ms=5, release_ms=90),
            pb.PeakFilter(cutoff_frequency_hz=3500, gain_db=2.0, q=0.9),
            pb.HighShelfFilter(cutoff_frequency_hz=10000, gain_db=1.5),
            send([pb.Delay(delay_seconds=0.03, mix=1.0), pb.HighpassFilter(250), pb.LowpassFilter(8000),
                  pb.Reverb(room_size=0.55, damping=0.55, wet_level=1.0, dry_level=0.0, width=1.0)], -15.0),
            send([pb.Delay(delay_seconds=0.11, feedback=0.12, mix=1.0), pb.HighpassFilter(300),
                  pb.LowpassFilter(5000)], -18.0),
        ],
        "drums": lambda: [
            pb.HighpassFilter(30),
            vst(r"oeksound\spiff_x64.vst3"),
            pb.Mix([pb.Gain(0.0), pb.Chain([pb.Compressor(threshold_db=-28, ratio=6.0, attack_ms=3, release_ms=60),
                                            pb.Gain(-8.0)])]),  # parallel 'New York' compression
            send([pb.HighpassFilter(400), pb.Reverb(room_size=0.25, damping=0.6, wet_level=1.0, dry_level=0.0)], -20.0),
        ],
        "bass": lambda: [
            pb.HighpassFilter(35),
            pb.Compressor(threshold_db=-22, ratio=4.0, attack_ms=10, release_ms=120),
            pb.Mix([pb.Gain(0.0), pb.Chain([pb.Distortion(drive_db=8), pb.LowpassFilter(3000), pb.Gain(-16.0)])]),
        ],
        "other": lambda: [  # guitars and the rest
            pb.HighpassFilter(80),
            pb.PeakFilter(cutoff_frequency_hz=320, gain_db=-2.0, q=1.0),   # mud
            vst(r"oeksound\soothe2_x64.vst3", depth=2.0),
            pb.PeakFilter(cutoff_frequency_hz=2800, gain_db=-1.5, q=1.2),  # leave room for the voice
            send([pb.HighpassFilter(300), pb.Reverb(room_size=0.4, damping=0.6, wet_level=1.0, dry_level=0.0, width=1.0)], -22.0),
        ],
        "bus": lambda: [
            vst(r"Soundtheory\Gullfoss.vst3", recover=35.0, tame=35.0),
            pb.Compressor(threshold_db=-16, ratio=2.0, attack_ms=30, release_ms=200),
        ],
    },
}


# Bus-only chains (user, song02: bus processing beat full stem production — stems amplify separation noise).
BUS = {
    "B1": lambda: [vst(r"Soundtheory\Gullfoss.vst3", recover=35.0, tame=35.0),
                   pb.Compressor(threshold_db=-16, ratio=2.0, attack_ms=30, release_ms=200)],
    "B2": lambda: [vst(r"oeksound\soothe2_x64.vst3", depth=3.0, mode="soft"),
                   vst(r"Soundtheory\Gullfoss.vst3", recover=35.0, tame=35.0),
                   pb.Compressor(threshold_db=-16, ratio=2.0, attack_ms=30, release_ms=200)],
    "B3": lambda: [vst(r"oeksound\soothe2_x64.vst3", depth=3.0, mode="soft"),
                   vst(r"Soundtheory\Gullfoss.vst3", recover=35.0, tame=55.0),
                   pb.Compressor(threshold_db=-16, ratio=2.0, attack_ms=30, release_ms=200)],
    "B4": lambda: [vst(r"iZotope\RX 11 Spectral De-noise.vst3", adaptive_learning=True, noise_reduction_db=4.0,
                       tonal_reduction_db=2.0, linked_reduction_db=4.0),
                   vst(r"oeksound\soothe2_x64.vst3", depth=3.0, mode="soft"),
                   vst(r"Soundtheory\Gullfoss.vst3", recover=35.0, tame=55.0),
                   pb.Compressor(threshold_db=-16, ratio=2.0, attack_ms=30, release_ms=200)],
}


def load(take, name):
    f = sorted(glob.glob(os.path.join(take, name + ".*")))[0]
    x, sr = sf.read(f, always_2d=True, dtype="float32")
    return x, sr


def align(y, x):
    """Shift y so it lines up with x (compensates plugin latency/lookahead)."""
    n = min(len(x), len(y), 48000 * 20)
    s = slice(len(x) // 3, len(x) // 3 + n)
    c = correlate(y[s].mean(1), x[s].mean(1), mode="full", method="fft")
    lag = int(np.argmax(c[len(c) // 2 - 4800: len(c) // 2 + 4801]) - 4800)
    if lag > 0:
        y = np.concatenate([y[lag:], np.zeros((lag, y.shape[1]), y.dtype)])
    elif lag < 0:
        y = np.concatenate([np.zeros((-lag, y.shape[1]), y.dtype), y[:lag]])
    return y[: len(x)], lag


def main():
    take, out = sys.argv[1], sys.argv[2]
    rest = [a for a in sys.argv[3:] if not a.startswith("--")]
    preset = PRESETS[rest[0] if rest else "rock"]
    # The tail's mix.* is loudness-normalised + limited; vocals + instrumental is the clean pre-limiter song.
    if glob.glob(os.path.join(take, "instrumental.*")):
        v, sr = load(take, "vocals"); i, _ = load(take, "instrumental")
        n = min(len(v), len(i)); mix = v[:n] + i[:n]
    else:
        mix, sr = load(take, "mix")
    if "--bus-only" in sys.argv:
        y = mix
    else:
        stems = {s: load(take, s)[0] for s in ("vocals", "drums", "bass", "other")}
        n = min(len(mix), *(len(v) for v in stems.values()))
        mix = mix[:n]
        stems = {k: v[:n] for k, v in stems.items()}
        residual = mix - sum(stems.values())
        y = residual.copy()
        for s, x in stems.items():
            board = pb.Pedalboard(preset[s]())
            p, lag = align(board(x.T.copy(), sr).T, x)
            y += p
            print(f"{s:7s} processed, latency fixed {lag:+d} samples", flush=True)
    bus_arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--bus=")), None)
    if "--no-bus" not in sys.argv:
        chain = BUS[bus_arg]() if bus_arg else preset["bus"]()
        b, lag = align(pb.Pedalboard(chain)(y.T.copy(), sr).T, y)
        y = b
        print(f"bus     processed, latency fixed {lag:+d} samples")
    sf.write(out, y, sr, subtype="FLOAT")
    print(out, "peak %.2f" % np.abs(y).max())


if __name__ == "__main__":
    main()
