"""Hand a finished song to the video engine: master + vocal stem (+ the ACE/YuE lyric sheet) -> a film folder that
song03_porch_light/video/tools/render.mjs renders. The step between "the song is done" and "shoot the video".
If <film> has no code yet it is created from the Porch Light film (index.html, film.js, lib/, sets/, docs/gapfix.py);
then rewrite its shot list (film.js: TRANS, BOUNDS, renderShot) for the new song, see REUSE_GUIDE.md.

Writes into <film>:
  audio/mix.wav           the master (render.mjs muxes it under the picture)
  audio/stems/vocals.wav  the vocal stem (forced alignment, docs/gapfix.py)
  beats.json              measured grid: bpm, period, offset (= first downbeat), beats, downbeats, bar_energy
  film.json               duration = song length, title (--title; shown in the title card and thumbnails)
  lipsync.json            {rate: 100, open: [...]} mouth openness 0..1 from the vocal envelope (180-3800 Hz)
  lyrics.json             DRAFT word timing: words spread over the sung frames by syllable count, so the film renders
                          and lines show up near the voice. Before the final render replace it with forced alignment
                          (motion-reel align.py over docs/lyrics.txt), then docs/gapfix.py, and check by ear.
  docs/lyrics.txt         alignment windows (@ t0 t1 Section) + one sung line per row, the input align.py expects
Existing beats.json / lipsync.json / lyrics.json / docs/lyrics.txt are kept (they may be hand-tuned) unless --force.
--bpm N: the tempo the song was generated at (ACE_BPM); avoids half/double/2-3 tempo errors. Check the printed bpm.
--downbeat SECONDS: the time of any bar's first beat, when the detected downbeat is a beat off.

usage: to_video.py <master.wav|flac> <vocals stem> <film dir> [--lyrics lyrics.txt] [--title "Song Name"] [--bpm N] [--downbeat S] [--force]"""
import argparse, json, os, re, shutil, sys
import numpy as np
import soundfile as sf
import librosa
from scipy.ndimage import binary_closing, binary_opening
from scipy.signal import butter, sosfiltfilt

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "song03_porch_light", "video", "porch-light")
CODE = ["index.html", "film.js", "lib", "sets", os.path.join("docs", "gapfix.py")]
SECTIONS = ["pre-chorus", "post-chorus", "chorus", "verse", "bridge", "intro", "outro", "hook", "refrain",
            "breakdown", "interlude", "instrumental", "guitar solo", "solo", "drop", "fade out"]
FPS_LIP = 100


