"""Face Swap tab: runs Changeling (its own repo, its own venv) as a subprocess.

Changeling stays a separate project: this only calls its headless command line,
    <CHANGELING_DIR>/psdenv/Scripts/python.exe run.py -s face -t target -o out ...
with CHANGELING_MODELS_DIR pointing at this repo's models/changeling, so the Models page
manages its two model files like every other model.
Changeling's NSFW check stays on: a flagged target ends with exit code 3.
"""
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from comfy_client import Cancelled, ComfyError

CHANGELING_DIR = Path(os.environ.get("CHANGELING_DIR") or os.environ.get("ROOP_DIR") or r"D:\cc\Changeling-CopyCat")
MODELS = Path(os.environ.get("MODELS_DIR", Path(__file__).parent / "models")) / "changeling"
SWAPPER, ENHANCER = "inswapper_128.onnx", "GFPGANv1.4.pth"
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
VIDEO_TYPES = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".gif")
BLOCKED = 3  # changeling.core.blocked()

_procs = {}  # job id -> running Popen, for cancel()
_lock = threading.Lock()


def _python():
    for p in (CHANGELING_DIR / "psdenv" / "Scripts" / "python.exe", CHANGELING_DIR / "psdenv" / "bin" / "python"):
        if p.exists():
            return p
    return None


def _installed():
    """Changeling's packages are really in its venv (setup.bat's .requirements marker can outlive them)."""
    venv = CHANGELING_DIR / "psdenv"
    sites = [venv / "Lib" / "site-packages", *venv.glob("lib/python3*/site-packages")]
    return any(all((s / pkg).is_dir() for pkg in ("onnxruntime", "insightface")) for s in sites)


def check(enhance):
    """Why Face Swap can't run yet, or None."""
    if not (CHANGELING_DIR / "run.py").exists():
        return f"Changeling isn't in {CHANGELING_DIR} (set CHANGELING_DIR)."
    if not _python() or not _installed():
        return f"Changeling isn't set up yet: run setup.bat in {CHANGELING_DIR} once."
    need = [SWAPPER] + ([ENHANCER] if enhance else [])
    missing = [n for n in need if not (MODELS / n).exists()]
    if missing:
        return "Missing " + ", ".join(missing) + ": get \"Changeling face swap\" on the Models page."
    return None


def swap(face_name, face_data, target_name, target_data, *, enhance=False,
         many_faces=False, job=None, timeout=3600, on_progress=None):
    """Swap the face in `face_data` onto `target_data` (an image or a video).
    Returns {"images": [(filename, bytes)], "prompt_id": None, "seed": None}."""
    problem = check(enhance)
    if problem:
        raise ComfyError(problem)
    ext = Path(target_name).suffix.lower()
    if ext not in IMAGE_TYPES + VIDEO_TYPES:
        raise ValueError(f"{target_name}: not an image or video Changeling can read")
    video = ext in VIDEO_TYPES
    out_name = f"faceswap_{time.strftime('%Y%m%d_%H%M%S')}{'.mp4' if video else '.png'}"

    with tempfile.TemporaryDirectory(prefix="faceswap_") as tmp:
        tmp = Path(tmp)
        face = tmp / ("face" + (Path(face_name).suffix.lower() or ".png"))
        target = tmp / ("target" + ext)
        out = tmp / out_name
        face.write_bytes(face_data)
        target.write_bytes(target_data)

        cmd = [str(_python()), "run.py", "-s", str(face), "-t", str(target), "-o", str(out),
               "--frame-processor", "face_swapper", *(["face_enhancer"] if enhance else []),
               "--execution-provider", "cuda", "--keep-fps"]
        if many_faces:
            cmd.append("--many-faces")
        env = dict(os.environ, CHANGELING_MODELS_DIR=str(MODELS), PYTHONUNBUFFERED="1")
        if on_progress:
            on_progress({"state": "running", "phase": "Starting Changeling"})
        proc = subprocess.Popen(cmd, cwd=CHANGELING_DIR, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        with _lock:
            _procs[job] = proc
        lines = []
        killer = threading.Timer(timeout, proc.kill)
        killer.start()
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                lines.append(line)
                if on_progress and line.startswith(("[CHANGELING.", "[ROOP.")):
                    on_progress({"state": "running", "phase": line.split("] ", 1)[-1].rstrip(".")})
            proc.wait()
        finally:
            killer.cancel()
            with _lock:
                cancelled = _procs.pop(job, None) is None
        if cancelled:
            raise Cancelled("Cancelled.")
        if proc.returncode == BLOCKED:
            raise ComfyError("Changeling's NSFW check flagged the target, so it wasn't processed.")
        if proc.returncode or not out.exists():
            tail = " | ".join(lines[-4:]) or f"exit code {proc.returncode}"
            raise ComfyError(f"Changeling failed: {tail}")
        return {"images": [(out_name, out.read_bytes())], "prompt_id": None, "seed": None}


def cancel(job):
    """Stop a running swap. True if there was one."""
    with _lock:
        proc = _procs.pop(job, None)
    if not proc:
        return False
    proc.kill()
    return True
