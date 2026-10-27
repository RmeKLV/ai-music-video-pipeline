# AI song audio playbook

How to turn a raw AI-generated song into a clean, professional-sounding track **automatically**.
Every rule here was measured. Update it after every song: what worked, what failed, with numbers.
Scripts live in `song01_paper_planes/scripts/` (to be promoted to a shared `pipeline/` folder).

---

## 1. The pipeline

### WINNER after round 4 (user's ears, chorus): process the ORIGINAL MIX, stems only as detectors
```
mix.wav -> vocal_fix.py repair --mode instrument                (de-cricket on the full mix)
        -> vocal_fix.py tame --detector <softmin vocal stem> --target -16 --max-cut 4   (sidechain fizz control)
        -> master_ref.py <genre reference> (EQ match 70 %, RMS match, TP limiter -1 dBTP)
```
song01: unsupported-HF bursts 39.6 % -> 21.9 %, fizz -14.2 -> -16.0 dB, brightness kept by the master EQ.
Ranking: D (this) > A (master only) > stem round-trip + master > Smule variant.

### Older stem chain (lost to the above; kept for reference / stems for video)

```
generate (ComfyUI, ACE-Step 1.5 XL)  ->  STOP ComfyUI
 -> separate: 3 models (MelBand unwa, BS-RoFormer 1297, Demucs htdemucs_ft)   separate_take.py / sep_bench.py
 -> vocal ensemble: softmin of the 3 vocal stems                               ensemble_vocals.py softmin
 -> vocal HF repair: de-cricket vocal_hard                                     vocal_fix.py repair --mode vocal_hard
 -> vocal fizz control: dynamic EQ 7.5-12.5 kHz, target -20 dB, max cut 10     vocal_fix.py tame --target -20 --max-cut 10
 -> clean air: AudioSR (sdpa, overlap 2.5) + gated HF blend >12 kHz + de-cricket   queue_audiosr.py
      (vocal: cutoff 17.8 -> 24 kHz, ticks 95 -> 47/min, hf_flag stays <15 %; raw AudioSR alone = 44 % hallucinated HF)
      (instrumental: blend at 14 kHz, mode instrument — judged by ear, meters misfire on cymbals)
 -> (option) Smule Renaissance body: smule_restore.py, then band_merge.py (Smule <1.5 kHz + chain above)
 -> remix vocal + instrumental with gains fitted to the original mix           vocal_fix.py remix
 -> master to a genre reference: match EQ (70 %, +-6 dB) + RMS + look-ahead TP limiter -1 dBTP   master_ref.py
      reference = commercial track via yt-dlp ("ytsearch1:<artist> <title> official audio"), into references/
      check with finalize_master.py (tonal balance table vs reference, true peak)
 -> score: eval_audio.py, harmonic_noise.py, aes_score.py, SongEval
```

One heavy AI job at a time (32 GB RAM PC): ComfyUI OR separation OR scoring, never two.

---

## 2. Problems -> how to measure -> fix

| What you hear | Cause (measured) | Meter | Good value | Fix |
|---|---|---|---|---|
| Metallic / robotic shine on the voice | voice-locked 8-12 kHz fizz from the generator (ACE: 13 dB above YuE2, corr 0.99 with voice) | `eval_audio.py` fizz_db | -20 to -26 dB | dynamic EQ `tame` (not static EQ: makes it dull) |
| Crickets / chirps / unnatural sparkle | HF energy not supported by the band below | `eval_audio.py` hf_flag_pct (vocals only) | < 15 % | de-cricket `repair --mode vocal_hard` |
| Static / grain *inside* sung notes | noise between harmonics, mostly from the **separator** (MelBand models leak it) | `harmonic_noise.py` 300-1k band | >= 28 dB | 3-model softmin ensemble (18 -> 29 dB) |
| Muffled / not clear | generator hard-cuts at ~16 kHz | `eval_audio.py` cutoff/roll99 | content to 18-20 kHz | (testing) AudioSR + gated blend |
| Volume dips mid-note | not the separator (unwa ducks only 0.6 s/song); likely generation | `find_dips.py`, separator cross-check | — | (todo) repaint / pick better take |
| "Not human" phrases | generation itself (pitch is NOT the cause: pitch micro-variation = YuE2) | `pitch_naturalness.py` | micro_c 25-35 | (todo) repaint those sections, more takes + auto-select, or re-voice (RVC/Seed-VC/Kits.ai) |

