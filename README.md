# AI music video pipeline

Scripts and notes for turning AI-generated songs (ACE-Step 1.5, YuE2) into clean,
mastered tracks and code-rendered music videos.

The songs themselves (lyrics, audio, renders) are not part of this repo, and neither are
model weights or third-party tools. Only the code and playbooks are here.

## What's here

| path | what it is |
|---|---|
| `AUDIO_PLAYBOOK.md` | the measured audio pipeline: separation, vocal repair, de-cricket, fizz control, mastering, drum fixes |
| `SONGWRITING_PLAYBOOK.md` | how songs are written and prompted for ACE-Step |
| `pipeline/` | shared audio tools: reference analysis, take ranking, blind A/B, drum transcribe/render/soften/gate, mix clarity, finishing |
| `song01_paper_planes/scripts/` | the original research scripts: stem separation benchmark, vocal ensemble, vocal fix, AudioSR queue, scoring, mastering |
| `song03_porch_light/video/` | pure-code music video engine (three.js + canvas): sets, line-art singer with lip-sync, shot list as code, renderer. See `REUSE_GUIDE.md` |
| `comfyui/nodes/` | my ComfyUI custom audio nodes: hybrid HF blend, batch audio I/O, YuE2 stems / lyric score / remix + master (was `comfyui-audio-nodes`) |
| `comfyui/workflows/` | the music workflows: YuE2 song, YuE2 cover, SUNO voice upscale, SUNO instrument batch (moved from `comfyui-workflows`) |
| `licenses/LICENSES.md` | licenses of the models and samples the pipeline relies on |

## Requirements

- Generation: ComfyUI with ACE-Step 1.5, or YuE2. Install the custom nodes from `comfyui/nodes/` (see its README)
- Separation models (MelBand RoFormer, BS-RoFormer, htdemucs_ft, MDX23C DrumSep), AudioSR, SongEval
- Video: Node.js, then `npm install` in `song03_porch_light/video/`

Scripts expect song folders (`songNN_name/` with audio and lyrics) that you provide yourself.

## From a local AI song to a music video

```sh
pip install -r pipeline/requirements.txt          # core + the steps you use
(cd song03_porch_light/video && npm install)      # three.js, Playwright, fonts

# 1. generate takes in ComfyUI (ACE-Step 1.5 / YuE2, see SONGWRITING_PLAYBOOK.md), then shortlist them
python pipeline/rank_takes.py "path/to/output/audio/ACE15*"
# 2. finish the picked take (separation, de-cricket, fizz control, reference master; see AUDIO_PLAYBOOK.md)
python pipeline/finish_song.py <take> reference.wav
# 3. hand it to the video engine: audio, beat grid, lip-sync, draft lyric timing, title
cd song03_porch_light/video
python ../../pipeline/to_video.py <take>/final/FINAL_master.wav <take>/stems_v3/vocals_unwa.flac my-song \
    --lyrics lyrics.txt --title "My Song" --bpm 92
# 4. write the shot list in my-song/film.js, align the lyrics, check, render (REUSE_GUIDE.md)
node tools/render.mjs --film my-song --contact
node tools/render.mjs --film my-song
```

`to_video.py` creates the film folder from the Porch Light film when it doesn't exist yet. The film folder
must sit in `song03_porch_light/video/`, next to `tools/` and `node_modules/`. Pass `--bpm` with the tempo
you generated at (`ACE_BPM`) so the beat grid can't lock to half, double or 2/3 tempo. Its lyric timing is a
draft so the film renders straight away; replace it with forced alignment before the final render.

### Paths

Every script finds tools and models relative to this repo (`tools/`, `tools/models/`, `assets/`), so the
layout in `.gitignore` works as is. Point them elsewhere with environment variables (see `pipeline/paths.py`):
`AI_TOOLS`, `AI_MODELS`, `AI_SONGEVAL`, `AI_DRUM_KIT`, `VST3_DIR`.

## License

MIT, see `LICENSE`. Third-party models and samples keep their own licenses (`licenses/LICENSES.md`).
