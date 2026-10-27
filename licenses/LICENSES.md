# Model licences for monetised YouTube use (checked 2026-10-17, dated copies in this folder)

| model | weights licence | monetise songs as an individual creator? | notes |
|---|---|---|---|
| **YuE2-3B** (m-a-p) | CC BY-NC 4.0 **+ individual creator permission (2026-09-16)** | **Yes** — "publish, distribute, sell, license or otherwise monetize", incl. commercial platforms, no fees/royalties | Companies need a commercial licence. Credit "#YuE2" optional. Conditions: no illegal/deceptive use, **no deceptive impersonation of real artists**. "Generated outputs are not subject to the model weights' NonCommercial restriction." |
| **ACE-Step 1.5** | MIT | Yes | — |
| YuE (v1, 7B+1B) | Apache 2.0 (since 2025-01-30) | Yes | credit "YuE by HKUST/M-A-P" |
| SongBench scorer | academic only, "commercial use prohibited" | — | not used |
| SongEval scorer | CC BY-NC-SA 4.0 (README) | — | research only; production ranking uses Whisper (MIT) + Audiobox Aesthetics (CC BY 4.0) |
| Audiobox Aesthetics | CC BY 4.0 | yes (tool) | production tie-breaker |
| Suno / Udio / MusicGPT free plans | service terms | No (free plan outputs non-commercial) | paid plans required |

Rules for this channel:
- Keep the dated licence copies for every model a published song was made with.
- "In the style of <band>" is fine; never present a song as made by or featuring a real artist.
- If the channel is ever run as a company, the YuE2 row changes: contact ryuanab@connect.ust.hk.
- Not legal advice.

## Video tools (song03 "Porch Light" music video, 2026-10-18)
| tool | licence | commercial video OK? | notes |
|---|---|---|---|
| three.js / Playwright / ffmpeg | MIT / Apache 2.0 / LGPL | yes | tools only |
| Cormorant Garamond, EB Garamond fonts | SIL OFL 1.1 | yes | embedding in video allowed, no attribution required; copies in video/porch-light/fonts |
| Whisper large-v3-turbo (Faster-Whisper-XXL) | MIT | yes | used to locate lyric lines |
| torchaudio MMS_FA forced aligner | weights CC BY-NC 4.0 | grey area | used only to MEASURE word timestamps; no model output appears in the video. If ever needed strictly clean: re-time with Whisper word stamps (MIT). |
| Poly Haven assets | CC0 | yes | downloaded for the abandoned Blender test; NOT in the final video |
