"""Protect the PC from RAM exhaustion while ComfyUI renders.
free < SOFT GB -> POST /interrupt + /free ; free < HARD GB -> kill ComfyUI's python.
Prints a line every 10 s with free RAM and the lowest seen so far."""
import ctypes, json, subprocess, time, urllib.request

# act on commit (RAM + page file) running out, not on low physical RAM: with a
# growable page file Windows can page idle data out instead of freezing
SOFT, HARD = 0.5, 0.25
HOST = "http://127.0.0.1:8188"


class MEMSTAT(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def mem():
    m = MEMSTAT(); m.dwLength = ctypes.sizeof(MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2**30, m.ullAvailPageFile / 2**30


def post(path, body=b"{}"):
    try:
        urllib.request.urlopen(urllib.request.Request(HOST + path, data=body,
                               headers={"Content-Type": "application/json"}), timeout=5)
    except Exception as e:
        print("post failed", path, e, flush=True)


low, last = 99.0, 0
while True:
    free, commit = mem()
    low = min(low, free)
    if commit < HARD:
        print(f"HARD LIMIT commit_free={commit:.2f}GB free={free:.2f}GB -> killing ComfyUI", flush=True)
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                        "Where-Object { $_.CommandLine -like '*ComfyUI*main.py*' } | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True)
    elif commit < SOFT:
        print(f"SOFT LIMIT free={free:.2f}GB commit_free={commit:.2f}GB -> interrupt + free", flush=True)
        post("/interrupt"); post("/free", json.dumps({"unload_models": True, "free_memory": True}).encode())
        time.sleep(5)
    if time.time() - last > 10:
        print(f"free={free:.1f}GB commit_free={commit:.1f}GB lowest={low:.1f}GB", flush=True)
        last = time.time()
    time.sleep(0.5)
