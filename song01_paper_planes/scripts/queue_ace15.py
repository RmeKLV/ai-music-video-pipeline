"""ACE-Step 1.5 XL SFT front end + the YuE2 tail (Demucs, Whisper score, master, save).
usage: queue_ace15.py style.txt lyrics.txt takes [cfg] [steps] [shift] [seconds] [lm] [seed]
env: ACE_BPM (124), ACE_KEY ("G major"), ACE_PREFIX (output name, default ACE15xl), ACE_TIMESIG (4)
     ACE_APG (default 1; 0 = plain CFG) -> Adaptive Projected Guidance before the sampler (eta 0, norm 2.5, momentum -0.75, ACE v1 values)
     lets cfg go higher without over-saturation/crackle; official 1.5 docs use ADG + guidance 7-9 + shift 3"""
import json, os, sys, random, urllib.request
sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from queue_yue2 import to_api, WF, HOST

style = open(sys.argv[1], encoding="utf-8").read().strip()
lyrics = open(sys.argv[2], encoding="utf-8").read().strip()
takes = int(sys.argv[3])
cfg = float(sys.argv[4]) if len(sys.argv) > 4 else 7.0  # with APG (default on); plain CFG crackles at 7, use 2.5 if ACE_APG=0  # same-seed test: crackle 79 clicks at cfg 7 -> 9 at 2.5, lyrics unchanged
steps = int(sys.argv[5]) if len(sys.argv) > 5 else 50
shift = float(sys.argv[6]) if len(sys.argv) > 6 else 3.0  # official recommendation; song02 same-seed test: lyrics 0.71 -> 0.88
seconds = float(sys.argv[7]) if len(sys.argv) > 7 else 150.0
# 4B + XL does not fit in 32 GB RAM on this box (fills RAM during XL load); 1.7B does
lm = sys.argv[8] if len(sys.argv) > 8 else "qwen_1.7b_ace15.safetensors"
fixed_seed = int(sys.argv[9]) if len(sys.argv) > 9 else None  # same seed = A/B a setting

tail = to_api(json.load(open(WF, encoding="utf-8")))
api = {k: tail[k] for k in ("16", "17", "18", "19", "20")}
api.update({
    "101": {"class_type": "UNETLoader", "inputs": {"unet_name": "acestep_v1.5_xl_sft_bf16.safetensors", "weight_dtype": "default"}},
    "102": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "qwen_0.6b_ace15.safetensors", "clip_name2": lm, "type": "ace"}},
    "103": {"class_type": "VAELoader", "inputs": {"vae_name": "ace_1.5_vae.safetensors"}},
    "104": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["101", 0], "shift": shift}},
    "105": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {
        "clip": ["102", 0], "tags": style, "lyrics": lyrics, "seed": 0, "bpm": int(os.environ.get("ACE_BPM", 124)), "duration": seconds,
        "timesignature": os.environ.get("ACE_TIMESIG", "4"), "language": "en", "keyscale": os.environ.get("ACE_KEY", "G major"), "generate_audio_codes": True,
        "cfg_scale": 2.0, "temperature": 0.85, "top_p": 0.9, "top_k": 0, "min_p": 0.0}},
    "106": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["105", 0]}},
    "107": {"class_type": "EmptyAceStep1.5LatentAudio", "inputs": {"seconds": seconds, "batch_size": 1}},
    "108": {"class_type": "KSampler", "inputs": {"model": ["104", 0], "positive": ["105", 0], "negative": ["106", 0],
        "latent_image": ["107", 0], "seed": 0, "steps": steps, "cfg": cfg, "sampler_name": "euler",
        "scheduler": "simple", "denoise": 1.0}},
    "109": {"class_type": "VAEDecodeAudioTiled", "inputs": {"samples": ["108", 0], "vae": ["103", 0],
                                                          "tile_size": 512, "overlap": 64}},
    "110": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": style}},
    "111": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": lyrics}},
    "112": {"class_type": "PrimitiveInt", "inputs": {"value": 0}},
})
if os.environ.get("AB_VAE"):  # decode the same latent with the original and ScragVAE decoders
    api.update({
        "113": {"class_type": "VAELoader", "inputs": {"vae_name": "ace_1.5_scragvae.safetensors"}},
        "114": {"class_type": "VAEDecodeAudioTiled", "inputs": {"samples": ["108", 0], "vae": ["113", 0],
                                                              "tile_size": 512, "overlap": 64}},
        "115": {"class_type": "SaveAudio", "inputs": {"audio": ["114", 0], "filename_prefix": "audio/AB_vae/scragvae"}},
        "116": {"class_type": "SaveAudio", "inputs": {"audio": ["109", 0], "filename_prefix": "audio/AB_vae/original"}},
    })
if os.environ.get("ACE_APG", "1") != "0":  # default ON since song02 (see SONGWRITING_PLAYBOOK.md)
    api["117"] = {"class_type": "APG", "inputs": {"model": ["104", 0], "eta": 0.0, "norm_threshold": 2.5, "momentum": -0.75}}
    api["108"]["inputs"]["model"] = ["117", 0]
api["16"]["inputs"]["audio"] = ["109", 0]
api["20"]["inputs"]["mix"] = ["109", 0]
api["17"]["inputs"].update({"lyrics": ["111", 0], "style": ["110", 0], "seed": ["112", 0],
                            "filename_prefix": f"audio/{os.environ.get('ACE_PREFIX', 'ACE15xl')}_{lm.split('_')[1]}_cfg{cfg:g}_sh{shift:g}{'_apg' if os.environ.get('ACE_APG', '1') != '0' else ''}"})

for _ in range(takes):
    seed = fixed_seed or random.randint(1, 2**31 - 1)
    for n in ("105", "108"):
        api[n]["inputs"]["seed"] = seed
    api["112"]["inputs"]["value"] = seed
    req = urllib.request.Request(HOST + "/prompt", data=json.dumps({"prompt": api}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req))
        if r.get("node_errors"):
            print("NODE ERRORS", json.dumps(r["node_errors"])[:3000]); sys.exit(1)
        print("queued seed", seed, "cfg", cfg, r.get("prompt_id"))
    except urllib.error.HTTPError as e:
        print("ERROR", e.read().decode()[:3000]); sys.exit(1)
