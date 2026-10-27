import sys, glob, json, os
from faster_whisper import WhisperModel
m = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8")
for d in sorted(glob.glob(r"D:/ComfyUI_windows_portable/ComfyUI/output/audio/YuE2_song_lyr*")):
    segs, _ = m.transcribe(d + "/vocals.flac", language="en", vad_filter=False, word_timestamps=True)
    out = []
    for s in segs:
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": [{"w": w.word.strip(), "s": w.start, "e": w.end} for w in s.words]})
    json.dump(out, open(d + "/whisper_words.json", "w"), indent=1)
    print("==", os.path.basename(d), flush=True)
    for s in out: print(f"  {s['start']:6.1f} {s['text']}", flush=True)
