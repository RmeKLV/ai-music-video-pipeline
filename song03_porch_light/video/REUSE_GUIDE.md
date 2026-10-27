# Making the next music video from this one (Porch Light, uploaded 2026-10-18)

Everything here is a pure-code film (three.js + canvas, Motion Reel harness): no paid assets, renders on the
7900 XTX in ~14 min for 3:30 at 1440p60. Run all commands from `song03_porch_light/video/` (or a copy of it).

## What to reuse
| file | what it gives you |
|---|---|
| `porch-light/sets/ink.js` | the "Midnight Linework" look: anti-aliased line shader (1 px feather), cel fills, two palettes (navy night / cream day), the night dome (ray-chord test), wind sway, NaN guards |
| `porch-light/sets/linework.js` | the valley world builder (house with real porch structure, trees, fields kept off the road, village, poles, moths, clock, snow, air motes, grass) |
| `porch-light/sets/keeper.js` | the line-art singer: profile drawing, lip-sync from `lipsync.json`, blinks |
| `porch-light/film.js` | shot list as code, lyric lines (verse lower-third + chorus type), 9 transition types (iris, through, luma, clock, flare, whip, ink, swarm, burst, tilt), thumbnail mode at t = 300/301/302 |
| `porch-light/docs/gapfix.py` | fixes lyrics landing inside long held notes (breath gaps) - always verify moves against the vocal |
| `tools/render.mjs` | renderer with `--jpeg` (fast capture) and `--scale 1.3333` (true 1440p) |
| `../../pipeline/drum_soften.py`, `drum_tail_gate.py` | drum softening + gating the AI hum between hits (see AUDIO_PLAYBOOK.md) |

## Steps for a new song
1. Copy `porch-light/` to a new folder name next to it (e.g. `paper-planes/`), keep `tools/`, `node_modules/`, `package.json`.
2. Put the new song's beat grid + lyrics in: `uv run <motion-reel>/scripts/beats.py <film> --track song.flac --full`,
   vocal stem to `<film>/audio/stems/vocals.wav`, lyric sheet to `docs/lyrics.txt` (one line per window), then
   `uv run <motion-reel>/scripts/align.py <film>` and `python docs/gapfix.py` (check every moved line by ear/energy).
3. Rewrite the shots in `film.js` (`renderShot`, `BOUNDS`, `TRANS`). Snap every cut to a downbeat from `beats.json`;
   never repeat a transition type more than twice; keep smootherstep easing.
4. Check: contact sheet (`--contact --every 2`), strips across cuts, and the flicker scan
   (half-size render + frame-difference scan) before any full render.
5. Final: `node tools/render.mjs --film <film> --video-only --scale 1.3333 --fps 60 --jpeg --gpu`, then mux the
   approved master with ffmpeg (AAC 320k). Short: `--format 9x16 --range a:b`.
6. Thumbnails: edit `thumbDraw()` in film.js, render `--at 300,301,302`, scale to 1280x720.

## Lessons the user gave (keep them)
- Metaphor over literal illustration; physically logical scenes (supports, steps to the ground, nothing floating).
- Lyrics must hit the sung word; check held notes. Transitions varied, eased, on the music.
- Show short previews before full renders; give real time estimates.
- One heavy GPU/AI job at a time on this PC.
