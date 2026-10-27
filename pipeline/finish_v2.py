"""Finisher v2 — every step won a blind/level-matched ear test by the user on song02 (2026-10-17):
  1. full mix (vocals + instrumental, pre-limiter) -> Gullfoss (recover 35, tame 35) + glue compressor   [bus B1]
  2. premium moves on the full mix: width (side +2.5 dB >4 kHz), tight low (HPF 30, -2 dB @60, mono <120 Hz),
     hi-hat tamer (TDR Nova dynamic bell 8.5 kHz, thr -14, 3:1)                                          [P1 + hats]
  3. master_ref.py vs genre reference: EQ match 70 % with sub-bass boost capped, tone: body +2.5 dB @180 Hz,
     high shelf -4 dB @7 kHz, roll-off 13 kHz; -14 LUFS (YouTube norm), true peak -1 dBTP              [Q1 + LUFS]
Rejected by ear: effects on separated stems, soothe2, RX de-noise, tape saturation, shared room reverb.
usage: finish_v2.py <take folder> <reference.wav> <out_dir> <name>     (tools venv; CPU only)"""
import os, subprocess, sys
import soundfile as sf
from paths import MASTER

take, ref, out_dir, name = sys.argv[1:5]
here = os.path.dirname(os.path.abspath(__file__))
py = sys.executable
os.makedirs(out_dir, exist_ok=True)
bus = os.path.join(out_dir, f"{name}_1_bus.wav")
prem = os.path.join(out_dir, f"{name}_2_premium.wav")
final = os.path.join(out_dir, f"{name}_FINAL.wav")
last = lambda r: "\n".join(r.stdout.strip().splitlines()[-2:])
print(last(subprocess.run([py, os.path.join(here, "produce.py"), take, bus, "rock", "--bus-only", "--bus=B1"],
                          check=True, capture_output=True, text=True)))
print(last(subprocess.run([py, os.path.join(here, "premium.py"), bus, prem, "width,low,hats"],
                          check=True, capture_output=True, text=True)))
# defaults = rock (song02 "deeper" Q1); override per genre via env, e.g. ballad (song03, user pick T3):
#   MASTER_HIGH_DB=1.5 MASTER_LP_HZ=0
defaults = dict(MASTER_LUFS="-14", MASTER_SUB_CAP="0", MASTER_BODY_DB="2.5", MASTER_HIGH_DB="-4", MASTER_LP_HZ="13000")
env = dict(os.environ, **{k: os.environ.get(k, v) for k, v in defaults.items()})
print(last(subprocess.run([py, MASTER, prem, ref, final],
                          check=True, capture_output=True, text=True, env=env)))
x, sr = sf.read(final, always_2d=True)
sf.write(final.replace(".wav", ".flac"), x, sr, subtype="PCM_24")
print("FINAL", final, f"{len(x) / sr:.1f} s")