def beat_grid(y, sr, downbeat=None, bpm=None):
    """Beat grid t = offset + k * period: librosa's tracker (started at the generation BPM when known), then the
    period at which every tracked beat is phase-coherent (robust to dropped/doubled beats over a long song), then
    least squares on the inliers."""
    hop = 128
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)   # mean over bands: median blurs kick and hats
    _, fr = librosa.beat.beat_track(onset_envelope=env, sr=sr, hop_length=hop, tightness=400, start_bpm=bpm or 120)
    t = librosa.frames_to_time(fr, sr=sr, hop_length=hop)
    if len(t) < 8:
        sys.exit("fewer than 8 beats detected: is this a song with a pulse?")
    p0 = 60 / bpm if bpm else float(np.median(np.diff(t)))
    cand = np.linspace(p0 * 0.97, p0 * 1.03, 3001)
    period = float(cand[np.argmax(np.abs(np.exp(2j * np.pi * t[None] / cand[:, None]).mean(1)))])
    offset = float(np.angle(np.exp(2j * np.pi * t / period).mean()) / (2 * np.pi) * period)
    k = np.round((t - offset) / period)
    keep = np.abs(t - (offset + period * k)) < 0.25 * period
    for _ in range(4):
        (offset, period), *_ = np.linalg.lstsq(np.stack([np.ones(keep.sum()), k[keep]], 1), t[keep], rcond=None)
        resid = t - (offset + period * k)
        keep = np.abs(resid) < max(0.006, 2.5 * np.median(np.abs(resid[keep])))
    offset %= period
    dur = len(y) / sr
    beats = offset + period * np.arange(int((dur - offset) / period) + 1)
    if downbeat is not None:
        phase = int(round((downbeat - offset) / period)) % 4
    else:
        # which of every 4 beats is the 1: chords change on the bar line (weight 1), the kick (weight 0.5)
        ch = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
        ct = librosa.times_like(ch, sr=sr, hop_length=512)
        B = np.array([ch[:, (ct >= a) & (ct < b)].mean(1) if np.any((ct >= a) & (ct < b)) else np.zeros(12)
                      for a, b in zip(beats[:-1], beats[1:])])
        B /= np.linalg.norm(B, axis=1, keepdims=True) + 1e-9
        flux = np.r_[0.0, 1 - np.sum(B[1:] * B[:-1], 1), 0.0][: len(beats)]
        low = librosa.onset.onset_strength(y=sosfiltfilt(butter(4, 150, "low", fs=sr, output="sos"), y), sr=sr, hop_length=hop)
        kick = np.interp(beats, librosa.times_like(low, sr=sr, hop_length=hop), low)
        z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
        phase = int(np.argmax(z(np.array([np.median(flux[p::4]) for p in range(4)])) +
                              0.5 * z(np.array([kick[p::4].mean() for p in range(4)]))))
    offset += phase * period                       # beat 0 = first downbeat; a pickup gets negative beats
    n0 = -int(offset / period)
    ks = np.arange(n0, int((dur - offset) / period) + 1)
    bt = offset + period * ks
    bar = 4 * period
    bar_e = [float(np.sqrt(np.mean(y[int((offset + i * bar) * sr): int((offset + (i + 1) * bar) * sr)] ** 2) + 1e-12))
             for i in range(int((dur - offset) / bar))]
    return {"bpm": round(60 / period, 3), "period": round(float(period), 6), "offset": round(float(offset), 5),
            "beats": [round(float(x), 5) for x in bt], "downbeats": [round(float(x), 5) for x, k in zip(bt, ks) if k % 4 == 0],
            "bar_energy": [round(e, 4) for e in bar_e], "fit_inliers": int(keep.sum()),
            "fit_residual_ms": round(float(np.sqrt(np.mean(resid[keep] ** 2))) * 1000, 2)}


