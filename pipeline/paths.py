"""Where the pipeline finds things on this machine. Every path is repo-relative by default and can be
overridden with an environment variable, so the same scripts run on the Windows box they were built on and
anywhere else. Set them once in your shell (or a .env your launcher reads):

  AI_ROOT        repo root (default: the folder above pipeline/)
  AI_TOOLS       third-party tool clones + weights      (default: $AI_ROOT/tools)
  AI_MODELS      separation model weights               (default: $AI_TOOLS/models)
  AI_SONGEVAL    SongEval clone (research ranking only) (default: $AI_TOOLS/SongEval)
  AI_DRUM_KIT    Big Rusty Drums Samples/ folder        (default: $AI_ROOT/assets/drums/big_rusty/Samples)
  VST3_DIR       VST3 plugin folder                     (default: the OS's standard VST3 location)
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("AI_ROOT", os.path.dirname(_here))
PIPELINE = _here
SCRIPTS = os.path.join(ROOT, "song01_paper_planes", "scripts")      # master_ref.py, vocal_fix.py, ...
NODES = os.path.join(ROOT, "comfyui", "nodes")                      # hybrid_hf_blend.py (HF repair core)
TOOLS = os.environ.get("AI_TOOLS", os.path.join(ROOT, "tools"))
MODELS = os.environ.get("AI_MODELS", os.path.join(TOOLS, "models"))
SONGEVAL = os.environ.get("AI_SONGEVAL", os.path.join(TOOLS, "SongEval"))
DRUM_KIT = os.environ.get("AI_DRUM_KIT", os.path.join(ROOT, "assets", "drums", "big_rusty", "Samples"))
MASTER = os.path.join(SCRIPTS, "master_ref.py")


def _default_vst3():
    if sys.platform == "win32":
        return r"C:\Program Files\Common Files\VST3"
    if sys.platform == "darwin":
        return "/Library/Audio/Plug-Ins/VST3"
    return os.path.expanduser("~/.vst3")


VST3 = os.environ.get("VST3_DIR", _default_vst3())


def need(path, what, env):
    """Fail early with a message that says what is missing and which variable points at it."""
    if not os.path.exists(path):
        sys.exit(f"{what} not found at {path}\n  set {env} to its location")
    return path


def find_mix(take):
    """The generation tail saves mix.wav or mix.flac in each take folder."""
    for f in ("mix.wav", "mix.flac"):
        p = os.path.join(take, f)
        if os.path.exists(p):
            return p
    sys.exit(f"no mix.wav / mix.flac in {take}")
