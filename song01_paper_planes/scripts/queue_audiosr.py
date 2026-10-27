"""Bandwidth regeneration ('air') through ComfyUI: AudioSR on a stem, then the SUNO-chain blend that adds only
the regenerated high band (above crossover) onto the original, gated by its envelope, then de-cricket.
Saves output/audio/audiosr/<tag>_sr (raw AudioSR) and <tag>_air (blended + repaired).
usage: queue_audiosr.py <file in ComfyUI/input> <tag> [crossover_hz=12000] [repair_mode=vocal]"""
import json, sys, time, urllib.request

HOST = "http://127.0.0.1:8188"
src, tag = sys.argv[1], sys.argv[2]
xover = float(sys.argv[3]) if len(sys.argv) > 3 else 12000.0
mode = sys.argv[4] if len(sys.argv) > 4 else "vocal"
p = {
    "in": {"class_type": "LoadAudio", "inputs": {"audio": src}},
    "sr": {"class_type": "AudioSR", "inputs": {
        "audio": ["in", 0], "ddim_steps": 50, "guidance_scale": 3.5, "seed": 42, "model": "audiosr_basic_fp32.safetensors",
        "chunk_size": 15.0, "overlap": 2.5, "unload_model": True, "show_spectrogram": False,
        "attention_backend": "sdpa", "dtype": "fp32", "use_torch_compile": False}},
    "blend": {"class_type": "HybridHFBlend", "inputs": {
        "base_audio": ["in", 0], "donor_audio": ["sr", 0], "crossover_hz": xover, "gate_low_db": -64.0,
        "gate_high_db": -44.0, "hf_gain": 1.0, "release_ms": 200.0, "hf_ceiling": 0.6}},
    "repair": {"class_type": "HFArtifactRepair", "inputs": {"audio": ["blend", 0], "mode": mode,
                                                           "detect_only": False, "lowpass_hz": 0.0}},
    "s_sr": {"class_type": "SaveAudio", "inputs": {"audio": ["sr", 0], "filename_prefix": f"audio/audiosr/{tag}_sr"}},
    "s_air": {"class_type": "SaveAudio", "inputs": {"audio": ["repair", 0], "filename_prefix": f"audio/audiosr/{tag}_air"}},
}
req = urllib.request.Request(HOST + "/prompt", data=json.dumps({"prompt": p}).encode(),
                             headers={"Content-Type": "application/json"})
try:
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
except urllib.error.HTTPError as e:
    sys.exit(e.read().decode())
print("queued", pid, flush=True)
t = time.time()
while True:
    time.sleep(5)
    h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
    if pid in h:
        st = h[pid]["status"]
        print(st.get("status_str"), f"{time.time() - t:.0f}s")
        for m in st.get("messages", []):
            if m[0] == "execution_error":
                print(json.dumps(m[1])[:1500])
        break
