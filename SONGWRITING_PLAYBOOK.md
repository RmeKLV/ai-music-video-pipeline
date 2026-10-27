# Songwriting playbook (for ACE-Step generation)

Grows with every song. Sources: ACE-Step official songwriting guide (references/acestep_docs/SKILL_songwriting.md),
Berklee / Pat Pattison prosody principles, genre breakdowns, and our own A/B results.

## Workflow for a new song "in the style of" a reference
1. Download reference with yt-dlp -> `references/` (also the mastering reference).
2. `pipeline/analyze_reference.py` -> tempo, key, tuning, section map + energy, tonal balance.
3. Research how the reference was built (themes, riff/melody devices, arrangement) — learn the *devices*, never copy
   melody, riffs or lyrics. Our song must be original.
4. Write: one core metaphor -> title/hook -> chorus first -> verses that tell the story -> pre-chorus that lifts.
5. Caption + lyrics + params (ACE rules below). Generate N takes, auto-score, pick, then the audio pipeline.

## Craft rules
- **One core metaphor per song**, explored from several angles (ACE guide; avoids "AI-flavoured" lyrics).
- **Prosody**: the feel of the music must match the meaning — tense/unstable for conflict, resolved for release.
  Stable sections (even line counts, rhymes that close) vs unstable (odd counts, open rhymes) to drive into the chorus.
- **Contrast between sections**: verse narrow/low/talky, pre-chorus rising, chorus higher, longer notes, open vowels.
- **Hook = the title**, short, repeated, sung on long open vowels; the chorus states it at least twice.
- **Concrete images > abstract adjectives**. Red flags: adjective stacking ("neon skies, electric hearts"),
  forced rhymes, mixed metaphors, lines too long for one breath.

## ACE-Step 1.5 input rules (official guide)
- Caption = most important input: genre + mood + instruments + timbre/texture + era + production + vocal type.
  No BPM/key in the caption (use params). Avoid conflicting styles; repeat what you want emphasised.
- Lyrics: blank line between sections; tags on own lines: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Bridge]
  [Guitar Solo] [Instrumental] [Breakdown] [Outro] [Fade Out]; at most ONE modifier per tag: `[Chorus - anthemic]`.
- Vocal tags: [raspy vocal] [whispered] [falsetto] [powerful belting] [harmonies] [call and response] [ad-lib].
- 6-10 syllables per line, same position in each section within +-1-2 syllables (model aligns syllables to beats).
- UPPERCASE = shouted/belted; (parentheses) = backing vocals; vowel stretching is unstable.
- Keep caption and lyric tags consistent (instruments, energy, vocal style).
- Duration: 2 verses + 2 choruses + bridge needs 180-240 s; when unsure, longer.
- Common keys (C, G, D, Am, Em) are most stable.

## ACE-Step model settings (official docs in references/acestep_docs, vs what we run)
| setting | ours (song01-02) | official "best quality" | status |
|---|---|---|---|
| DiT | XL SFT bf16 | XL SFT ("very high" quality; base only for extract/lego/complete) | ok |
| LM (songwriter) | qwen 1.7B | **4B for >=24 GB VRAM** ("strong" composition vs "medium") | test (RAM: needs page file fix, watchdog) |
| steps | 50 | 50-64 | ok |
| shift | 1.0 | **3.0** (Gradio default) | test |
| guidance | plain CFG 2.5 (cfg 7 crackled) | 7-9 **with ADG** (not in ComfyUI) | test APG (ComfyUI node; ACE v1 values eta 0, norm 2.5, momentum -0.75) |
| LM temp / cfg / top_p | 0.85 / 2.0 / 0.9 | 0.85 / 2.0 / 0.9 (lower temp 0.7 = safer, 0.9-1.1 = more creative) | ok |
| batch | 1 per seed | 2-4 takes, keep best | doing 4 + rank_takes.py |
`queue_ace15.py` args: style lyrics takes cfg steps shift seconds lm seed; env ACE_BPM ACE_KEY ACE_PREFIX ACE_APG=1.

