"""Queue the vocal-restoration candidates for one vocal stem through ComfyUI's API.
Every candidate is saved as output/audio/vocalfix/<tag>_<variant>_*.flac.
Variants: raw restorers (MossFormer2 SE / SR, Resemble Enhance, NovaSR (VoiceFixer: package not installed)) plus the
'SUNO AI Voice Upscale' chain (SE base + SR high band via HybridHFBlend -> HFArtifactRepair).
usage: queue_vocalfix.py <file in ComfyUI/input> <tag>"""
import json, sys, time, urllib.request

HOST = "http://127.0.0.1:8188"
src, tag = sys.argv[1], sys.argv[2]
p = {"in": {"class_type": "LoadAudio", "inputs": {"audio": src}}}


def restorer(name, model):
    p[f"L_{name}"] = {"class_type": "FL_ClearVoice_ModelLoader", "inputs": {"model": model, "force_reload": False}}
    p[f"P_{name}"] = {"class_type": "FL_ClearVoice_Process", "inputs": {"model": [f"L_{name}", 0], "audio": ["in", 0]}}
    return [f"P_{name}", 0]


def save(name, audio):
    p[f"S_{name}"] = {"class_type": "SaveAudio", "inputs": {"audio": audio, "filename_prefix": f"audio/vocalfix/{tag}_{name}"}}


outs = {
    "se": restorer("se", "MossFormer2_SE_48K"),
    "sr": restorer("sr", "MossFormer2_SR_48K"),
    "resemble": restorer("resemble", "Resemble_Enhance"),
    "novasr": restorer("novasr", "NovaSR"),
}
for k, v in outs.items():
    save(k, v)
# the existing SUNO chain, with the settings of its active nodes (16 + 17)
p["blend"] = {"class_type": "HybridHFBlend", "inputs": {
    "base_audio": outs["se"], "donor_audio": outs["sr"], "crossover_hz": 10500.0, "gate_low_db": -64.0,
    "gate_high_db": -44.0, "hf_gain": 0.75, "release_ms": 200.0, "hf_ceiling": 0.6}}
p["repair"] = {"class_type": "HFArtifactRepair", "inputs": {"audio": ["blend", 0], "mode": "vocal",
                                                           "detect_only": False, "lowpass_hz": 0.0}}
save("sunochain", ["repair", 0])
# de-cricket alone on the raw stem (does the existing repair node catch ACE's 8-12 kHz fizz?)
p["repair_raw"] = {"class_type": "HFArtifactRepair", "inputs": {"audio": ["in", 0], "mode": "vocal_hard",
                                                               "detect_only": False, "lowpass_hz": 0.0}}
save("repairhard", ["repair_raw", 0])

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