def vocal_envelope(v, sr):
    """dB level of the singing band at FPS_LIP frames per second (30 ms windows)."""
    x = sosfiltfilt(butter(4, [180, 3800], "band", fs=sr, output="sos"), v)
    hop, win = sr // FPS_LIP, int(0.03 * sr)
    x2 = np.pad(x ** 2, (win // 2, win))
    c = np.r_[0, np.cumsum(x2)]
    n = int(np.ceil(len(v) / hop))
    idx = np.arange(n) * hop
    return 10 * np.log10((c[idx + win] - c[idx]) / win + 1e-12)


def parse_sheet(path):
    """ACE-Step / YuE lyric sheet -> [(section, line)]. Section tags set the section ([Verse 2] -> Verse,
    [Chorus - anthemic] -> Chorus); vocal-style tags ([whispered], [harmonies]) and blank lines are skipped."""
    out, section = [], "Verse"
    for raw in open(path, encoding="utf-8").read().splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("[") and s.endswith("]"):
            name = s[1:-1].split(" - ")[0].strip().lower()
            name = re.sub(r"\s*\d+$", "", name)
            if name in SECTIONS:
                section = "-".join(w.capitalize() for w in name.replace(" ", "-").split("-"))
            continue
        out.append((section, s))
    return out


def syllables(w):
    return max(1, len(re.findall(r"[aeiouy]+", w.lower().rstrip("e")) or [1]))


def draft_timing(sheet, sung):
    """Spread the words over the sung frames (FPS_LIP grid) in order, each word's share = its syllables."""
    words = [(li, w) for li, (_, line) in enumerate(sheet) for w in line.split()]
    frames = np.flatnonzero(sung)
    if not words or not len(frames):
        return []
    cum = np.r_[0, np.cumsum([syllables(w) for _, w in words])]
    at = lambda c: float(frames[min(len(frames) - 1, int(c / cum[-1] * len(frames)))]) / FPS_LIP
    lines = []
    for li, (sec, text) in enumerate(sheet):
        ws = [{"w": w, "t0": round(at(cum[k]), 3), "t1": round(at(cum[k + 1] - 0.5), 3), "score": None}
              for k, (lj, w) in enumerate(words) if lj == li]
        if ws:
            lines.append({"text": text, "section": sec, "t0": ws[0]["t0"], "t1": max(ws[-1]["t1"], ws[0]["t0"] + 0.3), "words": ws})
    return lines


def windows(lines):
    """align.py windows: consecutive lines of one section, at most 4 lines / 20 s per window."""
    out, cur = [], []
    for l in lines:
        if cur and (l["section"] != cur[0]["section"] or len(cur) == 4 or l["t1"] - cur[0]["t0"] > 20):
            out.append(cur); cur = []
        cur.append(l)
    if cur:
        out.append(cur)
    rows = ["# alignment windows drafted by pipeline/to_video.py: check them against the vocal, then run align.py"]
    for w in out:
        rows.append(f"@ {max(0.0, w[0]['t0'] - 0.6):.2f} {w[-1]['t1'] + 0.6:.2f} {w[0]['section']}")
        rows += [l["text"] for l in w]
    return "\n".join(rows) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("master"); ap.add_argument("vocals"); ap.add_argument("film")
    ap.add_argument("--lyrics"); ap.add_argument("--title"); ap.add_argument("--bpm", type=float); ap.add_argument("--downbeat", type=float); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    film = a.film
    keep = lambda p: os.path.exists(p) and not a.force
    if not os.path.exists(os.path.join(film, "index.html")):
        for c in CODE:
            src, dst = os.path.join(TEMPLATE, c), os.path.join(film, c)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, dst)
        print(f"new film {film}: code copied from porch-light; rewrite TRANS / BOUNDS / renderShot in film.js")

    x, sr = sf.read(a.master, always_2d=True)
    v, vsr = sf.read(a.vocals, always_2d=True)
    dur = len(x) / sr
    if abs(len(v) / vsr - dur) > 0.1:
        print(f"warning: vocal stem is {len(v) / vsr:.2f} s, master {dur:.2f} s: stems from another render?")
    os.makedirs(os.path.join(film, "audio", "stems"), exist_ok=True)
    os.makedirs(os.path.join(film, "docs"), exist_ok=True)
    sf.write(os.path.join(film, "audio", "mix.wav"), x, sr, subtype="PCM_24")
    sf.write(os.path.join(film, "audio", "stems", "vocals.wav"), v, vsr, subtype="PCM_24")

    p = os.path.join(film, "beats.json")
    if keep(p):
        grid = json.load(open(p)); print("kept beats.json")
    else:
        grid = beat_grid(librosa.resample(x.mean(1), orig_sr=sr, target_sr=22050), 22050, a.downbeat, a.bpm)
        json.dump(grid, open(p, "w"), indent=1)
        print(f"beats.json: {grid['bpm']} bpm, first downbeat {grid['offset']:.3f} s, {len(grid['downbeats'])} bars, "
              f"fit {grid['fit_inliers']} beats / {grid['fit_residual_ms']} ms rms")

    p = os.path.join(film, "film.json")
    cfg = json.load(open(p)) if os.path.exists(p) else {}
    cfg["duration"] = round(dur, 3)
    if a.title:
        cfg["title"] = a.title
    json.dump(cfg, open(p, "w"), indent=1)

    db = vocal_envelope(v.mean(1), vsr)
    top = np.percentile(db, 97)
    opn = np.clip((db - (top - 24)) / 24, 0, 1) * (db > -55)
    p = os.path.join(film, "lipsync.json")
    if keep(p):
        print("kept lipsync.json")
    else:
        json.dump({"rate": FPS_LIP, "open": [round(float(o), 3) for o in opn]}, open(p, "w"))
        print(f"lipsync.json: {len(opn)} frames, mouth open (>0.3) {np.mean(opn > 0.3) * 100:.0f}% of the song")

    p, pt = os.path.join(film, "lyrics.json"), os.path.join(film, "docs", "lyrics.txt")
    if keep(p):
        print("kept lyrics.json")
    else:
        lines = []
        if a.lyrics:
            sung = binary_opening(binary_closing(db > top - 22, np.ones(25)), np.ones(10))   # bridge 0.25 s, drop < 0.1 s
            lines = draft_timing(parse_sheet(a.lyrics), sung)
            if not keep(pt):
                open(pt, "w", encoding="utf-8").write(windows(lines))
        json.dump({"lines": lines}, open(p, "w"), indent=1)
        print(f"lyrics.json: {len(lines)} lines, DRAFT timing" + ("" if a.lyrics else " (no --lyrics: instrumental)"))
    print(f"-> {film}   next: rewrite the shot list, then from song03_porch_light/video:\n"
          f"   node tools/render.mjs --film <film> --contact      (contact sheet, one frame per beat)")


if __name__ == "__main__":
    main()
