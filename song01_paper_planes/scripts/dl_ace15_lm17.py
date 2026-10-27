import os, shutil, time
from huggingface_hub import hf_hub_download
dst = r"D:\ComfyUI_windows_portable\ComfyUI\models\text_encoders\qwen_1.7b_ace15.safetensors"
stage = r"D:\ComfyUI_windows_portable\hf_stage"
t = time.time()
p = hf_hub_download("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/text_encoders/qwen_1.7b_ace15.safetensors", local_dir=stage)
shutil.move(p, dst); shutil.rmtree(stage, ignore_errors=True)
print(f"done {os.path.getsize(dst)} bytes in {time.time()-t:.0f}s", flush=True)
