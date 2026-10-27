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
