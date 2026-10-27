#!/usr/bin/env bash
# Score every vocal candidate of one song: stem metrics + remix with the RoFormer instrumental + SongEval.
# Run with ComfyUI STOPPED (SongEval needs ~13 GB RAM).  usage: score_vocalfix.sh ace|yue2
set -e
song=$1
ROOT="D:/Editing/Youtube/AI/song01_paper_planes"
PY="D:/Editing/Youtube/AI/tools/.venv/Scripts/python.exe"
OUT="$ROOT/analysis/vocalfix/$song"
V="$ROOT/analysis/sepbench/$song/melrof_kim_unwa"
case $song in
  ace)  MIX=$(ls D:/ComfyUI_windows_portable/ComfyUI/output/audio/ACE15xl_1.7b_cfg2.5_*s678686318*/mix.wav | head -1) ;;
  yue2) MIX=$(ls D:/ComfyUI_windows_portable/ComfyUI/output/audio/YuE2_song_lyr088_s899001831_*/mix.flac | head -1) ;;
esac
mkdir -p "$OUT/cand" "$OUT/remix"
cp "$V/vocals.flac" "$OUT/cand/${song}_raw.flac"
for f in D:/ComfyUI_windows_portable/ComfyUI/output/audio/vocalfix/${song}_*.flac; do
  b=$(basename "$f"); cp "$f" "$OUT/cand/${b%_0000*}.flac"
done
"$PY" "$ROOT/scripts/eval_audio.py" --whisper "$OUT"/cand/*.flac | grep '^{'
for f in "$OUT"/cand/*.flac; do
  b=$(basename "$f" .flac)
  "$PY" "$ROOT/scripts/vocal_fix.py" remix "$MIX" "$V/vocals.flac" "$V/instrumental.flac" "$f" "$OUT/remix/$b.wav"
done
cd D:/Editing/Youtube/AI/tools/SongEval && "$PY" eval.py -i "$OUT/remix" -o "$OUT/songeval" > /dev/null 2>&1
"$PY" - "$OUT/songeval/result.json" <<'EOF'
import json, sys
r = json.load(open(sys.argv[1]))
for k, v in sorted(r.items(), key=lambda kv: -sum(kv[1].values())):
    print(f"{k:28s} mean {sum(v.values()) / 5:.3f}  " + "  ".join(f"{a[:4]} {b:.2f}" for a, b in v.items()))
EOF
