# Music workflows

Moved here from [comfyui-workflows](https://github.com/RmeKLV/comfyui-workflows). The custom nodes they use are in [`../nodes`](../nodes).

## Music — YuE2

`YuE2_Song.json` (style + lyrics → song) and `YuE2_Cover.json` (reference song → its melody,
re-sung in a new style). YuE2 3B is in ComfyUI core from **v0.36.0**; models are the
[Comfy-Org repack](https://huggingface.co/Comfy-Org/YuE2): `yue2_3b_bf16.safetensors` in
`checkpoints/`, `sheetsage2_bf16.safetensors` in `audio_encoders/`.

Each run produces one folder, named with its lyric score and seed:

```
output/audio/YuE2_song_lyr094_s831001_00001/
    master.flac   <- use this: -14 LUFS, -1 dBTP
    mix.flac  vocals  instrumental  drums  bass  other  (+ guitar / piano when present)
```

The graph: ABC melody + chord plan → song tokens → acoustic KSampler → decode → Demucs stems →
Whisper lyric score → optional vocal clean-up → stem remix + master → save. The post-processing
nodes are in [comfyui-audio-nodes](../nodes).

What measuring it showed:

- **Quality is the seed.** With the song tokens held fixed, every stage-2 sampler landed 10–20×
  closer to a 64-step reference than a change of seed moves it. So the graph uses `dpmpp_2m`
  (11 s) instead of the template's `dpm_2` (21 s, two model calls per step), and the way to a
  good song is to queue 4–6 takes and sort `yue2_scores.csv` by lyric accuracy. The score
  caught a take that skipped its second verse (63 %) next to clean ones (94 %).
- **~80 % of the time is autoregressive token generation (~53 tokens/s).** SageAttention does
  not help token-by-token decode. **Video playing in a browser halved it to 27 tokens/s.**
- **`max_duration` 360, not the template's 120.** 120 truncated a 128.6 s song; the model stops
  on its own.
- **The SUNO restoration chains below make YuE2 worse** — its output is already full-band and
  mastered. See the numbers in the audio-nodes README. The only enhancement offered is an
  optional ClearVoice SE vocal clean-up, off by default.
- A 2-minute song takes ~3.5 min end to end on an RX 7900 XTX (ROCm, Windows), stems and
  scoring included; ~5.3 min with the vocal clean-up.

**Licence:** the YuE2, SheetSage2 and YuE2-VAE weights are **CC BY-NC 4.0** — not for monetised
releases.

---

## SUNO audio restoration

`SUNO AI Voice Upscale.json` — vocal restoration for generated stems: ClearVoice separation,
envelope-gated high-frequency blending, artefact repair.

`SUNO Instrument Batch Auto.json` — batch instrument-stem restoration. Reads the stem type from the
filename and adapts crossover, gain and gating per instrument, passing bass and dark pads through
untouched rather than inventing treble that was never there.

Both require my custom nodes: **[comfyui-audio-nodes](../nodes)**.
`SUNO Instrument Batch Auto` additionally uses [ComfyUI-AudioSR](https://github.com/kijai/ComfyUI-AudioSR).

These are for audio that is actually missing its top end, as Suno stems are. Do not run them on
YuE2 output (see above).

---