**Same-seed test, song02 (seed 1179511590, 215 s grunge):**
| settings | lyric acc | SongEval | crackle clicks |
|---|---|---|---|
| cfg 2.5, shift 1, 1.7B (old default) | 0.71 | 3.591 | 0 |
| cfg 2.5, shift 3 | 0.88 | 3.592 | 0 |
| **APG + cfg 7 + shift 3** | **0.87** | **3.739** (best of 7 takes) | **0** |
| 4B LM, cfg 2.5, shift 1 | 0.83 | 3.325 | 0 |
=> NEW DEFAULT: `ACE_APG=1`, cfg 7, shift 3, 50 steps, 1.7B. APG removes the cfg-7 crackle seen on song01 (plain CFG).
4B + XL now fits (page file) but commit headroom dips to ~4 GB while loading: watchdog mandatory. Not better on 1 seed;
retest with APG + shift 3 before deciding. SongEval runs lower for grunge (3.3-3.7) than pop (4.4): compare within genre only.

## Which generator (researched 2026-10-17)
SongBench (Tencent, expert-rated, 7 dimensions, 1-10) mean scores: DiffRhythm 2 4.93, LeVo 5.18, HeartMuLa 5.80,
**ACE-Step 1.5 6.04 (best open model)**, MiniMax 2.5 6.52, Suno v4.5 6.60, Mureka O2 6.67, Suno v5 6.86, Mureka V8 6.87.
=> Stay on ACE-Step; the ~0.8 gap to Suno must be closed by how we drive it (caption, settings, takes, repaint).
SongBench scorer (github.com/Tencent/SongBench, built on SongEval + MuQ) gives Vocal / Instrument / Mixing scores,
but its licence forbids commercial use -> only with the user's explicit OK.

## Caption lesson (song02, user's ears)
First song02 caption used lo-fi texture words ("raw", "gritty", "sludgy", "fuzzy", "analog", "raw production"):
user heard "too bright, mushy, buried vocal, like lowest-quality YouTube audio". Meters (mix_clarity.py,
codec_artifacts.py, Audiobox) could NOT see it: balance and vocal level were close to the real reference.
Testing a hi-fi caption (style_hifi.txt). Note: Audiobox PQ scores the real "Man in the Box" 7.22 — below our
takes — so PQ is useless for raw-sounding genres.

## Genre notes
### 90s grunge / alt-metal (ref: Alice In Chains "Man in the Box", 1990)
- Measured: ~110 BPM, E-flat tuning (half step down), minor/modal, bass-heavy dark master (+12 dB 80-250 Hz,
  steep top roll-off), crest 16 dB. Map: ~20 s riff intro, 16-bar verses, short 4-bar lifts, big repeating choruses.
- Devices: grinding mid-tempo "beat and grind" riff (Cantrell: "when we started to find ourselves");
  Phrygian/Locrian colour (b2, b5) in riffs; vocal melodies on minor pentatonic, descending lines, occasional
  out-of-key note; guitar and voice take turns (riff holds a long root note while the voice sings);
  two-part dark vocal harmonies; talk-box guitar hook; theme fused from two ideas (censorship + veal crate).

### song02 hi-fi caption test (mix_clarity.py on the tail's Demucs stems)
| take | vox_over_band | vox_presence | mid_flatness (mush) | transient_def | lyric |
|---|---|---|---|---|---|
| A old lo-fi caption, APG cfg7 (user: mushy, buried vocal) | -1.7 | +2.8 | 0.234 | 2.79 | 0.87 |
| B hi-fi caption, APG cfg7, seed 1 | -2.3 | +1.2 | 0.235 | 2.75 | 0.66 |
| C hi-fi caption, plain cfg2.5, seed 1 | -1.4 | +3.5 | **0.137** | **3.26** | 0.76 |
| D hi-fi caption, APG cfg7, seed 2 | +0.0 | +2.8 | 0.238 | 2.54 | 0.78 |
| E hi-fi caption, plain cfg2.5, seed 2 | **+1.1** | **+8.1** | **0.141** | 3.02 | 0.81 |
APG makes the midrange more noise-like (flatness 0.235 vs 0.14) on both seeds = probable "mush". The earlier APG win
(SongEval/lyrics) did not measure this. Awaiting user's ears to confirm mid_flatness as the automatic mush detector.
**User verdict (clips_round1): B (hi-fi caption + APG) > A (old caption + APG) > C, D, E — prediction from
mid_flatness was WRONG (inverse). Drop mid_flatness as a mush meter. APG stays.**
**But ALL takes judged unusable: "played in a garage, recorded on an old button phone".** Bandwidth (to ~17.8 kHz),
bass, vocal level, codec-hole and stereo meters all look like the commercial references, so the damage is in the
texture of the generation itself, invisible to every meter we have. Next test: official ACE-Step 1.5 pipeline
(ROCm Windows build) vs our ComfyUI path, same caption/lyrics/seed — is it the model or our implementation?

