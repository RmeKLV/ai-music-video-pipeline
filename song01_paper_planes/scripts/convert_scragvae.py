"""Convert ScragVAE (diffusers AutoencoderOobleck) to ComfyUI's ACE 1.5 VAE key layout.
Check: ScragVAE's encoder is unchanged from the original, so after conversion its encoder must
equal ComfyUI's ace_1.5_vae.safetensors encoder exactly -> proves the name mapping is right."""
import torch
from safetensors.torch import load_file, save_file

SRC = r"D:\ComfyUI_windows_portable\hf_scrag\diffusion_pytorch_model.safetensors"
REF = r"D:\ComfyUI_windows_portable\ComfyUI\models\vae\ace_1.5_vae.safetensors"
DST = r"D:\ComfyUI_windows_portable\ComfyUI\models\vae\ace_1.5_scragvae.safetensors"
N_BLOCKS = 5


def res_unit(pre_d, pre_c):
    return {f"{pre_d}.snake1": f"{pre_c}.layers.0", f"{pre_d}.conv1": f"{pre_c}.layers.1",
            f"{pre_d}.snake2": f"{pre_c}.layers.2", f"{pre_d}.conv2": f"{pre_c}.layers.3"}


m = {"encoder.conv1": "encoder.layers.0", "decoder.conv1": "decoder.layers.0",
     "encoder.snake1": f"encoder.layers.{N_BLOCKS + 1}", "encoder.conv2": f"encoder.layers.{N_BLOCKS + 2}",
     "decoder.snake1": f"decoder.layers.{N_BLOCKS + 1}", "decoder.conv2": f"decoder.layers.{N_BLOCKS + 2}"}
for i in range(N_BLOCKS):
    e, d = f"encoder.layers.{i + 1}", f"decoder.layers.{i + 1}"
    for j in range(3):  # encoder block: res units first, then snake + conv
        m.update(res_unit(f"encoder.block.{i}.res_unit{j + 1}", f"{e}.layers.{j}"))
    m[f"encoder.block.{i}.snake1"] = f"{e}.layers.3"
    m[f"encoder.block.{i}.conv1"] = f"{e}.layers.4"
    m[f"decoder.block.{i}.snake1"] = f"{d}.layers.0"  # decoder block: snake + conv_t first
    m[f"decoder.block.{i}.conv_t1"] = f"{d}.layers.1"
    for j in range(3):
        m.update(res_unit(f"decoder.block.{i}.res_unit{j + 1}", f"{d}.layers.{j + 2}"))

src, ref = load_file(SRC), load_file(REF)
out, missing = {}, []
for k, v in src.items():
    mod, param = k.rsplit(".", 1)
    if mod not in m:
        missing.append(k); continue
    nk = f"{m[mod]}.{param}"
    if nk not in ref:
        missing.append(f"{k} -> {nk} (not in ref)"); continue
    if v.shape != ref[nk].shape:
        assert v.numel() == ref[nk].numel(), (k, v.shape, ref[nk].shape)
        v = v.reshape(ref[nk].shape)
    out[nk] = v.to(ref[nk].dtype)

assert not missing, missing[:10]
assert set(out) == set(ref), sorted(set(ref) - set(out))[:10]
enc_diff = max((out[k].float() - ref[k].float()).abs().max().item() for k in ref if k.startswith("encoder."))
dec_diff = max((out[k].float() - ref[k].float()).abs().max().item() for k in ref if k.startswith("decoder."))
print(f"mapped {len(out)} tensors; encoder max diff vs original = {enc_diff:.3g} (must be ~0); "
      f"decoder max diff = {dec_diff:.3g} (must be > 0: retrained)")
assert enc_diff < 1e-2, "encoder mismatch -> mapping is wrong, not saving"
save_file(out, DST)
print("saved", DST)
