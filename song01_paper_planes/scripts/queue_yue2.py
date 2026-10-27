"""Convert YuE2_Song.json (UI format) to API format, set style/lyrics, queue N seeds.
usage: queue_yue2.py style.txt lyrics.txt [takes=4] [seconds=120] [prefix=YuE2_song] [seed]
env YUE2_VAE (default yue2_vae_legacy.safetensors; 'bundled' = checkpoint decoder)
env YUE2_SAMPLER=midpoint: official explicit-midpoint solver, uniform 32 steps (default: workflow dpmpp_2m/sgm_uniform)
env YUE2_EXTRA_VAE=<file in models/vae>: also decode the same latent with that VAE (saved as <prefix>_vae-<name>)
Launch ComfyUI with --fp32-vae: the official YuE2 preset decodes in FP32 (ComfyUI defaults to fp16 on this GPU)."""
import json, os, sys, random, urllib.request

HOST = "http://127.0.0.1:8188"
WF = r"D:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\YuE2_Song.json"


def get(path):
    return json.load(urllib.request.urlopen(HOST + path))


def to_api(ui):
    info = get("/object_info")
    links = {l[0]: (str(l[1]), l[2]) for l in ui["links"]}
    api = {}
    for n in ui["nodes"]:
        if n.get("mode", 0) != 0:
            continue
        spec = info[n["type"]]["input"]
        ordered = list(spec.get("required", {}).items()) + list(spec.get("optional", {}).items())
        linked = {i["name"]: i["link"] for i in n.get("inputs", []) if i.get("link") is not None}
        vals = list(n.get("widgets_values", []) or [])
        inputs = {}
        for name, s in ordered:
            typ = s[0]
            opts = s[1] if len(s) > 1 and isinstance(s[1], dict) else {}
            is_widget = (isinstance(typ, list) or typ in ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO")) and not opts.get("forceInput")
            if is_widget and vals:
                v = vals.pop(0)
                if typ == "INT" and (name in ("seed", "noise_seed") or opts.get("control_after_generate")):
                    if vals and vals[0] in ("fixed", "randomize", "increment", "decrement"):
                        vals.pop(0)
                inputs[name] = v
            if name in linked:
                inputs[name] = list(links[linked[name]])
        api[str(n["id"])] = {"class_type": n["type"], "inputs": inputs}
    return api


def main():
    style = open(sys.argv[1], encoding="utf-8").read().strip()
    lyrics = open(sys.argv[2], encoding="utf-8").read().strip()
    takes = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    seconds = float(sys.argv[4]) if len(sys.argv) > 4 else None
    prefix = sys.argv[5] if len(sys.argv) > 5 else None
    fixed_seed = int(sys.argv[6]) if len(sys.argv) > 6 else None
    ui = json.load(open(WF, encoding="utf-8"))
    for n in ui["nodes"]:
        if n["id"] == 2:
            n["widgets_values"] = [style]
        if n["id"] == 3:
            n["widgets_values"] = [lyrics]
        if n["id"] == 13 and seconds:  # EmptyYuE2LatentAudio [seconds, batch]
            n["widgets_values"][0] = seconds
        if n["id"] in (17, 20) and prefix:  # lyric score + save nodes: output name
            n["widgets_values"][0] = f"audio/{prefix}"
    api = to_api(ui)
    # Tiled decode, official chunking (YuE2-Vae config: decode_core_frames 1024, halo 16). The workflow's plain
    # VAEDecodeAudio in FP32 (--fp32-vae) made the watchdog kill ComfyUI on a 215 s song (commit ran out).
    for k, n in api.items():
        if n["class_type"] == "VAEDecodeAudio":
            n["class_type"] = "VAEDecodeAudioTiled"
            n["inputs"].update({"tile_size": 1024, "overlap": 32})
    # Default decoder = YuE2-Vae-legacy (authors' benchmark decoder; user preferred it by ear on song02 2026-10-17).
    # YUE2_VAE=bundled keeps the checkpoint's own decoder (== m-a-p/YuE2-Vae).
    main_vae = os.environ.get("YUE2_VAE", "yue2_vae_legacy.safetensors")
    if main_vae != "bundled":
        api["200"] = {"class_type": "VAELoader", "inputs": {"vae_name": main_vae}}
        for k, n in api.items():
            if n["class_type"] == "VAEDecodeAudioTiled" and k != "202":
                n["inputs"]["vae"] = ["200", 0]
    if os.environ.get("YUE2_SAMPLER") == "midpoint":  # official solver (custom_nodes/yue2_midpoint.py)
        k = api["14"]["inputs"]
        api["210"] = {"class_type": "YuE2MidpointSampler", "inputs": {}}
        api["211"] = {"class_type": "YuE2UniformSigmas", "inputs": {"steps": k["steps"]}}
        api["14"] = {"class_type": "SamplerCustom", "inputs": {
            "model": k["model"], "add_noise": True, "noise_seed": k["seed"], "cfg": k["cfg"],
            "positive": k["positive"], "negative": k["negative"], "sampler": ["210", 0], "sigmas": ["211", 0],
            "latent_image": k["latent_image"]}}
    extra = os.environ.get("YUE2_EXTRA_VAE")
    if extra:  # second decode of the same latent (node 14 = KSampler) with another VAE
        tag = extra.rsplit(".", 1)[0]
        api["201"] = {"class_type": "VAELoader", "inputs": {"vae_name": extra}}
        api["202"] = {"class_type": "VAEDecodeAudioTiled", "inputs": {"samples": ["14", 0], "vae": ["201", 0],
                                                                       "tile_size": 1024, "overlap": 32}}
        api["203"] = {"class_type": "SaveAudio", "inputs": {"audio": ["202", 0],
                      "filename_prefix": f"audio/{prefix or 'YuE2_song'}_vae-{tag}"}}
    for _ in range(takes):
        seed = fixed_seed or random.randint(1, 2**31 - 1)
        api["4"]["inputs"]["seed"] = seed
        req = urllib.request.Request(HOST + "/prompt", data=json.dumps({"prompt": api}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req))
            if r.get("node_errors"):
                print("NODE ERRORS", json.dumps(r["node_errors"])[:3000]); sys.exit(1)
            print("queued seed", seed, r.get("prompt_id"))
        except urllib.error.HTTPError as e:
            print("ERROR", e.read().decode()[:3000])
            sys.exit(1)


if __name__ == "__main__":
    main()