### YuE2 best-of-8 (song02, legacy FP32 decoder) — user blind test
- User: take2 (s699090359, lyric 0.86) ~2x better than take1 (s1758248038, lyric 0.90); take3 in between.
  AUTO RANKING WAS WRONG: lyric acc + Audiobox put take1 first. => meters can only SHORTLIST (lyric >= 0.80);
  the final pick needs ears (short clips of the top 3-4). Collect these verdicts to build a better selector later.
- Decoder blind X/Y: legacy preferred on take1, indistinguishable on take2/3 -> keep legacy default.
- Still "mid vs top songs". Complaints: instruments blend, lyrics hard to hear -> testing stem rebalance
  (pipeline/unmask_mix.py: vocal gain + 1-5 kHz instrumental dip while singing) on take2.
- Take2 remix test (V0 baseline, vocal +2/+4 dB, +2 dB with 1-5 kHz unmask dip): user "can't really hear a
  difference, maybe V3". => mix/mastering is NOT the bottleneck; the render quality of the model is.
  Levers ranked by audible effect: model choice (ACE->YuE2 ~2x) ~ take selection by ear (~2x) >> decoder/precision
  > mix rebalance/cleanup/master. Keep V3 (vocal +2 dB, 3 dB unmask) as a harmless default.
  Untested official setting left: YuE2 "32 midpoint synthesis steps" (ComfyUI uses dpmpp_2m/sgm_uniform).

### Genre choice matters (song03 "Porch Light", piano pop ballad, ref Olivia Rodrigo "drivers license")
- Chosen to dodge YuE2's weak spots found on song02: few cymbals (hi-hat hiss), mid-range vocal (hiss on belted
  highs), sparse arrangement. Style: felt piano, warm mid-range female vocal, brushed drums from verse 2, minimal
  cymbals, string pad, deep bass. 8 takes x 215 s.
- Result: lyric accuracy 90-97 % on ALL 8 takes (song02 rock: 81-90 %); Audiobox CE ~7.9 / PQ 8.3-8.4
  (song02: CE ~7.2 / PQ ~7.9). Ear pick pending (listen/takes A-D = s1324478624, s1060028101, s321168143, s424736152).
- analyze_reference.py reports double-time for slow ballads (143.6 -> really ~72 BPM): halve when > 130 for ballads.
- User picked take B (s1060028101, lyric 0.97) — "I like the chorus better". Finished with finish_v2:
  song03_porch_light/FINAL/Porch_Light_FINAL.flac (208 s, -14.0 LUFS, -1 dBTP). Vs reference: within ~2 dB
  250 Hz-8 kHz, ~3 dB darker above 8 kHz (Q1 tone was tuned on the rock song) — consider a lighter tone per genre.
- Brightness test on song03 (T0 rock "deeper" tone ... T3): user picked **T3 brightest** (high shelf +1.5 dB @7 kHz,
  no roll-off, body +2.5 dB @180 Hz kept). Ends ~1.5-5 dB brighter than the reference above 5 kHz.
  => master tone is GENRE-dependent: rock = deeper (HIGH -4, LP 13 kHz); ballad/pop = bright (HIGH +1.5, LP off).
  finish_v2.py now takes MASTER_* env overrides. song03 final: song03_porch_light/FINAL_bright/Porch_Light_FINAL.flac