## 3. What failed (do not retry without a new reason)

- **THE BIG ONE (round 3, user's ears): separate -> fix stems -> remix -> master LOST to just mastering the
  original mix.** The raw mix + master_ref.py sounded clearest, most air, least synthetic. Stem round-trips add
  separation artifacts and the fizz cuts took real air. Rule: the *mastered original* is the baseline every fix
  must beat; prefer processing the full mix and use stems only as detectors (sidechain), never as the audio path,
  unless a stem fix is proven better by ear against that baseline.
- **Smule Renaissance** also causes audible vocal volume dips (user, round 3).

- **Speech restorers on singing**: Resemble Enhance (lyrics 98 -> 61 %, SongEval 3.8), NovaSR, MossFormer2 SE/SR,
  the old SUNO chain on raw stems. Built for speech; they garble or add HF hallucination.
- **Static EQ cut** of the fizz band: dull, judges score it lower.
- **Hard `min` ensemble**: per-bin switching = musical noise; use `softmin`.
- **Single separator chosen on lyric accuracy only**: missed in-note static. Always measure harmonic noise.
- **Smule Renaissance as the whole vocal**: cleanest body of anything (in-note 36 dB) but blurs words
  (lyrics 96 -> 90 %) and hallucinates HF (60 % flagged). Body-only merge keeps most of the gain, still -2-3 % lyrics.
  Needs fp32 (fp16 dtype mismatch in its conv layers). 30 s per song on GPU.
- **Matchering 2**: output 3-5 dB off the reference's long-term balance (duller, thinner) with or without its
  limiter; its limiter is sample-peak only (true peak +1.5 dBTP). Replaced by master_ref.py (within +-1 dB above 250 Hz).
- yt-dlp 403 on first try: transient, a plain retry worked (was already up to date).

## 4. Judges: what each can and cannot see

- **SongEval** (whole song, 5 axes): matched ears for *generation* quality (cfg 7 vs 2.5), but is **blind to HF artifact repair** (all fixes within +-0.03).
- **Audiobox Aesthetics PQ** (Meta, CC BY 4.0): same story, 8.45-8.48 for everything; ACE raw 8.46 vs YuE2 8.48. Both mildly reward brightness.
- => For repair work use **stem meters** (fizz, hf_flag, harmonic noise, clicks, lyric_acc). Whole-song judges are for picking takes and settings.
- `clicks_min` is HF-sensitive: removing treble unmasks faint >12.5 kHz ticks (they were already there). Check the *difference signal* to prove processing did not create clicks.
- `hf_flag_pct` misfires on instrumentals (cymbals look like artifacts): YuE2 instrumental reads 62 %.

## 5. Tool gotchas (this PC: RX 7900 XTX, ROCm, Windows)

- **ComfyUI decodes audio VAEs in FLOAT16 by default on this GPU** (log: "VAE load device ... dtype: torch.float16").
  The official YuE2 preset uses an FP32 VAE. Launch ComfyUI with `--fp32-vae` for music (test running 2026-10-17).
- ComfyUI's bundled YuE2 decoder == official `m-a-p/YuE2-Vae` (listening decoder, identical weights).
  `YuE2-Vae-legacy` (benchmark decoder of the 6.96 SongBench result) differs ~4 % median per weight; copy in models/vae.

- ClearVoice picks the GPU via `nvidia-smi` -> silently CPU on AMD. Patched `clearvoice/networks.py` (backup `.orig_nvidia_smi`).
- `rotary-embedding-torch` must be 0.6.x in the tools venv, or RoFormers output silence.
- `torchaudio.load` is broken (torchcodec): load with soundfile.
- Never `pip install` packages that pull torch into the tools venv: use `uv pip install --no-deps`.
- SageAttention: do not use for audio models (AudioSR: `attention_backend=sdpa`).
- audio-separator peak-normalises outputs: gain-match stems before combining.

## 6. Generation-side levers (biggest wins, to automate next)

- ACE cfg 2.5 >> cfg 7 (crackle clicks 79 -> 9; SongEval 3.80 -> 4.46).
- ACE docs: thinking mode, batches of 2-4 takes, Repaint for flawed sections only.
- Plan: generate N takes -> auto-score (SongEval + stem meters + lyric acc) -> keep best -> repaint flagged sections.

### YuE2 decoder test (song02 take 4, seed 1566112829, same latent — waveform corr 1.000)
- fp16 vs fp32 decode: difference -48.9 dB below the music (-38 dB above 4 kHz). Small; keep `--fp32-vae` (free).
- FP32 + plain (non-tiled) VAEDecodeAudio on 215 s: commit ran out, watchdog killed ComfyUI. queue_yue2.py now
  forces VAEDecodeAudioTiled (tile 1024, overlap 32 = official decode_core_frames 1024 / halo 16).
- Legacy (benchmark) decoder: clearly different render (corr 0.961). Ear test pending (clips_round3_decoder).

## Production chain (2026-10-17, pipeline/produce.py)
- Effects engine: Spotify Pedalboard 0.9.26 (tools venv, --no-deps) + the user's VST3s, all scriptable headless:
  soothe2 (56 params), spiff, Gullfoss (recover/tame/brighten/bias/boost), TDR Nova, iZotope RX 11 (De-ess,
  De-crackle, Spectral De-noise...), Accusonus ERA6. Verified they process (not bypass/demo) on real audio.
- produce.py: per-stem chains (vocals: HPF, RX De-ess, soothe2, comp, presence/air EQ, plate reverb send with
  30 ms predelay, 110 ms slapback; drums: spiff, parallel comp, small room; bass: comp + parallel saturation;
  other/guitars: mud cut, soothe2, 2.8 kHz pocket for the voice, reverb send) + residual + bus (Gullfoss, glue comp),
  every processed stem auto-aligned by cross-correlation (plugin latency). Rebuild base = vocals + instrumental
  (tail's mix.* is already limited). Full song in ~40 s on CPU.
- Official YuE2 midpoint solver: custom_nodes/yue2_midpoint.py + env YUE2_SAMPLER=midpoint (SamplerCustom).
  Same seed vs dpmpp_2m: corr 0.997, difference -24.8 dB. 12 min per 237 s song (2x model evals).
- A stuck Smule process (PID 21328) from the fp16 attempt survives taskkill and burns 1 core: reboot clears it.
- User verdict (take2, same chorus): 3 bus-only (Gullfoss 35/35 + glue comp) BEST — "less noisy hi-hat".
  4 full stem production WORST — "too noisy, static noise so much": stem chains (spiff, compressors, presence/air
  EQ) amplify Demucs separation noise. Midpoint solver: no comment (not clearly better).
  => RULE CONFIRMED: process the full mix; never run character effects on separated stems.
- Bus variants measured: soothe2 soft depth 3 changes HF by -12.8 dB rel.; Gullfoss tame 35->55 barely changes
  output (-42 dB); RX Spectral De-noise adaptive (4/2/4 dB) removes a lot (-2.3 dB level) — treats sustained
  distorted guitar as noise. Ear test B1 / B2 / B4 pending.
- User (bus variants): B1 = B2 (soothe2 on bus inaudible -> dropped). B4 (RX Spectral De-noise adaptive) tames the
  loud hi-hats but they still sound synthetic, "no HQ sound" (generator's cymbal timbre). Whole song "too bright,
  could be deeper". => master_ref.py got a tone stage (env MASTER_LOW_DB @120 Hz shelf, MASTER_HIGH_DB @7 kHz shelf,
  MASTER_LP_HZ roll-off) after the EQ match, before the limiter. Test D0 (B4) / D1 (+2/-3) / D2 (+2/-3, LP 14k) /
  D3 (B1 + D2 tone).
- User (tone test): **D3 best** = B1 bus (Gullfoss 35/35 + glue comp, NO RX, NO soothe2) + master tone
  (+2 dB @120 Hz, -3 dB @7 kHz, LP 14 kHz). => pipeline/finish_v2.py is the default finisher.
  song02 FINAL: song02_rust_in_the_water/FINAL/Rust_in_the_Water_FINAL.flac (237 s, -1 dBTP).
  Note: sub 30-80 Hz ends ~8 dB above the Man-in-the-Box reference (EQ match + shelf) — watch for boom.
- "Premium feel" test (pipeline/premium.py, before master): P1 width (side +2.5 dB >4 kHz) + tight low
  (HPF 30, -2 dB @60 Hz, mono <120 Hz); P2 tape (tanh, pre/de-emphasis, 35 % parallel); P3 all + shared short room.
- Premium test: user "probably P3 (all moves), but they all sound distorted at some point". Checked: no digital
  clipping anywhere in the chain (float processing; raw YuE2 decode peaks +1.8 dBFS but is never clipped), limiter
  gain reduction in that chorus = 0 dB (>1 dB on 0.2 % of the whole song). => the distortion is not added by us;
  suspected in the generation (distorted-guitar timbre / AR artifacts). Raw-vs-P3 ear check sent (listen/raw_vs_p3).
- User: raw AI output sounds LESS broken than P3; "bomb explosion on old speakers" ~12 s into the P3 clip.
  Low-band analysis showed no sub spike there (same in all versions) -> tape saturation + shared room smear the
  drum hits. Tape and room REMOVED. P1 (width >4 kHz + tight mono low end) = best premium move.
- master_ref.py: MASTER_BODY_DB (peak 180 Hz, Q 0.8) for depth without boom; MASTER_SUB_CAP=0 stops the reference
  match from boosting <90 Hz. Test Q0 (P1) / Q1 (body +2.5, high -4, LP 13k) / Q2 (body +4, high -5, LP 12k).
- Mastering principles to adopt (user question): minimal moves; dynamic EQ (TDR Nova) only when a range spikes
  (hi-hats) instead of static cuts/RX; master to the platform (YouTube ~ -14 LUFS integrated, -1 dBTP) instead of
  matching a loud CD reference — keeps punch and verse/chorus contrast.
- User: **Q1 best** (P1 width+tight low, master: MASTER_SUB_CAP=0, BODY +2.5 dB @180 Hz, HIGH -4 dB @7 kHz, LP 13 kHz).
- Loudness: song02 FINAL measured -13.6 LUFS (pyloudnorm, tools venv) — already at the YouTube norm. master_ref.py
  now takes MASTER_LUFS=-14 and prints integrated LUFS.
- TDR Nova as hi-hat dynamic EQ (premium.py move "hats"): Nova's threshold is NOT the band level in dBFS.
  Calibrated on song02 (bell 8.5 kHz, Q 0.8, 3:1, 1/50 ms): thr -24 -> -7.7 dB avg (way too much), -18 -> -3.7,
  **-14 -> -1.6 avg / -4.4 on loudest 5 %**, -10 -> -0.5 / -2.1. Always calibrate per song by measuring the cut.
  Ear test R0 (Q1) vs R1 (Q1 + hats) pending.
- User: **R1 (Q1 + whole-mix hi-hat tamer) better than R0**. Locked into pipeline/finish_v2.py (bus B1 -> premium
  width,low,hats -> master Q1 tone + MASTER_LUFS=-14). song02 FINAL_v2: -14.0 LUFS, -1 dBTP, 237 s.
- Drums-only tamer (premium.py move hats_drums, env PREMIUM_DRUMS=<drum stem>): Nova on the drum stem, only the
  difference (pure reduction) is added to the mix. Drum-stem calibration: thr -24 -> -3.5 avg/-10.8 spikes,
  -20 -> -1.7/-8.7, **-16 -> -0.6/-6.1**, -12 -> -0.2/-3.6. Ear test R1 (whole mix) vs R2 (drums only) pending.

## Seeing the bad moments (pipeline/find_bad_moments.py, 2026-10-17)
- User: "fix every track individually"; drums sound artificial; vocals break a bit on loud notes.
- Averages don't show it: on song02 loud vocal notes are NOT harsher (2.5-4.5 kHz share -19.7 vs -19.1 dB) or
  grainier on average (harmonics-vs-noise loud >= normal). The damage is in specific MOMENTS.
- Detector v1 (flatness/HF/flux z-scores) flagged normal note onsets ("spectral jump") -> v2 ignores +-80 ms around
  onsets and scores noise-likeness / HF burst inside sustained sound, per loudness band (robust z). v2 vocals:
  0:46.0 (z 16.7), 0:54.7, 0:59.6, 1:44.6, 3:14.6; bass normal (z ~3); guitars 1:54.0 (z 9).
- Spectrograms (PNG per suspect, I inspect them): at 0:46 the harmonics fade and the note dissolves into hiss;
  at 0:59.6 the note's top above 2 kHz turns into an 8-12 kHz noise wash. The vocal stem also carries a constant
  bright hiss bed to 16 kHz under the harmonics (bleed + generation). Awaiting user confirmation of the clips.

## Drum re-creation (2026-10-17)
- User: drums sound artificial; hi-hats are mostly hiss. Spectrogram confirms: the AI drum stem has a constant
  4-16 kHz noise wash between hits. EQ/de-noise can't turn hiss into cymbals -> REPLACE with real samples.
- Kit: Big Rusty Drums (Karoryfer, CC0, github sfzinstruments/karoryfer.big-rusty-drums) in assets/drums/big_rusty;
  kick 14 vel layers x4 RR, snare 10x4 (top/btm/oh mics), hat closed 6x4, open 4x4, crash; close mics mono + OH stereo.
  Licence copy: licenses/BigRustyDrums_LICENSE_2026-10-17.txt.
- pipeline/drum_transcribe.py v2: one onset per hit, classified by band jumps (kick 35-120, snare 150-400 + 1.5-5k,
  hat 7-16k, crash = sustained). song02: 526 onsets -> kick 264, snare 165, hat 286, crash 1. Check PNG.
  (v1 per-band peak picking double-counted: 813 kicks.)
- pipeline/drum_render.py: velocity -> layer, RR rotation, hats closed unless the next hat is >= 0.8 s away (open,
  choked at next hat). Rendered drums were +7.9 ms late (onset detector marks after the start) -> align by
  cross-correlating band envelopes with the AI drum stem (0 residual).
- Mixes: replace = instrumental - AI drums + new drums (RMS-matched, +2.7 dB); layer = + new drums at -3 dB.
  Then bus B1 + premium width,low + Q1 master. Ear test pending (listen/drums_real).
- User (drums_real): 3 replace = BAD (wrong drums/notes, too quiet, other instruments dip on hits); 2 layered = maybe best.
  Measured: the bus glue compressor ducks the vocal band -2.5 dB at every kick/snare in the layered mix (pumping)
  -> add real drums AFTER the bus. Real kit was too quiet: per-drum match at the AI's own hits needed kick +2.7,
  snare +8.0, cymbals +6.6 dB (overall RMS match was dominated by the AI hiss).
- Drum transcription models: ADTOF = CC BY-NC-SA (no), ADTOF-pytorch = no licence (no), ADTLib = BSD but old TF.
  DrumSep (MDX23C, aufr33/jarredou, in audio-separator: kick/snare/toms/hh/ride/crash) used for ANALYSIS only.
  Crashes on ROCm GPU (MIOpen instance-norm kernel compile error) -> run on CPU (HIP_VISIBLE_DEVICES="").
- Hiss research: no open neural model for AI-music hiss exists; commercial web tools only; deshimmer (MIT, DSP,
  5-12 kHz) is the open option (needs user OK to run). Built pipeline/drum_hiss_gate.py: drum stem >4 kHz only open
  for a natural decay after each hit (hat .12 s, snare .25, crash 1.2), -14 dB between; reduction-only (delta).
  Each AI hit still carries a long hissy tail, so gating alone is partial.
- L2 = hiss-gated AI drums -> bus B1 -> width,low -> + real kick/snare/cymbals (per-drum matched, -3 dB, bus-level
  compensated) -> Q1 master; L3 = same at 0 dB. Limiter >3 dB on 0.1 % (L2) / 0.5 % (L3) of samples.
- User (drums_v2): picked 1 = the FIRST layered version (real kit -3 dB pre-bus, flat RMS gain) over the hiss-gated
  + per-drum + post-bus versions, then: "give up on this — no way to get the right drums across the whole song if
  you miss hi-hats". DECISION: drum re-creation is a dead end for now (transcription misses/mislabels hits; hat
  detection weakest). Keep drum_* scripts for later; revisit only with a commercially licensed, accurate drum
  transcriber.
- song02 FINAL_v3 = layer_premium (real kit layered softly under AI drums) + Q1 master, -14.0 LUFS, -1 dBTP:
  song02_rust_in_the_water/FINAL_v3/Rust_in_the_Water_FINAL.flac

## Drum softening (song03 "Porch Light", 2026-10-18)
- User: drums "too robotic sometimes" (stem sent: drums.flac). Picked "softer + roomier" over real-kit layering / verse drop.
- pipeline/drum_soften.py: drum stem only, swapped into the instrumental (instrumental - drums + soft(drums)), then the
  unchanged finish_v2 chain (ballad env MASTER_HIGH_DB=1.5 MASTER_LP_HZ=0, ref drivers license). soft() = level trim,
  transient softening (fast vs slow envelope), hiss gate >5 kHz between hits, drums-only small room (synthetic IR,
  10 ms predelay, 250 Hz-6 kHz). NOTE: a drums-only room is OK; the rejected one (song02) was a SHARED room.
- Blind A/B (32 s, pre-chorus into chorus 2): user picked S2 = level -5, attack -6, room -12, gate -14 over the
  release and over S1 (-3/-3.5/-16/-10). New master: song03_porch_light/FINAL_v2_softdrums/Porch_Light_FINAL.flac.
- Follow-up (same day): user still heard "hit, then flickering static hum" at 1:29. Soloed stems (bass/drums/other/vocals,
  loudness-matched) let the user point at it: the DRUM stem's tail between hits (mostly low end, not the >5 kHz hiss).
  Lesson: ask the ear with soloed stems before guessing; level/attack/hiss gate/room barely moved the tail
  (hit-to-tail drop 18.5 -> 17.1 dB). Fix = full-band tail gate in drum_soften.py (env FULLGATE=-40 TAIL=0.06,
  NOTCH="165,9", room off): drop 36.7 dB; user approved by ear. Master: song03_porch_light/FINAL_v3_gateddrums.
- Round 3: G2's full gate also killed the 2:04 crescendo into chorus 2 (user: "weird bug 2:02-2:05", 8 dB hole).
  Automatic "keep rises / keep loud" rules failed by ear: the hum itself swells and is loud (~-40 dBFS 20 ms RMS),
  so any level/rise rule reopened the buzz and caused dips. Working fix = approved G2 everywhere + the ORIGINAL
  drum stem in 123.6-125.6 s (60 ms crossfades). Verified: window matches release (-26.2 vs -26.5 dB), elsewhere
  = G2 within 0.04 dB. User approved. Master: song03_porch_light/FINAL_v4/Porch_Light_FINAL.flac.
  Lesson: when a heuristic can't separate artefact from music, patch the flagged spot surgically and verify
  numerically against the approved version before sending clips.
