import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import importlib.metadata
import importlib.util
import webbrowser
from shutil import which
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import psutil
from packaging import version

from runtime_profiles import detect_system_info, ProfileManager
from process_manager import GpuProcessManager

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

BASE_DIR = Path(__file__).resolve().parent
INSTALLED_MODULES_FILE = BASE_DIR / "installed_modules.json"
FAVORITES_FILE = BASE_DIR / "favorites_modules.json"
LANGUAGES_FILE = BASE_DIR / "assets" / "languages.json"
SETTINGS_FILE = BASE_DIR / "data" / "app_settings.json"
LOG_DIR = BASE_DIR / "logs"

DEFAULT_SETTINGS = {
    "language": "es",
    "model_dir": r"C:\models",
    "show_logs": True,
    "theme": "Light",
    "rag_endpoint": "http://127.0.0.1:8080/v1/chat/completions",
}

AVAILABLE_MODULES = [
    {"key": "monitor", "title_key": "mod_monitor_title", "desc_key": "mod_monitor_desc", "category": "core", "compute": "cpu"},
    {"key": "llm_frontend", "title_key": "mod_llm_title", "desc_key": "mod_llm_desc", "category": "core", "compute": "cpu_gpu"},
    {"key": "inclu_ia", "title_key": "mod_incluia_title", "desc_key": "mod_incluia_desc", "category": "core", "compute": "cpu"},
    {"key": "ml_sharp", "title_key": "mod_mlsharp_title", "desc_key": "mod_mlsharp_desc", "category": "vision", "compute": "gpu"},
    {"key": "model_3d", "title_key": "mod_model3d_title", "desc_key": "mod_model3d_desc", "category": "vision", "compute": "gpu"},
    {"key": "spotedit", "title_key": "mod_spotedit_title", "desc_key": "mod_spotedit_desc", "category": "vision", "compute": "gpu"},
    {"key": "hy_motion", "title_key": "mod_hymotion_title", "desc_key": "mod_hymotion_desc", "category": "motion", "compute": "gpu"},
    {"key": "proedit", "title_key": "mod_proedit_title", "desc_key": "mod_proedit_desc", "category": "vision", "compute": "gpu", "coming_soon": True},
    {"key": "neutts", "title_key": "mod_neutts_title", "desc_key": "mod_neutts_desc", "category": "audio", "compute": "cpu_gpu"},
    {"key": "finetune_glm", "title_key": "mod_finetune_glm_title", "desc_key": "mod_finetune_glm_desc", "category": "core", "compute": "cpu_gpu"},
    {"key": "research_assistant", "title_key": "mod_research_title", "desc_key": "mod_research_desc", "category": "knowledge", "compute": "cpu"},
    {"key": "klein", "title_key": "mod_klein_title", "desc_key": "mod_klein_desc", "category": "vision", "compute": "gpu"},
    {"key": "hyworld", "title_key": "mod_hyworld_title", "desc_key": "mod_hyworld_desc", "category": "vision", "compute": "gpu"},
    {"key": "cyberscraper", "title_key": "mod_cyber_title", "desc_key": "mod_cyber_desc", "category": "tools", "compute": "cpu"},
    {"key": "viga", "title_key": "mod_viga_title", "desc_key": "mod_viga_desc", "category": "vision", "compute": "gpu"},
    {"key": "videomama", "title_key": "mod_videomama_title", "desc_key": "mod_videomama_desc", "category": "vision", "compute": "gpu"},
    {"key": "luxtts", "title_key": "mod_luxtts_title", "desc_key": "mod_luxtts_desc", "category": "audio", "compute": "cpu_or_gpu"},
    {"key": "vibevoice_asr", "title_key": "mod_vibevoice_asr_title", "desc_key": "mod_vibevoice_asr_desc", "category": "audio", "compute": "cpu_or_gpu"},
    {"key": "frankenmotion", "title_key": "mod_frankenmotion_title", "desc_key": "mod_frankenmotion_desc", "category": "motion", "compute": "gpu", "coming_soon": True},
    {"key": "flowact_r1", "title_key": "mod_flowact_r1_title", "desc_key": "mod_flowact_r1_desc", "category": "motion", "compute": "gpu", "coming_soon": True},
    {"key": "omni_transfer", "title_key": "mod_omni_transfer_title", "desc_key": "mod_omni_transfer_desc", "category": "vision", "compute": "gpu"},
    {"key": "qwen3_tts", "title_key": "mod_qwen3_tts_title", "desc_key": "mod_qwen3_tts_desc", "category": "audio", "compute": "cpu_or_gpu"},
    {"key": "lightonocr", "title_key": "mod_lightonocr_title", "desc_key": "mod_lightonocr_desc", "category": "vision", "compute": "cpu_or_gpu"},
    {"key": "personaplex", "title_key": "mod_personaplex_title", "desc_key": "mod_personaplex_desc", "category": "audio", "compute": "gpu"},
]

MODEL3D_PLAIN_KEYS = {
    "monitor": "mod_monitor_plain",
    "llm_frontend": "mod_llm_plain",
    "inclu_ia": "mod_incluia_plain",
    "ml_sharp": "mlsharp_plain",
    "model_3d": "model3d_plain",
    "spotedit": "spotedit_plain",
    "hy_motion": "hymotion_plain",
    "proedit": "proedit_plain",
    "neutts": "neutts_plain",
    "finetune_glm": "finetune_plain",
    "research_assistant": "mod_research_plain",
    "klein": "klein_plain",
    "hyworld": "hyworld_plain",
    "cyberscraper": "cyber_plain",
    "viga": "viga_plain",
    "videomama": "videomama_plain",
    "luxtts": "luxtts_plain",
    "vibevoice_asr": "vibevoice_asr_plain",
    "frankenmotion": "frankenmotion_plain",
    "flowact_r1": "flowact_r1_plain",
    "omni_transfer": "omni_transfer_plain",
    "qwen3_tts": "qwen3_tts_plain",
    "lightonocr": "lightonocr_plain",
    "personaplex": "personaplex_plain",
}

SERVICE_META = [
    {"key": "llm_service", "name_key": "svc_name_llm", "desc_key": "svc_desc_llm", "port": 8080},
    {"key": "clm_service", "name_key": "svc_name_clm", "desc_key": "svc_desc_clm", "port": 8081},
    {"key": "vlm_service", "name_key": "svc_name_vlm", "desc_key": "svc_desc_vlm", "port": 9090},
    {"key": "alm_service", "name_key": "svc_name_alm", "desc_key": "svc_desc_alm", "port": 5000},
    {"key": "slm_service", "name_key": "svc_name_slm", "desc_key": "svc_desc_slm", "port": 5001},
]

SYSTEM_INFO = detect_system_info()
PROFILE_MANAGER = ProfileManager(SYSTEM_INFO, LOG_DIR)
PROCESS_MANAGER = GpuProcessManager(PROFILE_MANAGER, log_dir=str(LOG_DIR))

MODULE_PROCS: Dict[str, subprocess.Popen] = {}
MODULE_PROC_LOCK = threading.Lock()
MODULE_STATE: Dict[str, Dict] = {}

CYBER_BACKEND_DIR = BASE_DIR / "ai-backends" / "CyberScraper-2077"
HYMOTION_BACKEND_DIR = BASE_DIR / "ai-backends" / "HY-Motion-1.0"
HYMOTION_OUTPUT_DIR = BASE_DIR / "hymotion-out"
HYWORLD_BACKEND_DIR = BASE_DIR / "ai-backends" / "HunyuanWorld-Mirror"
HYWORLD_OUTPUT_DIR = BASE_DIR / "hyworld-out"
KLEIN_DATA_DIR = BASE_DIR / "data" / "klein"
KLEIN_OUTPUT_DIR = BASE_DIR / "klein-out"
INCLUIA_SERVER_PATH = BASE_DIR / "modules" / "inclu_ia" / "software" / "server.py"
INCLUIA_REQ_PATH = BASE_DIR / "modules" / "inclu_ia" / "requirements.txt"
MLSHARP_BACKEND_DIR = BASE_DIR / "ai-backends" / "ml-sharp"
MLSHARP_OUTPUT_DIR = BASE_DIR / "ml-sharp-out"
MLSHARP_VIEWER_TEMPLATE = BASE_DIR / "modules" / "ml_sharp" / "viewer_template.html"
MLSHARP_MODEL_URL = "https://ml-site.cdn-apple.com/models/sharp/sharp_2572gikvuh.pt"
MLSHARP_MODEL_NAME = "sharp_2572gikvuh.pt"
MODEL3D_DATA_DIR = BASE_DIR / "data" / "model_3d"
MODEL3D_CONFIG_PATH = MODEL3D_DATA_DIR / "config.json"
MODEL3D_OUTPUT_BASE = BASE_DIR.parent / "system" / "3d-out"
MODEL3D_BACKENDS_DIR = BASE_DIR / "3d-backends"
MODEL3D_WEIGHTS_DIR = BASE_DIR / "3d-weights"
NEUTTS_BACKEND_DIR = BASE_DIR / "ai-backends" / "neutts"
NEUTTS_DATA_DIR = BASE_DIR / "data" / "neutts"
NEUTTS_OUTPUT_DIR = BASE_DIR / "neutts-out"
PROEDIT_OUTPUT_DIR = BASE_DIR / "proedit-out"
FINETUNE_OUTPUT_DIR = BASE_DIR / "finetune-out"
FINETUNE_SCRIPT_PATH = BASE_DIR / "data" / "finetune_glm" / "finetune_glm_4_7_flash.py"
RESEARCH_DATA_DIR = BASE_DIR / "data" / "research_assistant"
RESEARCH_DOCS_DIR = RESEARCH_DATA_DIR / "docs"
RESEARCH_LIBRARY_PATH = RESEARCH_DATA_DIR / "library.json"
RESEARCH_INDEX_PATH = RESEARCH_DATA_DIR / "index.json"
SPOTEDIT_BACKEND_DIR = BASE_DIR / "ai-backends" / "SpotEdit"
SPOTEDIT_DATA_DIR = BASE_DIR / "data" / "spotedit"
SPOTEDIT_OUTPUT_DIR = BASE_DIR / "spotedit-out"
VIGA_BACKEND_DIR = BASE_DIR / "ai-backends" / "VIGA"
VIGA_OUTPUT_DIR = BASE_DIR / "viga-out"
VIGA_SAM_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
VIDEOMAMA_BACKEND_DIR = BASE_DIR / "ai-backends" / "VideoMaMa"
VIDEOMAMA_OUTPUT_DIR = BASE_DIR / "videomama-out"
LUXTTS_BACKEND_DIR = BASE_DIR / "ai-backends" / "LuxTTS"
LUXTTS_OUTPUT_DIR = BASE_DIR / "luxtts-out"
VIBEVOICE_BACKEND_DIR = BASE_DIR / "ai-backends" / "VibeVoice"
VIBEVOICE_OUTPUT_DIR = BASE_DIR / "vibevoice-asr-out"
FRANKENMOTION_BACKEND_DIR = BASE_DIR / "ai-backends" / "FrankenMotion"
OMNITRANSFER_BACKEND_DIR = BASE_DIR / "ai-backends" / "OmniTransfer"
QWEN3TTS_BACKEND_DIR = BASE_DIR / "ai-backends" / "Qwen3-TTS"
QWEN3TTS_OUTPUT_DIR = BASE_DIR / "qwen3-tts-out"
LIGHTONOCR_BACKEND_DIR = BASE_DIR / "ai-backends" / "LightOnOCR"
LIGHTONOCR_OUTPUT_DIR = BASE_DIR / "lightonocr-out"
PERSONAPLEX_BACKEND_DIR = BASE_DIR / "ai-backends" / "PersonaPlex"
PERSONAPLEX_OUTPUT_DIR = BASE_DIR / "personaplex-out"

HYWORLD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
KLEIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
KLEIN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MLSHARP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL3D_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL3D_OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
MODEL3D_BACKENDS_DIR.mkdir(parents=True, exist_ok=True)
MODEL3D_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
NEUTTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
NEUTTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROEDIT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FINETUNE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH_DOCS_DIR.mkdir(parents=True, exist_ok=True)
SPOTEDIT_DATA_DIR.mkdir(parents=True, exist_ok=True)
SPOTEDIT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VIGA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VIDEOMAMA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LUXTTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VIBEVOICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
QWEN3TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LIGHTONOCR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PERSONAPLEX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _log_path(name: str) -> Path:
    return LOG_DIR / f"web_{name}.log"


def _append_log(name: str, message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _log_path(name).open("a", encoding="utf-8", errors="replace") as f:
        f.write(message.rstrip() + "\n")


def _tail_log(name: str, lines: int = 200) -> List[str]:
    path = _log_path(name)
    if not path.exists():
        return []
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return data[-lines:]
    except Exception:
        return []


def _clear_log(name: str) -> None:
    path = _log_path(name)
    if path.exists():
        try:
            path.unlink()
        except Exception:
            path.write_text("", encoding="utf-8")


def _run_cmd(key: str, cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict] = None) -> None:
    def worker():
        _append_log(key, f"$ {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                env=env,
            )
            with MODULE_PROC_LOCK:
                MODULE_PROCS[key] = proc
            if proc.stdout:
                for line in proc.stdout:
                    _append_log(key, line.rstrip())
            proc.wait()
            rc = proc.returncode
            _append_log(key, f"[done] exit={rc}")
        except Exception as exc:
            _append_log(key, f"[error] {exc}")
        finally:
            with MODULE_PROC_LOCK:
                MODULE_PROCS.pop(key, None)

    threading.Thread(target=worker, daemon=True).start()


def _run_cmd_blocking(key: str, cmd: List[str], cwd: Optional[Path] = None) -> int:
    _append_log(key, f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if proc.stdout:
            for line in proc.stdout:
                _append_log(key, line.rstrip())
        proc.wait()
        _append_log(key, f"[done] exit={proc.returncode}")
        return proc.returncode
    except Exception as exc:
        _append_log(key, f"[error] {exc}")
        return 1


def _run_cmd_with_marker(
    key: str,
    cmd: List[str],
    cwd: Optional[Path] = None,
    marker: Optional[Path] = None,
) -> None:
    def worker():
        _append_log(key, f"$ {' '.join(cmd)}")
        rc = 1
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            with MODULE_PROC_LOCK:
                MODULE_PROCS[key] = proc
            if proc.stdout:
                for line in proc.stdout:
                    _append_log(key, line.rstrip())
            proc.wait()
            rc = proc.returncode
            _append_log(key, f"[done] exit={rc}")
        except Exception as exc:
            _append_log(key, f"[error] {exc}")
        finally:
            if marker and rc == 0:
                try:
                    marker.write_text("ok", encoding="utf-8")
                except Exception:
                    pass
            with MODULE_PROC_LOCK:
                MODULE_PROCS.pop(key, None)

    threading.Thread(target=worker, daemon=True).start()


def _is_running(key: str) -> bool:
    with MODULE_PROC_LOCK:
        proc = MODULE_PROCS.get(key)
    return proc is not None and proc.poll() is None


def _stop_proc(key: str) -> None:
    with MODULE_PROC_LOCK:
        proc = MODULE_PROCS.get(key)
    if not proc:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    with MODULE_PROC_LOCK:
        MODULE_PROCS.pop(key, None)


def _resolve_hymotion_backend_dir() -> Path:
    primary = HYMOTION_BACKEND_DIR
    legacy = BASE_DIR.parent / "system" / "ai-backends" / "HY-Motion-1.0"
    if primary.exists():
        return primary
    if legacy.exists():
        return legacy
    return primary


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _klein_deps_ok() -> bool:
    required = ["diffusers", "transformers", "accelerate", "safetensors", "huggingface_hub", "torch", "PIL"]
    for pkg in required:
        try:
            if pkg == "PIL":
                import PIL  # noqa: F401
            else:
                importlib.metadata.version(pkg)
        except Exception:
            return False
    return True


def _mlsharp_find_sharp() -> Optional[str]:
    scripts_dir = Path(sys.executable).resolve().parent / "Scripts"
    for name in ("sharp.exe", "sharp"):
        candidate = scripts_dir / name
        if candidate.exists():
            return str(candidate)
    return shutil.which("sharp")


def _neutts_deps_ok(repo_id: str) -> bool:
    try:
        import neutts  # noqa: F401
        import soundfile  # noqa: F401
    except Exception:
        return False
    if repo_id.endswith("gguf"):
        try:
            import llama_cpp  # noqa: F401
        except Exception:
            return False
    return True


def _neutts_espeak_status() -> Dict:
    exe = which("espeak-ng") or which("espeak")
    if exe:
        return {"ok": True, "detail": exe}
    lib_path = os.environ.get("PHONEMIZER_ESPEAK_LIBRARY", "")
    if lib_path and Path(lib_path).exists():
        return {"ok": True, "detail": lib_path}
    bin_path = os.environ.get("PHONEMIZER_ESPEAK_PATH", "")
    if bin_path and Path(bin_path).exists():
        return {"ok": True, "detail": bin_path}
    return {"ok": False, "detail": ""}


def _query_nvidia_smi() -> Optional[Dict[str, List]]:
    smi = which("nvidia-smi")
    if not smi:
        default_smi = Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe")
        if default_smi.exists():
            smi = str(default_smi)
    if not smi:
        system32_smi = Path(r"C:\Windows\System32\nvidia-smi.exe")
        if system32_smi.exists():
            smi = str(system32_smi)
    if not smi:
        return None
    cmd = [
        smi,
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    names: List[str] = []
    vram: List[float] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            names.append(parts[0])
            try:
                vram.append(round(float(parts[1]) / 1024.0, 2))
            except Exception:
                vram.append(0.0)
        else:
            names.append(parts[0])
            vram.append(0.0)
    if not names:
        return None
    return {"names": names, "vram": vram}


def _query_windows_gpu() -> Optional[Dict[str, List]]:
    wmic = which("wmic")
    if not wmic:
        default_wmic = Path(r"C:\Windows\System32\wbem\WMIC.exe")
        if default_wmic.exists():
            wmic = str(default_wmic)
    if not wmic:
        return None
    cmd = [wmic, "path", "win32_VideoController", "get", "Name,AdapterRAM", "/format:csv"]
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    names: List[str] = []
    vram: List[float] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("node"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        _, adapter_ram, name = parts[0], parts[1], parts[2]
        if not name:
            continue
        names.append(name)
        try:
            vram.append(round(float(adapter_ram) / (1024**3), 2))
        except Exception:
            vram.append(0.0)
    if not names:
        return None
    sorted_names, sorted_vram = _sort_gpu_names(names, vram)
    return {"names": sorted_names, "vram": sorted_vram}


def _rank_gpu(name: str, vram: float) -> float:
    lowered = name.lower()
    score = vram
    if "nvidia" in lowered:
        score += 1000.0
    if "amd" in lowered or "radeon" in lowered:
        score += 500.0
    if "intel" in lowered:
        score += 200.0
    if "virtual" in lowered or "microsoft" in lowered or "basic render" in lowered:
        score -= 1000.0
    return score


def _sort_gpu_names(names: List[str], vram: List[float]) -> tuple[list[str], list[float]]:
    pairs = list(zip(names, vram))
    pairs.sort(key=lambda item: _rank_gpu(item[0], item[1]), reverse=True)
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _query_windows_gpu_cim() -> Optional[Dict[str, List]]:
    ps = which("powershell") or which("pwsh")
    if not ps:
        return None
    cmd = [
        ps,
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json",
    ]
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    if not output.strip():
        return None
    try:
        data = json.loads(output)
    except Exception:
        return None
    items = data if isinstance(data, list) else [data]
    names: List[str] = []
    vram: List[float] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or "").strip()
        if not name:
            continue
        names.append(name)
        try:
            vram.append(round(float(item.get("AdapterRAM", 0)) / (1024**3), 2))
        except Exception:
            vram.append(0.0)
    if not names:
        return None
    sorted_names, sorted_vram = _sort_gpu_names(names, vram)
    return {"names": sorted_names, "vram": sorted_vram}


def _query_nvidia_smi_stats() -> Optional[Dict[str, List]]:
    smi = which("nvidia-smi")
    if not smi:
        default_smi = Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe")
        if default_smi.exists():
            smi = str(default_smi)
    if not smi:
        system32_smi = Path(r"C:\Windows\System32\nvidia-smi.exe")
        if system32_smi.exists():
            smi = str(system32_smi)
    if not smi:
        return None
    cmd = [
        smi,
        "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    utils: List[float] = []
    temps: List[float] = []
    mem_used: List[float] = []
    mem_total: List[float] = []
    for line in output.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        try:
            utils.append(float(parts[0]))
        except Exception:
            utils.append(0.0)
        try:
            temps.append(float(parts[1]))
        except Exception:
            temps.append(0.0)
        try:
            mem_used.append(round(float(parts[2]) / 1024.0, 2))
        except Exception:
            mem_used.append(0.0)
        try:
            mem_total.append(round(float(parts[3]) / 1024.0, 2))
        except Exception:
            mem_total.append(0.0)
    if not utils:
        return None
    return {
        "util": utils,
        "temp": temps,
        "mem_used": mem_used,
        "mem_total": mem_total,
    }


RESEARCH_STOPWORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con", "contra",
    "cual", "cuando", "de", "del", "desde", "donde", "dos", "el", "ella", "ellas",
    "ellos", "en", "era", "eramos", "eran", "eres", "es", "esa", "esas", "ese", "eso",
    "esos", "esta", "estaba", "estaban", "estado", "estais", "estamos", "estan", "estar",
    "estas", "este", "esto", "estos", "fue", "fuera", "fueron", "ha", "hace", "haces",
    "hacia", "han", "hasta", "la", "las", "le", "les", "lo", "los", "mas", "me", "mi",
    "mis", "mucho", "muy", "no", "nos", "nosotros", "o", "otra", "otras", "otro",
    "otros", "para", "pero", "poco", "por", "porque", "que", "quien", "se", "sea",
    "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien", "tan", "tanto", "te",
    "tengo", "ti", "tiene", "tienen", "tu", "tus", "un", "una", "uno", "unos", "y",
}


def _model3d_load_config() -> Dict:
    if MODEL3D_CONFIG_PATH.exists():
        try:
            data = json.loads(MODEL3D_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _model3d_save_config(config: Dict) -> None:
    try:
        MODEL3D_CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _model3d_repo_name(key: str) -> Optional[str]:
    return {
        "stepx1": "Step1X-3D",
        "hunyuan3d2": "Hunyuan3D-2",
        "sam3d": "sam-3d-objects",
    }.get(key)


def _model3d_repo_url(key: str) -> Optional[str]:
    return {
        "stepx1": "https://github.com/stepfun-ai/Step1X-3D",
        "hunyuan3d2": "https://github.com/Tencent/Hunyuan3D-2",
        "sam3d": "https://github.com/facebookresearch/sam-3d-objects",
    }.get(key)


def _model3d_repo_path(key: str) -> Optional[Path]:
    name = _model3d_repo_name(key)
    if not name:
        return None
    return MODEL3D_BACKENDS_DIR / name


def _model3d_weights_options(key: str) -> List[Dict]:
    suffix = " (recommended)"
    if key == "stepx1":
        base_dir = MODEL3D_WEIGHTS_DIR / "Step1X-3D"
        return [
            {
                "key": "stepx1_default",
                "label": f"stepfun-ai/Step1X-3D{suffix}",
                "repo_id": "stepfun-ai/Step1X-3D",
                "local_dir": str(base_dir),
            }
        ]
    if key == "hunyuan3d2":
        base_dir = MODEL3D_WEIGHTS_DIR / "Hunyuan3D-2"
        return [
            {
                "key": "hunyuan_default",
                "label": f"tencent/Hunyuan3D-2{suffix}",
                "repo_id": "tencent/Hunyuan3D-2",
                "local_dir": str(base_dir),
            }
        ]
    if key == "sam3d":
        return [
            {
                "key": "sam3d_default",
                "label": "facebook/sam-3d-objects",
                "repo_id": "facebook/sam-3d-objects",
                "local_dir": str(_model3d_repo_path("sam3d") / "checkpoints" / "hf"),
            }
        ]
    return []


def _hf_cache_dir() -> Path:
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
        return Path(HF_HUB_CACHE)
    except Exception:
        return Path.home() / ".cache" / "huggingface" / "hub"


def _model3d_clear_hf_cache(repo_id: str) -> None:
    cache_dir = _hf_cache_dir()
    if not cache_dir.exists():
        return
    safe_id = repo_id.replace("/", "--")
    target = cache_dir / f"models--{safe_id}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def _model3d_is_backend_installed(key: str) -> bool:
    repo_path = _model3d_repo_path(key)
    return bool(repo_path and repo_path.exists())


def _model3d_is_weights_installed(key: str) -> bool:
    options = _model3d_weights_options(key)
    if not options:
        return False
    option = options[0]
    local_dir = Path(option["local_dir"])
    return local_dir.exists()


def _model3d_has_custom_rasterizer() -> bool:
    try:
        import custom_rasterizer  # noqa: F401
    except Exception:
        pass
    else:
        return True
    for path in sys.path:
        if not path or "site-packages" not in path.lower():
            continue
        try:
            base = Path(path)
        except Exception:
            continue
        if (base / "custom_rasterizer").exists():
            return True
        for candidate in base.glob("custom_rasterizer*.egg"):
            if candidate.exists():
                return True
        for candidate in base.glob("custom_rasterizer_kernel*.pyd"):
            if candidate.exists():
                return True
    return False


def _model3d_nvcc_version() -> str:
    nvcc = which("nvcc")
    if not nvcc:
        default_nvcc = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin\nvcc.exe")
        if default_nvcc.exists():
            nvcc = str(default_nvcc)
    if not nvcc:
        return ""
    try:
        output = subprocess.check_output([nvcc, "--version"], text=True, stderr=subprocess.STDOUT)
    except Exception:
        return ""
    for line in output.splitlines():
        line = line.strip()
        if "release" in line.lower():
            parts = line.split("release")
            if len(parts) > 1:
                return parts[1].split(",")[0].strip()
    return ""


def _model3d_torch_cuda_version() -> str:
    try:
        import torch
    except Exception:
        return ""
    return str(getattr(torch.version, "cuda", "") or "")


def _model3d_torch_version() -> str:
    try:
        import torch
    except Exception:
        return ""
    return str(getattr(torch, "__version__", "") or "")


def _model3d_torch_at_least(target: str) -> bool:
    torch_version = _model3d_torch_version()
    if not torch_version:
        return False
    try:
        clean = torch_version.split("+")[0]
        return version.parse(clean) >= version.parse(target)
    except Exception:
        return False


def _model3d_compiler_found() -> bool:
    if which("cl"):
        return True
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    return vswhere.exists()


def _model3d_prereqs_status() -> Dict:
    try:
        import pybind11  # noqa: F401
        pybind11_ok = True
    except Exception:
        pybind11_ok = False
    nvcc_version = _model3d_nvcc_version()
    torch_cuda = _model3d_torch_cuda_version()
    torch_version = _model3d_torch_version()
    cuda_match = False
    if nvcc_version and torch_cuda:
        cuda_match = nvcc_version.startswith(torch_cuda)
    return {
        "pybind11_ok": pybind11_ok,
        "compiler_ok": _model3d_compiler_found(),
        "nvcc_version": nvcc_version,
        "torch_cuda": torch_cuda,
        "torch_version": torch_version,
        "cuda_match": cuda_match,
    }


def _model3d_write_stepx1_script(input_path: str, output_dir: str, repo_path: Path) -> Path:
    script_path = MODEL3D_DATA_DIR / "stepx1_run.py"
    weights_dir = MODEL3D_WEIGHTS_DIR / "Step1X-3D"
    script = (
        "import os\n"
        "import sys\n"
        f"sys.path.insert(0, r\"{repo_path}\")\n"
        "import torch\n"
        "import trimesh\n"
        "from step1x3d_geometry.models.pipelines.pipeline import Step1X3DGeometryPipeline\n"
        "from step1x3d_geometry.models.pipelines.pipeline_utils import reduce_face, remove_degenerate_face\n"
        "from step1x3d_texture.pipelines.step1x_3d_texture_synthesis_pipeline import Step1X3DTexturePipeline\n"
        f"input_image = r\"{input_path}\"\n"
        f"out_dir = r\"{output_dir}\"\n"
        "os.makedirs(out_dir, exist_ok=True)\n"
        f"weights_dir = r\"{weights_dir}\"\n"
        "base = weights_dir if weights_dir and os.path.exists(weights_dir) else \"stepfun-ai/Step1X-3D\"\n"
        "geo = Step1X3DGeometryPipeline.from_pretrained(base, subfolder=\"Step1X-3D-Geometry-1300m\").to(\"cuda\")\n"
        "gen = torch.Generator(device=geo.device).manual_seed(2025)\n"
        "out = geo(input_image, guidance_scale=7.5, num_inference_steps=50, generator=gen)\n"
        "mesh_path = os.path.join(out_dir, \"mesh.glb\")\n"
        "out.mesh[0].export(mesh_path)\n"
        "tex = Step1X3DTexturePipeline.from_pretrained(base, subfolder=\"Step1X-3D-Texture\")\n"
        "mesh = trimesh.load(mesh_path)\n"
        "mesh = remove_degenerate_face(mesh)\n"
        "mesh = reduce_face(mesh)\n"
        "textured = tex(input_image, mesh, seed=2025)\n"
        "textured.export(os.path.join(out_dir, \"mesh_textured.glb\"))\n"
    )
    script_path.write_text(script, encoding="utf-8")
    return script_path


def _model3d_write_hunyuan_script(input_path: str, output_dir: str, repo_path: Path) -> Path:
    script_path = MODEL3D_DATA_DIR / "hunyuan_run.py"
    weights_dir = MODEL3D_WEIGHTS_DIR / "Hunyuan3D-2"
    script = (
        "import os\n"
        "import sys\n"
        f"sys.path.insert(0, r\"{repo_path}\")\n"
        "os.environ[\"HF_HUB_DISABLE_PROGRESS_BARS\"] = \"1\"\n"
        "from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline\n"
        "from hy3dgen.texgen import Hunyuan3DPaintPipeline\n"
        f"input_image = r\"{input_path}\"\n"
        f"out_dir = r\"{output_dir}\"\n"
        "os.makedirs(out_dir, exist_ok=True)\n"
        "mesh_path = os.path.join(out_dir, \"mesh.glb\")\n"
        f"weights_dir = r\"{weights_dir}\"\n"
        "base = \"tencent/Hunyuan3D-2\"\n"
        "local_ok = False\n"
        "if weights_dir and os.path.exists(weights_dir):\n"
        "    os.environ[\"HY3DGEN_MODELS\"] = weights_dir\n"
        "    for name in (\"hunyuan3d-dit-v2-0\", \"hunyuan3d-dit-v2-0-fast\", \"hunyuan3d-dit-v2-0-turbo\"):\n"
        "        path = os.path.join(weights_dir, \"tencent\", \"Hunyuan3D-2\", name)\n"
        "        if os.path.exists(path):\n"
        "            local_ok = True\n"
        "            break\n"
        "if local_ok:\n"
        "    os.environ[\"HF_HUB_OFFLINE\"] = \"1\"\n"
        "pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(base)\n"
        "mesh = pipeline(image=input_image)[0]\n"
        "mesh.export(mesh_path)\n"
        "paint = Hunyuan3DPaintPipeline.from_pretrained(base)\n"
        "mesh = paint(mesh, image=input_image)\n"
        "mesh.export(os.path.join(out_dir, \"mesh_textured.glb\"))\n"
    )
    script_path.write_text(script, encoding="utf-8")
    return script_path


def _model3d_write_sam3d_script(image_path: str, mask_path: str, output_dir: str, repo_path: Path) -> Path:
    script_path = MODEL3D_DATA_DIR / "sam3d_run.py"
    script = (
        "import os\n"
        "import sys\n"
        f"sys.path.insert(0, r\"{repo_path}\")\n"
        "from notebook.inference import Inference, load_image, load_mask\n"
        f"image_path = r\"{image_path}\"\n"
        f"mask_path = r\"{mask_path}\"\n"
        f"out_dir = r\"{output_dir}\"\n"
        "os.makedirs(out_dir, exist_ok=True)\n"
        "config_path = os.path.join(\"checkpoints\", \"hf\", \"pipeline.yaml\")\n"
        "inference = Inference(config_path, compile=False)\n"
        "image = load_image(image_path)\n"
        "mask = load_mask(mask_path)\n"
        "output = inference(image, mask, seed=42)\n"
        "output[\"gs\"].save_ply(os.path.join(out_dir, \"sam3d_splat.ply\"))\n"
    )
    script_path.write_text(script, encoding="utf-8")
    return script_path


def _start_http_server(directory: Path, module_key: str, viewer_path: str) -> str:
    port = 8000
    while port < 8100:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                port += 1
                continue
        except Exception:
            break
    python_exe = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [python_exe, "-m", "http.server", str(port), "--directory", str(directory)]
    _run_cmd(f"{module_key}_server_{port}", cmd, cwd=directory)
    return f"http://localhost:{port}/{viewer_path}"


def _mlsharp_list_scenes() -> List[Dict]:
    scenes = []
    output_base = MLSHARP_OUTPUT_DIR
    output_base.mkdir(parents=True, exist_ok=True)
    root_viewer = output_base / "gaussians" / "index.html"
    if root_viewer.exists():
        scenes.append(
            {
                "name": _mlsharp_scene_label(output_base, "Salida actual"),
                "path": str(output_base),
                "has_viewer": True,
                "renamable": True,
            }
        )
    for path in output_base.iterdir():
        if path.is_dir() and path.name.startswith("splat_"):
            display = path.name.replace("splat_", "")
            display = _mlsharp_scene_label(path, display)
            viewer_path = path / "gaussians" / "index.html"
            scenes.append(
                {
                    "name": display,
                    "path": str(path),
                    "has_viewer": viewer_path.exists(),
                    "renamable": True,
                }
            )
    scenes.sort(key=lambda item: item["name"], reverse=True)
    return scenes


def _mlsharp_setup_viewer(output_dir: Path) -> None:
    try:
        gaussians_dir = output_dir / "gaussians"
        gaussians_dir.mkdir(parents=True, exist_ok=True)
        viewer_dst = gaussians_dir / "index.html"
        scene_dst = gaussians_dir / "scene.ply"
        scene_full_dst = gaussians_dir / "scene_full.ply"
        ply_files = [f for f in output_dir.iterdir() if f.suffix == ".ply"]
        if not ply_files:
            _append_log("ml_sharp", "Warning: No .ply file found in output.")
            return
        src_ply = ply_files[0]
        shutil.move(str(src_ply), str(scene_full_dst))
        _append_log("ml_sharp", f"Moved {src_ply.name} to {scene_full_dst}")
        if _mlsharp_simplify_ply(scene_full_dst, scene_dst):
            _append_log("ml_sharp", f"Viewer PLY written to {scene_dst}")
        else:
            shutil.copy(str(scene_full_dst), str(scene_dst))
            _append_log("ml_sharp", "Viewer PLY fallback: copied full PLY.")
        if MLSHARP_VIEWER_TEMPLATE.exists():
            shutil.copy(str(MLSHARP_VIEWER_TEMPLATE), str(viewer_dst))
            _append_log("ml_sharp", f"Viewer created at: {viewer_dst}")
        else:
            _append_log("ml_sharp", f"Error: viewer_template.html not found at {MLSHARP_VIEWER_TEMPLATE}")
    except Exception as exc:
        _append_log("ml_sharp", f"Error setting up viewer: {exc}")


def _mlsharp_torch_status() -> Dict[str, bool]:
    try:
        import torch

        cuda_ok = bool(torch.cuda.is_available()) and torch.version.cuda is not None
        return {"installed": True, "cuda": cuda_ok}
    except Exception:
        return {"installed": False, "cuda": False}


def _mlsharp_scene_label(scene_path: Path, fallback: str) -> str:
    label_path = scene_path / ".scene_name"
    try:
        if label_path.exists():
            value = label_path.read_text(encoding="utf-8").strip()
            if value:
                return value
    except Exception:
        pass
    return fallback


def _mlsharp_write_scene_label(scene_path: Path, name: str) -> None:
    label_path = scene_path / ".scene_name"
    scene_path.mkdir(parents=True, exist_ok=True)
    label_path.write_text(name.strip(), encoding="utf-8")


def _mlsharp_simplify_ply(source: Path, dest: Path) -> bool:
    try:
        from plyfile import PlyData, PlyElement
    except Exception as exc:
        _append_log("ml_sharp", f"PLY simplify skipped: {exc}")
        return False
    try:
        plydata = PlyData.read(str(source))
        vertex = next((elem for elem in plydata.elements if elem.name == "vertex"), None)
        if vertex is None:
            _append_log("ml_sharp", "PLY simplify failed: no vertex element.")
            return False
        vertex_element = PlyElement.describe(vertex.data, "vertex")
        PlyData([vertex_element], text=False, byte_order="<").write(str(dest))
        return True
    except Exception as exc:
        _append_log("ml_sharp", f"PLY simplify failed: {exc}")
        return False


def _mlsharp_checkpoint_path() -> Path:
    return Path.home() / ".cache" / "torch" / "hub" / "checkpoints" / MLSHARP_MODEL_NAME


def _mlsharp_ensure_checkpoint() -> Optional[Path]:
    path = _mlsharp_checkpoint_path()
    try:
        if path.exists() and path.stat().st_size > 1024 * 1024:
            return path
    except Exception:
        pass
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _append_log("ml_sharp", f"Downloading checkpoint to {path}...")
        import urllib.request

        with urllib.request.urlopen(MLSHARP_MODEL_URL) as response, path.open("wb") as out:
            shutil.copyfileobj(response, out)
        if path.exists() and path.stat().st_size > 1024 * 1024:
            return path
    except Exception as exc:
        _append_log("ml_sharp", f"Checkpoint download failed: {exc}")
    return None


def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _research_load_library() -> List[Dict]:
    data = _load_json(RESEARCH_LIBRARY_PATH, [])
    return data if isinstance(data, list) else []


def _research_save_library(library: List[Dict]) -> None:
    _save_json(RESEARCH_LIBRARY_PATH, library)


def _research_load_index() -> List[Dict]:
    data = _load_json(RESEARCH_INDEX_PATH, [])
    return data if isinstance(data, list) else []


def _research_save_index(index: List[Dict]) -> None:
    _save_json(RESEARCH_INDEX_PATH, index)


def _research_get_doc(library: List[Dict], doc_id: str) -> Optional[Dict]:
    for doc in library:
        if doc.get("id") == doc_id:
            return doc
    return None


def _research_extract_pdf_text(path: Path) -> str:
    if not PyPDF2:
        return ""
    try:
        reader = PyPDF2.PdfReader(str(path))
        parts: List[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(parts)
    except Exception:
        return ""


def _research_tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in RESEARCH_STOPWORDS and len(t) > 2]


def _research_term_freq(tokens: List[str]) -> Dict[str, int]:
    tf: Dict[str, int] = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    return tf


def _research_build_idf(chunks: List[Dict]) -> Dict[str, float]:
    df: Dict[str, int] = {}
    for chunk in chunks:
        seen = set(chunk.get("tf", {}).keys())
        for token in seen:
            df[token] = df.get(token, 0) + 1
    n = max(len(chunks), 1)
    idf: Dict[str, float] = {}
    for token, count in df.items():
        idf[token] = math.log((n + 1) / (count + 1)) + 1.0
    return idf


def _research_tfidf(tf: Dict[str, int], idf: Dict[str, float]) -> Dict[str, float]:
    vec: Dict[str, float] = {}
    for token, count in tf.items():
        weight = idf.get(token)
        if weight:
            vec[token] = count * weight
    return vec


def _research_cosine(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    dot = 0.0
    for token, weight in v1.items():
        if token in v2:
            dot += weight * v2[token]
    norm1 = math.sqrt(sum(v * v for v in v1.values()))
    norm2 = math.sqrt(sum(v * v for v in v2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def _research_search(index: List[Dict], query: str, top_k: int = 4) -> List[Dict]:
    q_tf = _research_term_freq(_research_tokenize(query))
    idf = _research_build_idf(index)
    q_vec = _research_tfidf(q_tf, idf)
    scored = []
    for chunk in index:
        c_vec = _research_tfidf(chunk.get("tf", {}), idf)
        score = _research_cosine(q_vec, c_vec)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def _research_chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> List[str]:
    tokens = text.split()
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk = " ".join(tokens[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end == len(tokens):
            break
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(tokens):
            break
    return chunks


def _research_split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _research_extractive_summary(text: str, max_sentences: int = 5) -> str:
    sentences = _research_split_sentences(text)
    if not sentences:
        return ""
    sentence_tfs = [_research_term_freq(_research_tokenize(s)) for s in sentences]
    df: Dict[str, int] = {}
    for tf in sentence_tfs:
        for token in tf.keys():
            df[token] = df.get(token, 0) + 1
    n = len(sentence_tfs)
    idf = {token: math.log((n + 1) / (df_t + 1)) + 1.0 for token, df_t in df.items()}
    scores = []
    for i, tf in enumerate(sentence_tfs):
        score = sum((idf.get(token, 0.0) * count) for token, count in tf.items())
        scores.append((score, i, sentences[i]))
    scores.sort(key=lambda item: item[0], reverse=True)
    top = sorted(scores[:max_sentences], key=lambda item: item[1])
    return " ".join([s for _, _, s in top])


def _research_format_authors(authors_raw: str, style: str) -> str:
    if not authors_raw:
        return ""
    authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
    return ", ".join(authors)


def _research_format_citation(doc: Dict, style: str) -> str:
    title = doc.get("title") or doc.get("original_name") or "Documento"
    authors = _research_format_authors(doc.get("authors", ""), style)
    year = doc.get("year") or "s.f."
    venue = doc.get("venue") or ""
    url = doc.get("url") or ""

    if style == "apa":
        parts = [authors, f"({year}).", title]
        if venue:
            parts.append(venue)
        if url:
            parts.append(url)
        return " ".join(p for p in parts if p).strip()

    if style == "ieee":
        parts = [authors, f"\"{title},\""]
        if venue:
            parts.append(venue + ",")
        parts.append(year + ".")
        if url:
            parts.append(url)
        return " ".join(p for p in parts if p).strip()

    return title


def _research_format_sources(hits: List[Dict], library: List[Dict]) -> str:
    lines = []
    for idx, hit in enumerate(hits, start=1):
        doc = _research_get_doc(library, hit.get("doc_id"))
        if doc:
            title = doc.get("title") or doc.get("original_name") or doc.get("filename")
        else:
            title = "Documento"
        lines.append(f"[{idx}] {title}")
    return "\n".join(lines)


def _research_answer_with_llm(endpoint: str, question: str, context: str) -> str:
    if not endpoint:
        return ""
    system_prompt = (
        "Responde usando solo el contexto provisto. "
        "Si no hay suficiente informacion, explica la limitacion."
    )
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Contexto:\n{context}\n\nPregunta:\n{question}"},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }
    try:
        response = httpx.post(endpoint, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception:
        return ""


def _get_settings() -> Dict:
    settings = _load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings or {})
    return merged


def _set_settings(updates: Dict) -> Dict:
    settings = _get_settings()
    settings.update(updates)
    _save_json(SETTINGS_FILE, settings)
    return settings


def _get_languages() -> Dict:
    return _load_json(LANGUAGES_FILE, {})


def _get_language_bundle(lang: str) -> Dict:
    languages = _get_languages()
    return languages.get(lang, languages.get("es", {}))


def _get_installed_modules() -> List[str]:
    installed = _load_json(INSTALLED_MODULES_FILE, [])
    if "monitor" not in installed:
        installed.insert(0, "monitor")
    return installed


def _save_installed(installed: List[str]) -> None:
    if "monitor" not in installed:
        installed.insert(0, "monitor")
    _save_json(INSTALLED_MODULES_FILE, installed)


def _get_favorites() -> List[str]:
    data = _load_json(FAVORITES_FILE, [])
    if isinstance(data, list):
        return [str(x) for x in data]
    return []


def _save_favorites(favorites: List[str]) -> None:
    cleaned = []
    for key in favorites:
        if key not in cleaned:
            cleaned.append(key)
    _save_json(FAVORITES_FILE, cleaned[:3])


def _build_modules(lang: str) -> List[Dict]:
    bundle = _get_language_bundle(lang)
    compute_labels = {
        "cpu": bundle.get("compute_cpu", "CPU"),
        "gpu": bundle.get("compute_gpu", "GPU"),
        "cpu_or_gpu": bundle.get("compute_cpu_or_gpu", "CPU o GPU"),
        "cpu_gpu": bundle.get("compute_cpu_gpu", "CPU + GPU"),
    }
    installed = set(_get_installed_modules())
    modules = []
    for meta in AVAILABLE_MODULES:
        modules.append(
            {
                "key": meta["key"],
                "category": meta["category"],
                "title": bundle.get(meta["title_key"], meta["key"]),
                "description": bundle.get(meta["desc_key"], ""),
                "plain": bundle.get(MODEL3D_PLAIN_KEYS.get(meta["key"], ""), ""),
                "installed": meta["key"] in installed,
                "compute": compute_labels.get(meta.get("compute"), ""),
                "coming_soon": bool(meta.get("coming_soon")),
            }
        )
    return modules


def _scan_models(model_dir: str, lang: str) -> List[Dict]:
    bundle = _get_language_bundle(lang)
    recommended_suffix = bundle.get("suffix_recommended", " (recommended)")
    search_dir = Path(model_dir)
    models = []
    if not search_dir.exists():
        return models
    for path in search_dir.rglob("*.gguf"):
        name = path.name
        recommended = "qwen2.5-coder-7b-instruct" in name.lower()
        label = f"{name}{recommended_suffix}" if recommended else name
        models.append({"label": label, "path": str(path), "recommended": recommended})
    return models


def _service_status(lang: str) -> List[Dict]:
    bundle = _get_language_bundle(lang)
    services = []
    for srv in SERVICE_META:
        status = PROCESS_MANAGER.get_service_status(srv["key"])
        services.append(
            {
                "key": srv["key"],
                "name": bundle.get(srv["name_key"], srv["key"]),
                "description": bundle.get(srv["desc_key"], ""),
                "port": srv["port"],
                "installed": status.get("installed", False),
                "running": status.get("running", False),
            }
        )
    return services


app = FastAPI(title="UNLZ AI Studio Web Bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModuleAction(BaseModel):
    key: str


class SettingsUpdate(BaseModel):
    language: str | None = None
    model_dir: str | None = None
    show_logs: bool | None = None
    theme: str | None = None


class ServiceAction(BaseModel):
    key: str
    model_path: str | None = None


class GaussianRun(BaseModel):
    input_path: str


class GaussianScene(BaseModel):
    path: str


class PickDialog(BaseModel):
    title: Optional[str] = None
    initial_dir: Optional[str] = None


class CyberInstall(BaseModel):
    branch: str | None = None


class CyberServerStart(BaseModel):
    port: int = 8501
    openai_key: str | None = None
    google_key: str | None = None
    scrapeless_key: str | None = None
    ollama_url: str | None = None


class HYMotionDownload(BaseModel):
    model_key: str


class HYMotionRun(BaseModel):
    model_key: str
    prompt: str
    output_dir: str | None = None


class HYWorldDeps(BaseModel):
    mode: str


class HYWorldRun(BaseModel):
    mode: str
    input_path: str | None = None
    output_dir: str | None = None


class VigaDeps(BaseModel):
    target: str | None = None


class VigaRun(BaseModel):
    runner: str
    task: str
    model: str
    dataset_path: str | None = None
    output_dir: str | None = None
    max_rounds: int | None = None


class VideoMamaRun(BaseModel):
    base_model_path: str
    unet_checkpoint_path: str
    image_root_path: str
    mask_root_path: str
    output_dir: str | None = None
    keep_aspect_ratio: bool = False


class LuxTTSRun(BaseModel):
    text: str
    prompt_audio: str
    output_dir: str | None = None
    model_id: str = "YatharthS/LuxTTS"
    device: str = "auto"
    threads: int = 2
    rms: float = 0.01
    t_shift: float = 0.9
    num_steps: int = 4
    speed: float = 1.0
    return_smooth: bool = False


class VibeVoiceASRRun(BaseModel):
    model_path: str = "microsoft/VibeVoice-ASR"
    audio_file: str
    output_dir: str | None = None
    device: str = "auto"
    max_new_tokens: int = 32768
    temperature: float = 0.0
    top_p: float = 1.0
    num_beams: int = 1
    attn_implementation: str = "flash_attention_2"


class Qwen3TTSRun(BaseModel):
    mode: str = "custom_voice"
    model_id: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    text: str
    language: str = "Auto"
    speaker: str = "Vivian"
    instruct: str | None = None
    ref_audio: str | None = None
    ref_text: str | None = None
    output_dir: str | None = None
    device: str = "auto"
    dtype: str = "bfloat16"
    attn_implementation: str = "flash_attention_2"


class LightOnOCRRun(BaseModel):
    input_path: str
    input_type: str = "auto"
    page: int = 0
    dpi: int = 200
    model_id: str = "lightonai/LightOnOCR-2-1B"
    device: str = "auto"
    dtype: str = "auto"
    max_new_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.9
    output_dir: str | None = None


class PersonaPlexRun(BaseModel):
    input_wav: str
    voice_prompt: str = "NATF2.pt"
    text_prompt: str | None = None
    seed: str = "42424242"
    cpu_offload: bool = False
    output_dir: str | None = None
    hf_token: str | None = None


class IncluIAStart(BaseModel):
    model: str = "tiny"
    port: int = 5000


class KleinDownload(BaseModel):
    model_id: str


class KleinRun(BaseModel):
    model_id: str
    prompt: str
    width: int
    height: int
    steps: int
    guidance: float
    output_dir: str | None = None
    device: str = "auto"
    seed: int | None = None


class LLMChatStart(BaseModel):
    model_path: str


class LLMChatMessage(BaseModel):
    message: str


class LLMDownload(BaseModel):
    repo_id: str
    filename: str


class LLMDelete(BaseModel):
    path: str


class MLSharpRun(BaseModel):
    input_path: str
    output_dir: str | None = None
    device: str | None = None
    render: bool = False


class MLSharpOpen(BaseModel):
    path: str


class MLSharpTorchInstall(BaseModel):
    variant: str = "cpu"


class MLSharpRename(BaseModel):
    path: str
    name: str


class Model3DSetBackend(BaseModel):
    backend_key: str


class Model3DRun(BaseModel):
    backend_key: str
    input_paths: List[str]
    input_mode: str
    output_dir: str | None = None


class Model3DWeights(BaseModel):
    backend_key: str
    weight_key: str


class Model3DHfToken(BaseModel):
    token: str


class Model3DPython(BaseModel):
    command: str


class NeuttsDeps(BaseModel):
    repo_id: str


class NeuttsGenerate(BaseModel):
    repo_id: str
    text: str
    ref_audio: str
    ref_text: str
    device: str = "cpu"


class ResearchAdd(BaseModel):
    path: str


class ResearchRemove(BaseModel):
    doc_id: str


class ResearchMeta(BaseModel):
    doc_id: str
    title: str = ""
    authors: str = ""
    year: str = ""
    venue: str = ""
    url: str = ""


class ResearchDoc(BaseModel):
    doc_id: str


class ResearchAsk(BaseModel):
    question: str
    endpoint: Optional[str] = None


class SpotEditModel(BaseModel):
    backend: str = "qwen"


class SpotEditRun(BaseModel):
    input_path: str
    mask_path: str
    prompt: str = ""
    backend: str = "qwen"
    output_dir: Optional[str] = None


class FinetuneRun(BaseModel):
    dataset_path: str
    output_dir: Optional[str] = None
    epochs: float = 1.0
    batch_size: int = 1
    grad_accum: int = 8
    learning_rate: float = 0.0002
    max_seq_len: int = 4096
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    export_gguf: bool = True
    gguf_quant: str = "q4_k_m"


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/bootstrap")
def bootstrap():
    settings = _get_settings()
    lang = settings.get("language", "es")
    return {
        "settings": settings,
        "language": lang,
        "translations": _get_language_bundle(lang),
        "modules": _build_modules(lang),
        "favorites": _get_favorites(),
    }


@app.post("/ui/pick_file")
def pick_file(payload: PickDialog):
    paths = _pick_file_dialog(payload.title, payload.initial_dir)
    primary = paths[0] if paths else ""
    return {"path": primary, "paths": paths}


@app.post("/ui/pick_folder")
def pick_folder(payload: PickDialog):
    path = _pick_folder_dialog(payload.title, payload.initial_dir)
    return {"path": path}


@app.get("/modules")
def modules():
    settings = _get_settings()
    lang = settings.get("language", "es")
    return {"modules": _build_modules(lang)}


@app.post("/modules/install")
def install_module(action: ModuleAction):
    installed = _get_installed_modules()
    if action.key == "monitor":
        return {"installed": installed}
    if action.key not in installed:
        installed.append(action.key)
        _save_installed(installed)
    return {"installed": installed}


@app.post("/modules/uninstall")
def uninstall_module(action: ModuleAction):
    installed = _get_installed_modules()
    if action.key == "monitor":
        return {"installed": installed}
    if action.key in installed:
        installed.remove(action.key)
        _save_installed(installed)
    return {"installed": installed}


@app.get("/favorites")
def favorites():
    return {"favorites": _get_favorites()}


@app.post("/favorites/add")
def favorites_add(action: ModuleAction):
    favorites = _get_favorites()
    if action.key not in favorites:
        if len(favorites) >= 3:
            return {"favorites": favorites}
        favorites.append(action.key)
    _save_favorites(favorites)
    return {"favorites": _get_favorites()}


@app.post("/favorites/remove")
def favorites_remove(action: ModuleAction):
    favorites = _get_favorites()
    if action.key in favorites:
        favorites.remove(action.key)
    _save_favorites(favorites)
    return {"favorites": _get_favorites()}


@app.get("/settings")
def settings():
    return {"settings": _get_settings()}


@app.post("/settings")
def update_settings(update: SettingsUpdate):
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    settings = _set_settings(updates)
    return {"settings": settings}


@app.get("/monitor")
def monitor():
    settings = _get_settings()
    lang = settings.get("language", "es")
    model_dir = settings.get("model_dir", DEFAULT_SETTINGS["model_dir"])
    sys_info = detect_system_info()
    gpu_names = list(sys_info.gpu_names or [])
    vram_list = list(sys_info.vram_gb_per_gpu or [])
    cuda_available = sys_info.cuda_available
    smi = _query_nvidia_smi()
    if smi:
        gpu_names = smi["names"]
        vram_list = smi["vram"]
        cuda_available = True
    elif not gpu_names:
        wmi = _query_windows_gpu()
        if wmi:
            gpu_names = wmi["names"]
            vram_list = wmi["vram"]
        else:
            cim = _query_windows_gpu_cim()
            if cim:
                gpu_names = cim["names"]
                vram_list = cim["vram"]
    def is_virtual_gpu(name: str) -> bool:
        lowered = name.lower()
        return ("virtual" in lowered) or ("microsoft" in lowered) or ("basic render" in lowered)

    if gpu_names:
        pairs = list(zip(gpu_names, vram_list))
        filtered = [p for p in pairs if not is_virtual_gpu(p[0])]
        if filtered:
            gpu_names = [p[0] for p in filtered]
            vram_list = [p[1] for p in filtered]

    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_temp = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            first_group = next(iter(temps.values()))
            if first_group:
                cpu_temp = first_group[0].current
    except Exception:
        cpu_temp = None

    ram = psutil.virtual_memory()
    ram_used = round(ram.used / (1024**3), 2)
    ram_available = round(ram.available / (1024**3), 2)

    gpu_util = None
    gpu_temp = None
    gpu_mem_used = None
    gpu_mem_total = None
    smi_stats = _query_nvidia_smi_stats()
    if smi_stats and smi_stats.get("util"):
        gpu_util = smi_stats["util"][0]
        gpu_temp = smi_stats["temp"][0]
        gpu_mem_used = smi_stats["mem_used"][0]
        gpu_mem_total = smi_stats["mem_total"][0]

    return {
        "system": {
            "cpu_name": sys_info.cpu_name,
            "cpu_threads": sys_info.cpu_threads,
            "ram_gb": sys_info.ram_gb,
            "ram_used_gb": ram_used,
            "ram_available_gb": ram_available,
            "ram_percent": ram.percent,
            "cpu_percent": cpu_percent,
            "cpu_temp_c": cpu_temp,
            "cuda_available": cuda_available,
            "gpu_names": gpu_names,
            "vram_gb": vram_list,
            "gpu_util": gpu_util,
            "gpu_temp_c": gpu_temp,
            "gpu_mem_used_gb": gpu_mem_used,
            "gpu_mem_total_gb": gpu_mem_total,
        },
        "services": _service_status(lang),
        "models": _scan_models(model_dir, lang),
    }


@app.post("/services/start")
def start_service(action: ServiceAction):
    ports = {s["key"]: s["port"] for s in SERVICE_META}
    if action.key not in ports:
        raise HTTPException(status_code=400, detail="Unknown service key")
    if action.key in ("llm_service", "clm_service") and not action.model_path:
        raise HTTPException(status_code=400, detail="model_path required")
    config = {"port": ports[action.key]}
    if action.key in ("llm_service", "clm_service"):
        config["model_path"] = action.model_path
    PROCESS_MANAGER.start_process(action.key, config)
    return {"ok": True}


@app.post("/services/stop")
def stop_service(action: ServiceAction):
    PROCESS_MANAGER.stop(action.key)
    return {"ok": True}


@app.post("/services/install")
def install_service(action: ServiceAction):
    PROCESS_MANAGER.install_service(action.key)
    return {"ok": True}


@app.post("/services/uninstall")
def uninstall_service(action: ServiceAction):
    PROCESS_MANAGER.uninstall_service(action.key)
    return {"ok": True}


@app.get("/modules/cyberscraper/state")
def cyberscraper_state():
    installed = CYBER_BACKEND_DIR.exists()
    running = _is_running("cyberscraper")
    return {
        "installed": installed,
        "running": running,
        "backend_dir": str(CYBER_BACKEND_DIR),
    }


@app.post("/modules/cyberscraper/install")
def cyberscraper_install(payload: CyberInstall):
    if CYBER_BACKEND_DIR.exists():
        return {"ok": True}
    branch = payload.branch or ""
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["-b", branch])
    cmd.extend(["https://github.com/itsOwen/CyberScraper-2077.git", str(CYBER_BACKEND_DIR)])
    CYBER_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd("cyberscraper", cmd, cwd=CYBER_BACKEND_DIR.parent)
    return {"ok": True}


@app.post("/modules/cyberscraper/uninstall")
def cyberscraper_uninstall():
    if CYBER_BACKEND_DIR.exists():
        shutil.rmtree(CYBER_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/cyberscraper/deps")
def cyberscraper_deps():
    req_path = CYBER_BACKEND_DIR / "requirements.txt"
    if not req_path.exists():
        raise HTTPException(status_code=404, detail="requirements.txt not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("cyberscraper", [python_path, "-m", "pip", "install", "-r", str(req_path)], cwd=CYBER_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/cyberscraper/playwright")
def cyberscraper_playwright():
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("cyberscraper", [python_path, "-m", "playwright", "install"], cwd=CYBER_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/cyberscraper/start")
def cyberscraper_start(payload: CyberServerStart):
    if _is_running("cyberscraper"):
        return {"ok": True}
    if not CYBER_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-m",
        "streamlit",
        "run",
        "main.py",
        "--server.port",
        str(payload.port),
    ]
    env = os.environ.copy()
    if payload.openai_key:
        env["OPENAI_API_KEY"] = payload.openai_key
    if payload.google_key:
        env["GOOGLE_API_KEY"] = payload.google_key
    if payload.scrapeless_key:
        env["SCRAPELESS_API_KEY"] = payload.scrapeless_key
    if payload.ollama_url:
        env["OLLAMA_BASE_URL"] = payload.ollama_url
    _run_cmd("cyberscraper", cmd, cwd=CYBER_BACKEND_DIR, env=env)
    return {"ok": True}


@app.post("/modules/cyberscraper/stop")
def cyberscraper_stop():
    _stop_proc("cyberscraper")
    return {"ok": True}


@app.post("/modules/cyberscraper/open")
def cyberscraper_open():
    if CYBER_BACKEND_DIR.exists():
        os.startfile(str(CYBER_BACKEND_DIR))
    return {"ok": True}


@app.get("/modules/cyberscraper/logs")
def cyberscraper_logs(lines: int = 200):
    return {"lines": _tail_log("cyberscraper", lines)}

@app.post("/modules/cyberscraper/clear_logs")
def cyberscraper_clear_logs():
    _clear_log("cyberscraper")
    return {"ok": True}



@app.get("/modules/hy_motion/state")
def hymotion_state():
    backend_dir = _resolve_hymotion_backend_dir()
    deps_marker = backend_dir / ".deps_installed"
    return {
        "installed": backend_dir.exists(),
        "deps_installed": deps_marker.exists(),
        "backend_dir": str(backend_dir),
        "output_dir": str(HYMOTION_OUTPUT_DIR),
        "running": _is_running("hy_motion"),
    }


@app.post("/modules/hy_motion/install")
def hymotion_install():
    backend_dir = _resolve_hymotion_backend_dir()
    if backend_dir.exists():
        return {"ok": True}
    backend_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", "https://github.com/Tencent-Hunyuan/HY-Motion-1.0", str(backend_dir)]
    _run_cmd("hy_motion", cmd, cwd=backend_dir.parent)
    return {"ok": True}


@app.post("/modules/hy_motion/uninstall")
def hymotion_uninstall():
    backend_dir = _resolve_hymotion_backend_dir()
    if backend_dir.exists():
        shutil.rmtree(backend_dir, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/hy_motion/deps")
def hymotion_deps():
    backend_dir = _resolve_hymotion_backend_dir()
    req_path = backend_dir / "requirements.txt"
    if not req_path.exists():
        raise HTTPException(status_code=404, detail="requirements.txt not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")

    def worker():
        _run_cmd("hy_motion", [python_path, "-m", "pip", "install", "--only-binary=:all:", "PyYAML==6.0.2"], cwd=backend_dir.parent)
        while _is_running("hy_motion"):
            time.sleep(0.5)
        _run_cmd("hy_motion", [python_path, "-m", "pip", "install", "-r", str(req_path)], cwd=backend_dir)
        while _is_running("hy_motion"):
            time.sleep(0.5)
        try:
            (backend_dir / ".deps_installed").write_text("ok", encoding="utf-8")
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True}


@app.post("/modules/hy_motion/download_weights")
def hymotion_download(payload: HYMotionDownload):
    backend_dir = _resolve_hymotion_backend_dir()
    script_path = BASE_DIR / "data" / "hymotion" / "hymotion_download.py"
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-u",
        str(script_path),
        "--model",
        payload.model_key,
        "--output_dir",
        str(backend_dir / "ckpts" / "tencent"),
    ]
    _run_cmd("hy_motion", cmd, cwd=backend_dir.parent)
    return {"ok": True}


@app.post("/modules/hy_motion/run")
def hymotion_run(payload: HYMotionRun):
    backend_dir = _resolve_hymotion_backend_dir()
    model_path = backend_dir / "ckpts" / "tencent" / payload.model_key
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model weights not found")
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    output_dir = Path(payload.output_dir or str(HYMOTION_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = BASE_DIR / "data" / "hymotion"
    temp_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = temp_dir / f"prompt_{int(time.time() * 1000)}.txt"
    prompt_path.write_text(payload.prompt, encoding="utf-8")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(backend_dir / "local_infer.py"),
        "--model_path",
        str(model_path),
        "--input_text_dir",
        str(prompt_path.parent),
        "--output_dir",
        str(output_dir),
        "--disable_duration_est",
        "--disable_rewrite",
    ]
    _run_cmd("hy_motion", cmd, cwd=backend_dir)
    return {"ok": True}


@app.post("/modules/hy_motion/open_output")
def hymotion_open(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/hy_motion/logs")
def hymotion_logs(lines: int = 200):
    return {"lines": _tail_log("hy_motion", lines)}

@app.post("/modules/hy_motion/clear_logs")
def hy_motion_clear_logs():
    _clear_log("hy_motion")
    return {"ok": True}



@app.get("/modules/hyworld/state")
def hyworld_state():
    return {
        "installed": HYWORLD_BACKEND_DIR.exists(),
        "output_dir": str(HYWORLD_OUTPUT_DIR),
        "running": _is_running("hyworld"),
    }


@app.post("/modules/hyworld/install")
def hyworld_install():
    if HYWORLD_BACKEND_DIR.exists():
        return {"ok": True}
    HYWORLD_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", "https://github.com/Tencent-Hunyuan/HunyuanWorld-Mirror", str(HYWORLD_BACKEND_DIR)]
    _run_cmd("hyworld", cmd, cwd=HYWORLD_BACKEND_DIR.parent)
    return {"ok": True}


@app.post("/modules/hyworld/uninstall")
def hyworld_uninstall():
    if HYWORLD_BACKEND_DIR.exists():
        shutil.rmtree(HYWORLD_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/hyworld/deps")
def hyworld_deps(payload: HYWorldDeps):
    if not HYWORLD_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    mode = payload.mode or "demo"
    req_name = "requirements_demo.txt" if mode == "demo" else "requirements.txt"
    req_path = HYWORLD_BACKEND_DIR / req_name
    if not req_path.exists():
        raise HTTPException(status_code=404, detail=f"{req_name} not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("hyworld", [python_path, "-m", "pip", "install", "-r", str(req_path)], cwd=HYWORLD_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/hyworld/download_weights")
def hyworld_download():
    if not HYWORLD_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-m",
        "huggingface_hub",
        "download",
        "tencent/HunyuanWorld-Mirror",
        "--local-dir",
        str(HYWORLD_BACKEND_DIR / "ckpts"),
    ]
    _run_cmd("hyworld", cmd, cwd=HYWORLD_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/hyworld/run")
def hyworld_run(payload: HYWorldRun):
    if not HYWORLD_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    mode = payload.mode or "demo"
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    if mode == "demo":
        app_path = HYWORLD_BACKEND_DIR / "app.py"
        if not app_path.exists():
            raise HTTPException(status_code=404, detail="app.py not found")
        _run_cmd("hyworld", [python_path, str(app_path)], cwd=HYWORLD_BACKEND_DIR)
        return {"ok": True}
    input_path = payload.input_path or ""
    if not input_path:
        raise HTTPException(status_code=400, detail="input_path required")
    output_dir = Path(payload.output_dir or str(HYWORLD_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = HYWORLD_BACKEND_DIR / "infer.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="infer.py not found")
    _run_cmd("hyworld", [python_path, str(script_path), "--input_path", input_path, "--output_path", str(output_dir)], cwd=HYWORLD_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/hyworld/open_output")
def hyworld_open(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/hyworld/logs")
def hyworld_logs(lines: int = 200):
    return {"lines": _tail_log("hyworld", lines)}

@app.post("/modules/hyworld/clear_logs")
def hyworld_clear_logs():
    _clear_log("hyworld")
    return {"ok": True}


def _viga_sam_path() -> Path:
    return VIGA_BACKEND_DIR / "utils" / "third_party" / "sam" / "sam_vit_h_4b8939.pth"


@app.get("/modules/viga/state")
def viga_state():
    return {
        "installed": VIGA_BACKEND_DIR.exists(),
        "output_dir": str(VIGA_OUTPUT_DIR),
        "running": _is_running("viga"),
        "sam_downloaded": _viga_sam_path().exists(),
    }


@app.post("/modules/viga/install")
def viga_install():
    if VIGA_BACKEND_DIR.exists():
        return {"ok": True}
    VIGA_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)

    def worker():
        rc = _run_cmd_blocking(
            "viga",
            ["git", "clone", "--depth", "1", "https://github.com/Fugtemypt123/VIGA", str(VIGA_BACKEND_DIR)],
            cwd=VIGA_BACKEND_DIR.parent,
        )
        if rc == 0:
            _run_cmd_blocking(
                "viga",
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=VIGA_BACKEND_DIR,
            )

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True}


@app.post("/modules/viga/uninstall")
def viga_uninstall():
    if VIGA_BACKEND_DIR.exists():
        shutil.rmtree(VIGA_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/viga/deps")
def viga_deps(payload: VigaDeps):
    if not VIGA_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    target = (payload.target or "agent").lower()
    req_map = {
        "agent": "requirements/requirement_agent.txt",
        "blender": "requirements/requirement_blender.txt",
        "sam": "requirements/requirement_sam.txt",
    }
    req_rel = req_map.get(target)
    if not req_rel:
        raise HTTPException(status_code=400, detail="Unknown dependency target")
    req_path = VIGA_BACKEND_DIR / req_rel
    if not req_path.exists():
        raise HTTPException(status_code=404, detail=f"{req_rel} not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("viga", [python_path, "-m", "pip", "install", "-r", str(req_path)], cwd=VIGA_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/viga/download_sam")
def viga_download_sam():
    if not VIGA_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    target = _viga_sam_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    def worker():
        _append_log("viga", f"$ download {VIGA_SAM_URL}")
        try:
            with httpx.stream("GET", VIGA_SAM_URL, timeout=120) as response:
                response.raise_for_status()
                with target.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        if chunk:
                            handle.write(chunk)
            _append_log("viga", "[done] sam download")
        except Exception as exc:
            _append_log("viga", f"[error] {exc}")

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True}


@app.post("/modules/viga/run")
def viga_run(payload: VigaRun):
    if not VIGA_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    runner = payload.runner.strip()
    task = payload.task.strip()
    model = payload.model.strip()
    if not runner or not task or not model:
        raise HTTPException(status_code=400, detail="runner, task, and model are required")
    script_path = VIGA_BACKEND_DIR / "runners" / f"{runner}.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Runner not found")
    default_dataset = "data/dynamic_scene" if runner == "dynamic_scene" else "data/static_scene"
    dataset_path = payload.dataset_path or default_dataset
    output_dir = Path(
        payload.output_dir
        or str(VIGA_OUTPUT_DIR / f"{runner}_{time.strftime('%Y%m%d_%H%M%S')}")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--task",
        task,
        "--model",
        model,
        "--dataset-path",
        dataset_path,
        "--output-dir",
        str(output_dir),
    ]
    if payload.max_rounds:
        cmd.extend(["--max-rounds", str(payload.max_rounds)])
    _run_cmd("viga", cmd, cwd=VIGA_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/viga/open_output")
def viga_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/viga/logs")
def viga_logs(lines: int = 200):
    return {"lines": _tail_log("viga", lines)}


@app.post("/modules/viga/clear_logs")
def viga_clear_logs():
    _clear_log("viga")
    return {"ok": True}


@app.get("/modules/videomama/state")
def videomama_state():
    return {
        "installed": VIDEOMAMA_BACKEND_DIR.exists(),
        "output_dir": str(VIDEOMAMA_OUTPUT_DIR),
        "running": _is_running("videomama"),
    }


@app.post("/modules/videomama/install")
def videomama_install():
    if VIDEOMAMA_BACKEND_DIR.exists():
        return {"ok": True}
    VIDEOMAMA_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "videomama",
        ["git", "clone", "--depth", "1", "https://github.com/cvlab-kaist/VideoMaMa", str(VIDEOMAMA_BACKEND_DIR)],
        cwd=VIDEOMAMA_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/videomama/uninstall")
def videomama_uninstall():
    if VIDEOMAMA_BACKEND_DIR.exists():
        shutil.rmtree(VIDEOMAMA_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/videomama/deps")
def videomama_deps():
    if not VIDEOMAMA_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    script_path = VIDEOMAMA_BACKEND_DIR / "scripts" / "setup.sh"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="setup.sh not found")
    _run_cmd("videomama", ["bash", str(script_path)], cwd=VIDEOMAMA_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/videomama/run")
def videomama_run(payload: VideoMamaRun):
    if not VIDEOMAMA_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    script_path = VIDEOMAMA_BACKEND_DIR / "inference_onestep_folder.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="inference_onestep_folder.py not found")
    output_dir = Path(payload.output_dir or str(VIDEOMAMA_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--base_model_path",
        payload.base_model_path,
        "--unet_checkpoint_path",
        payload.unet_checkpoint_path,
        "--image_root_path",
        payload.image_root_path,
        "--mask_root_path",
        payload.mask_root_path,
        "--output_dir",
        str(output_dir),
    ]
    if payload.keep_aspect_ratio:
        cmd.append("--keep_aspect_ratio")
    _run_cmd("videomama", cmd, cwd=VIDEOMAMA_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/videomama/open_output")
def videomama_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/videomama/logs")
def videomama_logs(lines: int = 200):
    return {"lines": _tail_log("videomama", lines)}


@app.post("/modules/videomama/clear_logs")
def videomama_clear_logs():
    _clear_log("videomama")
    return {"ok": True}


@app.get("/modules/luxtts/state")
def luxtts_state():
    return {
        "installed": LUXTTS_BACKEND_DIR.exists(),
        "output_dir": str(LUXTTS_OUTPUT_DIR),
        "running": _is_running("luxtts"),
    }


@app.post("/modules/luxtts/install")
def luxtts_install():
    if LUXTTS_BACKEND_DIR.exists():
        return {"ok": True}
    LUXTTS_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "luxtts",
        ["git", "clone", "--depth", "1", "https://github.com/ysharma3501/LuxTTS", str(LUXTTS_BACKEND_DIR)],
        cwd=LUXTTS_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/luxtts/uninstall")
def luxtts_uninstall():
    if LUXTTS_BACKEND_DIR.exists():
        shutil.rmtree(LUXTTS_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/luxtts/deps")
def luxtts_deps():
    if not LUXTTS_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    req_path = LUXTTS_BACKEND_DIR / "requirements.txt"
    if not req_path.exists():
        raise HTTPException(status_code=404, detail="requirements.txt not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("luxtts", [python_path, "-m", "pip", "install", "-r", str(req_path)], cwd=LUXTTS_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/luxtts/run")
def luxtts_run(payload: LuxTTSRun):
    if not LUXTTS_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    if not payload.prompt_audio.strip():
        raise HTTPException(status_code=400, detail="Prompt audio is required")
    script_path = BASE_DIR / "data" / "luxtts" / "luxtts_infer.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="luxtts_infer.py not found")
    output_dir = Path(payload.output_dir or str(LUXTTS_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--model_id",
        payload.model_id,
        "--device",
        payload.device,
        "--threads",
        str(payload.threads),
        "--text",
        payload.text,
        "--prompt_audio",
        payload.prompt_audio,
        "--output_dir",
        str(output_dir),
        "--rms",
        str(payload.rms),
        "--t_shift",
        str(payload.t_shift),
        "--num_steps",
        str(payload.num_steps),
        "--speed",
        str(payload.speed),
    ]
    if payload.return_smooth:
        cmd.append("--return_smooth")
    _run_cmd("luxtts", cmd, cwd=LUXTTS_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/luxtts/open_output")
def luxtts_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/luxtts/logs")
def luxtts_logs(lines: int = 200):
    return {"lines": _tail_log("luxtts", lines)}


@app.post("/modules/luxtts/clear_logs")
def luxtts_clear_logs():
    _clear_log("luxtts")
    return {"ok": True}


@app.get("/modules/vibevoice_asr/state")
def vibevoice_state():
    return {
        "installed": VIBEVOICE_BACKEND_DIR.exists(),
        "output_dir": str(VIBEVOICE_OUTPUT_DIR),
        "running": _is_running("vibevoice_asr"),
    }


@app.post("/modules/vibevoice_asr/install")
def vibevoice_install():
    if VIBEVOICE_BACKEND_DIR.exists():
        return {"ok": True}
    VIBEVOICE_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "vibevoice_asr",
        ["git", "clone", "--depth", "1", "https://github.com/microsoft/VibeVoice", str(VIBEVOICE_BACKEND_DIR)],
        cwd=VIBEVOICE_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/vibevoice_asr/uninstall")
def vibevoice_uninstall():
    if VIBEVOICE_BACKEND_DIR.exists():
        shutil.rmtree(VIBEVOICE_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/vibevoice_asr/deps")
def vibevoice_deps():
    if not VIBEVOICE_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd(
        "vibevoice_asr",
        [python_path, "-m", "pip", "install", "-e", ".[asr]"],
        cwd=VIBEVOICE_BACKEND_DIR,
    )
    return {"ok": True}


@app.post("/modules/vibevoice_asr/run")
def vibevoice_run(payload: VibeVoiceASRRun):
    if not VIBEVOICE_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    if not payload.audio_file.strip():
        raise HTTPException(status_code=400, detail="audio_file is required")
    script_path = BASE_DIR / "data" / "vibevoice_asr" / "vibevoice_asr_infer.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="vibevoice_asr_infer.py not found")
    output_dir = Path(payload.output_dir or str(VIBEVOICE_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--model_path",
        payload.model_path,
        "--audio_file",
        payload.audio_file,
        "--output_dir",
        str(output_dir),
        "--device",
        payload.device,
        "--max_new_tokens",
        str(payload.max_new_tokens),
        "--temperature",
        str(payload.temperature),
        "--top_p",
        str(payload.top_p),
        "--num_beams",
        str(payload.num_beams),
        "--attn_implementation",
        payload.attn_implementation,
    ]
    _run_cmd("vibevoice_asr", cmd, cwd=VIBEVOICE_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/vibevoice_asr/open_output")
def vibevoice_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/vibevoice_asr/logs")
def vibevoice_logs(lines: int = 200):
    return {"lines": _tail_log("vibevoice_asr", lines)}


@app.post("/modules/vibevoice_asr/clear_logs")
def vibevoice_clear_logs():
    _clear_log("vibevoice_asr")
    return {"ok": True}


@app.get("/modules/frankenmotion/state")
def frankenmotion_state():
    return {
        "installed": FRANKENMOTION_BACKEND_DIR.exists(),
        "running": _is_running("frankenmotion"),
    }


@app.post("/modules/frankenmotion/install")
def frankenmotion_install():
    if FRANKENMOTION_BACKEND_DIR.exists():
        return {"ok": True}
    FRANKENMOTION_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "frankenmotion",
        ["git", "clone", "--depth", "1", "https://github.com/Coral79/FrankenMotion-Code", str(FRANKENMOTION_BACKEND_DIR)],
        cwd=FRANKENMOTION_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/frankenmotion/uninstall")
def frankenmotion_uninstall():
    if FRANKENMOTION_BACKEND_DIR.exists():
        shutil.rmtree(FRANKENMOTION_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.get("/modules/frankenmotion/logs")
def frankenmotion_logs(lines: int = 200):
    return {"lines": _tail_log("frankenmotion", lines)}


@app.post("/modules/frankenmotion/clear_logs")
def frankenmotion_clear_logs():
    _clear_log("frankenmotion")
    return {"ok": True}


@app.get("/modules/omni_transfer/state")
def omnitransfer_state():
    return {
        "installed": OMNITRANSFER_BACKEND_DIR.exists(),
        "running": _is_running("omni_transfer"),
    }


@app.post("/modules/omni_transfer/install")
def omnitransfer_install():
    if OMNITRANSFER_BACKEND_DIR.exists():
        return {"ok": True}
    OMNITRANSFER_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "omni_transfer",
        ["git", "clone", "--depth", "1", "https://github.com/PangzeCheung/OmniTransfer", str(OMNITRANSFER_BACKEND_DIR)],
        cwd=OMNITRANSFER_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/omni_transfer/uninstall")
def omnitransfer_uninstall():
    if OMNITRANSFER_BACKEND_DIR.exists():
        shutil.rmtree(OMNITRANSFER_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.get("/modules/omni_transfer/logs")
def omnitransfer_logs(lines: int = 200):
    return {"lines": _tail_log("omni_transfer", lines)}


@app.post("/modules/omni_transfer/clear_logs")
def omnitransfer_clear_logs():
    _clear_log("omni_transfer")
    return {"ok": True}


@app.get("/modules/qwen3_tts/state")
def qwen3_tts_state():
    return {
        "installed": QWEN3TTS_BACKEND_DIR.exists(),
        "output_dir": str(QWEN3TTS_OUTPUT_DIR),
        "running": _is_running("qwen3_tts"),
    }


@app.post("/modules/qwen3_tts/install")
def qwen3_tts_install():
    if QWEN3TTS_BACKEND_DIR.exists():
        return {"ok": True}
    QWEN3TTS_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "qwen3_tts",
        ["git", "clone", "--depth", "1", "https://github.com/QwenLM/Qwen3-TTS", str(QWEN3TTS_BACKEND_DIR)],
        cwd=QWEN3TTS_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/qwen3_tts/uninstall")
def qwen3_tts_uninstall():
    if QWEN3TTS_BACKEND_DIR.exists():
        shutil.rmtree(QWEN3TTS_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/qwen3_tts/deps")
def qwen3_tts_deps():
    if not QWEN3TTS_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("qwen3_tts", [python_path, "-m", "pip", "install", "-e", "."], cwd=QWEN3TTS_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/qwen3_tts/run")
def qwen3_tts_run(payload: Qwen3TTSRun):
    if not QWEN3TTS_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    script_path = BASE_DIR / "data" / "qwen3_tts" / "qwen3_tts_infer.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="qwen3_tts_infer.py not found")
    output_dir = Path(payload.output_dir or str(QWEN3TTS_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--mode",
        payload.mode,
        "--model_id",
        payload.model_id,
        "--text",
        payload.text,
        "--language",
        payload.language,
        "--speaker",
        payload.speaker,
        "--output_dir",
        str(output_dir),
        "--device",
        payload.device,
        "--dtype",
        payload.dtype,
        "--attn_implementation",
        payload.attn_implementation,
    ]
    if payload.instruct:
        cmd.extend(["--instruct", payload.instruct])
    if payload.ref_audio:
        cmd.extend(["--ref_audio", payload.ref_audio])
    if payload.ref_text:
        cmd.extend(["--ref_text", payload.ref_text])
    _run_cmd("qwen3_tts", cmd, cwd=QWEN3TTS_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/qwen3_tts/open_output")
def qwen3_tts_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/qwen3_tts/logs")
def qwen3_tts_logs(lines: int = 200):
    return {"lines": _tail_log("qwen3_tts", lines)}


@app.post("/modules/qwen3_tts/clear_logs")
def qwen3_tts_clear_logs():
    _clear_log("qwen3_tts")
    return {"ok": True}


@app.get("/modules/lightonocr/state")
def lightonocr_state():
    return {
        "installed": LIGHTONOCR_BACKEND_DIR.exists(),
        "output_dir": str(LIGHTONOCR_OUTPUT_DIR),
        "running": _is_running("lightonocr"),
    }


@app.post("/modules/lightonocr/install")
def lightonocr_install():
    if LIGHTONOCR_BACKEND_DIR.exists():
        return {"ok": True}
    LIGHTONOCR_BACKEND_DIR.mkdir(parents=True, exist_ok=True)
    marker = LIGHTONOCR_BACKEND_DIR / "SOURCE.txt"
    marker.write_text("https://huggingface.co/lightonai/LightOnOCR-2-1B\n", encoding="utf-8")
    return {"ok": True}


@app.post("/modules/lightonocr/uninstall")
def lightonocr_uninstall():
    if LIGHTONOCR_BACKEND_DIR.exists():
        shutil.rmtree(LIGHTONOCR_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/lightonocr/deps")
def lightonocr_deps():
    if not LIGHTONOCR_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd(
        "lightonocr",
        [
            python_path,
            "-m",
            "pip",
            "install",
            "git+https://github.com/huggingface/transformers",
            "pillow",
            "pypdfium2",
        ],
        cwd=LIGHTONOCR_BACKEND_DIR,
    )
    return {"ok": True}


@app.post("/modules/lightonocr/run")
def lightonocr_run(payload: LightOnOCRRun):
    if not LIGHTONOCR_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    if not payload.input_path.strip():
        raise HTTPException(status_code=400, detail="input_path is required")
    script_path = BASE_DIR / "data" / "lightonocr" / "lightonocr_infer.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="lightonocr_infer.py not found")
    output_dir = Path(payload.output_dir or str(LIGHTONOCR_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--input_path",
        payload.input_path,
        "--input_type",
        payload.input_type,
        "--page",
        str(payload.page),
        "--dpi",
        str(payload.dpi),
        "--model_id",
        payload.model_id,
        "--device",
        payload.device,
        "--dtype",
        payload.dtype,
        "--max_new_tokens",
        str(payload.max_new_tokens),
        "--temperature",
        str(payload.temperature),
        "--top_p",
        str(payload.top_p),
        "--output_dir",
        str(output_dir),
    ]
    _run_cmd("lightonocr", cmd, cwd=LIGHTONOCR_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/lightonocr/open_output")
def lightonocr_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/lightonocr/logs")
def lightonocr_logs(lines: int = 200):
    return {"lines": _tail_log("lightonocr", lines)}


@app.post("/modules/lightonocr/clear_logs")
def lightonocr_clear_logs():
    _clear_log("lightonocr")
    return {"ok": True}


@app.get("/modules/personaplex/state")
def personaplex_state():
    return {
        "installed": PERSONAPLEX_BACKEND_DIR.exists(),
        "output_dir": str(PERSONAPLEX_OUTPUT_DIR),
        "running": _is_running("personaplex"),
    }


@app.post("/modules/personaplex/install")
def personaplex_install():
    if PERSONAPLEX_BACKEND_DIR.exists():
        return {"ok": True}
    PERSONAPLEX_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        "personaplex",
        ["git", "clone", "--depth", "1", "https://github.com/NVIDIA/personaplex", str(PERSONAPLEX_BACKEND_DIR)],
        cwd=PERSONAPLEX_BACKEND_DIR.parent,
    )
    return {"ok": True}


@app.post("/modules/personaplex/uninstall")
def personaplex_uninstall():
    if PERSONAPLEX_BACKEND_DIR.exists():
        shutil.rmtree(PERSONAPLEX_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/personaplex/deps")
def personaplex_deps():
    if not PERSONAPLEX_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd(
        "personaplex",
        [python_path, "-m", "pip", "install", "moshi/.", "accelerate"],
        cwd=PERSONAPLEX_BACKEND_DIR,
    )
    return {"ok": True}


@app.post("/modules/personaplex/run")
def personaplex_run(payload: PersonaPlexRun):
    if not PERSONAPLEX_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    if not payload.input_wav.strip():
        raise HTTPException(status_code=400, detail="input_wav is required")
    script_path = BASE_DIR / "data" / "personaplex" / "personaplex_offline.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="personaplex_offline.py not found")
    output_dir = Path(payload.output_dir or str(PERSONAPLEX_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        str(script_path),
        "--repo_dir",
        str(PERSONAPLEX_BACKEND_DIR),
        "--input_wav",
        payload.input_wav,
        "--voice_prompt",
        payload.voice_prompt,
        "--seed",
        payload.seed,
        "--output_dir",
        str(output_dir),
    ]
    if payload.text_prompt:
        cmd.extend(["--text_prompt", payload.text_prompt])
    if payload.cpu_offload:
        cmd.append("--cpu_offload")
    if payload.hf_token:
        cmd.extend(["--hf_token", payload.hf_token])
    _run_cmd("personaplex", cmd, cwd=PERSONAPLEX_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/personaplex/open_output")
def personaplex_open_output(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/personaplex/logs")
def personaplex_logs(lines: int = 200):
    return {"lines": _tail_log("personaplex", lines)}


@app.post("/modules/personaplex/clear_logs")
def personaplex_clear_logs():
    _clear_log("personaplex")
    return {"ok": True}

def _incluia_deps_missing() -> bool:
    required = ("flask", "flask_socketio", "faster_whisper", "speech_recognition", "numpy")
    return any(importlib.util.find_spec(name) is None for name in required)


def _ensure_incluia_deps() -> None:
    if not _incluia_deps_missing():
        return
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    if INCLUIA_REQ_PATH.exists():
        cmd = [python_path, "-m", "pip", "install", "-r", str(INCLUIA_REQ_PATH)]
    else:
        cmd = [
            python_path,
            "-m",
            "pip",
            "install",
            "flask",
            "flask-socketio",
            "faster-whisper",
            "SpeechRecognition",
            "numpy",
        ]
    _append_log("inclu_ia", "Instalando dependencias de Inclu-IA...")
    rc = _run_cmd_blocking("inclu_ia", cmd, cwd=INCLUIA_SERVER_PATH.parent)
    if rc != 0:
        raise HTTPException(status_code=500, detail="No se pudieron instalar las dependencias de Inclu-IA.")


def _pick_file_dialog(title: Optional[str], initial_dir: Optional[str]) -> List[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"tkinter no disponible: {exc}")
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    filetypes = [("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All files", "*.*")]
    paths = filedialog.askopenfilenames(
        title=title or "Select file",
        initialdir=initial_dir or "",
        filetypes=filetypes,
    )
    try:
        root.destroy()
    except Exception:
        pass
    return list(paths) if paths else []


def _pick_folder_dialog(title: Optional[str], initial_dir: Optional[str]) -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"tkinter no disponible: {exc}")
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    path = filedialog.askdirectory(
        title=title or "Select folder",
        initialdir=initial_dir or "",
    )
    try:
        root.destroy()
    except Exception:
        pass
    return path or ""


@app.get("/modules/inclu_ia/state")
def incluia_state():
    running = _is_running("inclu_ia")
    port = MODULE_STATE.get("inclu_ia_port", 5000)
    model = MODULE_STATE.get("inclu_ia_model", "tiny")
    ip = _get_local_ip()
    return {
        "running": running,
        "port": port,
        "model": model,
        "url": f"http://{ip}:{port}",
    }


@app.post("/modules/inclu_ia/start")
def incluia_start(payload: IncluIAStart):
    if _is_running("inclu_ia"):
        return {"ok": True}
    if not INCLUIA_SERVER_PATH.exists():
        raise HTTPException(status_code=404, detail="server.py not found")
    _ensure_incluia_deps()
    model = payload.model or "tiny"
    port = payload.port or 5000
    MODULE_STATE["inclu_ia_model"] = model
    MODULE_STATE["inclu_ia_port"] = port
    cmd = [sys.executable, str(INCLUIA_SERVER_PATH), "--model", model, "--port", str(port)]
    _run_cmd("inclu_ia", cmd, cwd=INCLUIA_SERVER_PATH.parent)
    return {"ok": True}


@app.post("/modules/inclu_ia/stop")
def incluia_stop():
    _stop_proc("inclu_ia")
    return {"ok": True}


@app.get("/modules/inclu_ia/logs")
def incluia_logs(lines: int = 200):
    return {"lines": _tail_log("inclu_ia", lines)}

@app.post("/modules/inclu_ia/clear_logs")
def inclu_ia_clear_logs():
    _clear_log("inclu_ia")
    return {"ok": True}



@app.get("/modules/klein/state")
def klein_state():
    return {
        "deps_ok": _klein_deps_ok(),
        "output_dir": str(KLEIN_OUTPUT_DIR),
        "running": _is_running("klein"),
    }


@app.post("/modules/klein/deps")
def klein_deps():
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    packages = ["diffusers", "transformers", "accelerate", "safetensors", "huggingface_hub", "pillow"]
    _run_cmd("klein", [python_path, "-m", "pip", "install", *packages], cwd=KLEIN_DATA_DIR)
    return {"ok": True}


@app.post("/modules/klein/download")
def klein_download(payload: KleinDownload):
    script_path = KLEIN_DATA_DIR / "klein_run.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="klein_run.py not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _run_cmd("klein", [python_path, "-u", str(script_path), "--model", payload.model_id, "--download-only"], cwd=KLEIN_DATA_DIR)
    return {"ok": True}


@app.post("/modules/klein/run")
def klein_run(payload: KleinRun):
    script_path = KLEIN_DATA_DIR / "klein_run.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="klein_run.py not found")
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt required")
    output_dir = Path(payload.output_dir or str(KLEIN_OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"klein_{int(time.time() * 1000)}.png"
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-u",
        str(script_path),
        "--model",
        payload.model_id,
        "--prompt",
        payload.prompt,
        "--width",
        str(payload.width),
        "--height",
        str(payload.height),
        "--steps",
        str(payload.steps),
        "--guidance",
        str(payload.guidance),
        "--output",
        str(output_path),
        "--device",
        payload.device,
    ]
    if payload.seed is not None:
        cmd.extend(["--seed", str(payload.seed)])
    _run_cmd("klein", cmd, cwd=KLEIN_DATA_DIR)
    return {"ok": True, "output": str(output_path)}


@app.post("/modules/klein/open_output")
def klein_open(payload: GaussianScene):
    target = Path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/klein/logs")
def klein_logs(lines: int = 200):
    return {"lines": _tail_log("klein", lines)}

@app.post("/modules/klein/clear_logs")
def klein_clear_logs():
    _clear_log("klein")
    return {"ok": True}



@app.get("/modules/llm_frontend/state")
def llm_frontend_state():
    settings = _get_settings()
    model_dir = settings.get("model_dir", DEFAULT_SETTINGS["model_dir"])
    models = _scan_models(model_dir, settings.get("language", "es"))
    return {
        "running": PROCESS_MANAGER.is_running("llm_chat"),
        "model_dir": model_dir,
        "models": models,
    }


@app.post("/modules/llm_frontend/start")
def llm_frontend_start(payload: LLMChatStart):
    if PROCESS_MANAGER.is_running("llm_chat"):
        return {"ok": True}
    config = {
        "model_path": payload.model_path,
        "port": 8081,
        "host": "127.0.0.1",
        "ctx_size": 2048,
        "n_gpu_layers": 99,
    }
    PROCESS_MANAGER.start_process("llm_chat", config)
    return {"ok": True}


@app.post("/modules/llm_frontend/stop")
def llm_frontend_stop():
    PROCESS_MANAGER.stop("llm_chat")
    return {"ok": True}


@app.post("/modules/llm_frontend/chat")
def llm_frontend_chat(payload: LLMChatMessage):
    if not PROCESS_MANAGER.is_running("llm_chat"):
        raise HTTPException(status_code=400, detail="Chat server not running")
    body = {
        "messages": [{"role": "user", "content": payload.message}],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    try:
        _append_log("llm_frontend", f"[user] {payload.message}")
        response = httpx.post("http://127.0.0.1:8081/v1/chat/completions", json=body, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        _append_log("llm_frontend", f"[assistant] {answer}")
        return {"answer": answer}
    except Exception as exc:
        _append_log("llm_frontend", f"[error] {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/modules/llm_frontend/delete")
def llm_frontend_delete(payload: LLMDelete):
    path = Path(payload.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Model file not found")
    path.unlink()
    return {"ok": True}


@app.post("/modules/llm_frontend/download")
def llm_frontend_download(payload: LLMDownload):
    from huggingface_hub import hf_hub_download

    settings = _get_settings()
    model_dir = Path(settings.get("model_dir", DEFAULT_SETTINGS["model_dir"]))
    model_dir.mkdir(parents=True, exist_ok=True)
    hf_hub_download(
        repo_id=payload.repo_id,
        filename=payload.filename,
        local_dir=str(model_dir),
        local_dir_use_symlinks=False,
    )
    return {"ok": True}


@app.get("/modules/llm_frontend/logs")
def llm_frontend_logs(lines: int = 200):
    return {"lines": _tail_log("llm_frontend", lines)}

@app.post("/modules/llm_frontend/clear_logs")
def llm_frontend_clear_logs():
    _clear_log("llm_frontend")
    return {"ok": True}



@app.get("/modules/ml_sharp/state")
def mlsharp_state():
    scenes = _mlsharp_list_scenes()
    current = MODULE_STATE.get("ml_sharp_last_output")
    torch_status = _mlsharp_torch_status()
    return {
        "installed": MLSHARP_BACKEND_DIR.exists(),
        "deps_installed": (MLSHARP_BACKEND_DIR / ".deps_installed").exists(),
        "output_dir": str(MLSHARP_OUTPUT_DIR),
        "running": _is_running("ml_sharp"),
        "scenes": scenes,
        "last_output": current,
        "torch_installed": torch_status["installed"],
        "torch_cuda": torch_status["cuda"],
    }


@app.post("/modules/ml_sharp/deps")
def mlsharp_deps():
    if not MLSHARP_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    req_path = MLSHARP_BACKEND_DIR / "requirements.txt"
    if not req_path.exists():
        raise HTTPException(status_code=404, detail="requirements.txt not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")

    def worker():
        rc = _run_cmd_blocking(
            "ml_sharp",
            [python_path, "-m", "pip", "install", "-r", str(req_path)],
            cwd=MLSHARP_BACKEND_DIR,
        )
        if rc != 0:
            _append_log("ml_sharp", "Retrying pip install with --user and force reinstall...")
            rc = _run_cmd_blocking(
                "ml_sharp",
                [
                    python_path,
                    "-m",
                    "pip",
                    "install",
                    "--user",
                    "--upgrade",
                    "--force-reinstall",
                    "--no-cache-dir",
                    "-r",
                    str(req_path),
                ],
                cwd=MLSHARP_BACKEND_DIR,
            )
        if rc == 0:
            rc = _run_cmd_blocking(
                "ml_sharp",
                [python_path, "-m", "pip", "install", "-e", str(MLSHARP_BACKEND_DIR)],
                cwd=MLSHARP_BACKEND_DIR,
            )
            if rc != 0:
                _append_log("ml_sharp", "Retrying editable install with --user...")
                rc = _run_cmd_blocking(
                    "ml_sharp",
                    [python_path, "-m", "pip", "install", "--user", "-e", str(MLSHARP_BACKEND_DIR)],
                    cwd=MLSHARP_BACKEND_DIR,
                )
        try:
            (MLSHARP_BACKEND_DIR / ".deps_installed").write_text("ok", encoding="utf-8")
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True}


@app.post("/modules/ml_sharp/install_torch")
def mlsharp_install_torch(payload: MLSharpTorchInstall):
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    variant = (payload.variant or "cpu").lower()
    if variant not in ("cpu", "cu121"):
        raise HTTPException(status_code=400, detail="Invalid torch variant")
    index_url = "https://download.pytorch.org/whl/cpu" if variant == "cpu" else "https://download.pytorch.org/whl/cu121"
    cmd = [
        python_path,
        "-m",
        "pip",
        "install",
        "--user",
        "--upgrade",
        "--force-reinstall",
        "--no-cache-dir",
        "torch",
        "torchvision",
        "--index-url",
        index_url,
    ]
    _run_cmd("ml_sharp", cmd, cwd=MLSHARP_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/ml_sharp/run")
def mlsharp_run(payload: MLSharpRun):
    input_path = Path(payload.input_path)
    if not input_path.exists():
        raise HTTPException(status_code=400, detail="Input path not found")
    sharp_cmd = _mlsharp_find_sharp()
    if not sharp_cmd:
        raise HTTPException(status_code=404, detail="sharp command not found")
    if payload.output_dir:
        output_dir = Path(payload.output_dir)
    else:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = MLSHARP_OUTPUT_DIR / f"splat_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    MODULE_STATE["ml_sharp_last_output"] = str(output_dir)
    cmd = [sharp_cmd, "predict", "-i", str(input_path), "-o", str(output_dir)]
    if payload.render:
        cmd.append("--render")
    if payload.device and payload.device != "default":
        cmd.extend(["--device", payload.device])

    def worker():
        checkpoint = _mlsharp_ensure_checkpoint()
        if checkpoint:
            cmd.extend(["--checkpoint-path", str(checkpoint)])
        _append_log("ml_sharp", f"$ {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(MLSHARP_BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            with MODULE_PROC_LOCK:
                MODULE_PROCS["ml_sharp"] = proc
            if proc.stdout:
                for line in proc.stdout:
                    _append_log("ml_sharp", line.rstrip())
            proc.wait()
            _append_log("ml_sharp", f"[done] exit={proc.returncode}")
        except Exception as exc:
            _append_log("ml_sharp", f"[error] {exc}")
        finally:
            with MODULE_PROC_LOCK:
                MODULE_PROCS.pop("ml_sharp", None)
        _mlsharp_setup_viewer(output_dir)

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "output_dir": str(output_dir)}


@app.post("/modules/ml_sharp/open_output")
def mlsharp_open(payload: MLSharpOpen):
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    gaussians_dir = target / "gaussians"
    os.startfile(str(gaussians_dir if gaussians_dir.exists() else target))
    return {"ok": True}


@app.post("/modules/ml_sharp/open_scene")
def mlsharp_open_scene(payload: MLSharpOpen):
    target = Path(payload.path) / "gaussians"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    os.startfile(str(target))
    return {"ok": True}


@app.post("/modules/ml_sharp/view_scene")
def mlsharp_view_scene(payload: MLSharpOpen):
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    url = _start_http_server(target, "ml_sharp", "gaussians/index.html")
    return {"url": url}


@app.post("/modules/ml_sharp/rename_scene")
def mlsharp_rename_scene(payload: MLSharpRename):
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid name")
    invalid_chars = '<>:"/\\\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "")
    name = name.strip().strip(".")
    if not name:
        raise HTTPException(status_code=400, detail="Invalid name")
    if target.resolve() == MLSHARP_OUTPUT_DIR.resolve():
        _mlsharp_write_scene_label(target, name)
        return {"ok": True, "path": str(target)}
    dest = target.parent / name
    if dest.exists():
        raise HTTPException(status_code=400, detail="Name already exists")
    target.rename(dest)
    try:
        label_path = dest / ".scene_name"
        if label_path.exists():
            label_path.unlink()
    except Exception:
        pass
    return {"ok": True, "path": str(dest)}


@app.get("/modules/ml_sharp/logs")
def mlsharp_logs(lines: int = 200):
    return {"lines": _tail_log("ml_sharp", lines)}

@app.post("/modules/ml_sharp/clear_logs")
def ml_sharp_clear_logs():
    _clear_log("ml_sharp")
    return {"ok": True}



@app.get("/modules/model_3d/state")
def model3d_state():
    config = _model3d_load_config()
    backend = config.get("backend", "hunyuan3d2")
    weights = _model3d_weights_options(backend)
    try:
        from huggingface_hub import HfFolder
        token_saved = bool(HfFolder.get_token())
    except Exception:
        token_saved = False
    return {
        "backend": backend,
        "weights": weights,
        "installed": _model3d_is_backend_installed(backend),
        "weights_installed": _model3d_is_weights_installed(backend),
        "running": _is_running("model3d"),
        "output_base": str(MODEL3D_OUTPUT_BASE),
        "last_output_dir": config.get("last_output_dir"),
        "hf_token_saved": token_saved,
    }


@app.get("/modules/model_3d/prereqs")
def model3d_prereqs():
    return _model3d_prereqs_status()


@app.post("/modules/model_3d/install_pybind11")
def model3d_install_pybind11():
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _append_log("model3d", "Instalando pybind11...")
    _run_cmd("model3d", [python_path, "-m", "pip", "install", "pybind11"])
    return {"ok": True}


@app.post("/modules/model_3d/open_build_tools")
def model3d_open_build_tools():
    webbrowser.open("https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    return {"ok": True}


@app.post("/modules/model_3d/open_cuda_toolkit")
def model3d_open_cuda_toolkit():
    webbrowser.open("https://developer.nvidia.com/cuda-12-1-0-download-archive")
    return {"ok": True}


@app.post("/modules/model_3d/open_cuda_needed")
def model3d_open_cuda_needed():
    torch_cuda = _model3d_torch_cuda_version()
    if torch_cuda.startswith("12.1"):
        webbrowser.open("https://developer.nvidia.com/cuda-12-1-0-download-archive")
    elif torch_cuda.startswith("12.4"):
        webbrowser.open("https://developer.nvidia.com/cuda-12-4-0-download-archive")
    elif torch_cuda.startswith("12.0"):
        webbrowser.open("https://developer.nvidia.com/cuda-12-0-0-download-archive")
    elif torch_cuda.startswith("11.8"):
        webbrowser.open("https://developer.nvidia.com/cuda-11-8-0-download-archive")
    else:
        webbrowser.open("https://developer.nvidia.com/cuda-downloads")
    return {"ok": True}


def _model3d_safe_rel_path(rel_path: str) -> Path:
    if not rel_path:
        raise HTTPException(status_code=400, detail="Path required")
    base = MODEL3D_OUTPUT_BASE.resolve()
    target = (base / rel_path).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return target


def _model3d_history_items() -> List[Dict]:
    if not MODEL3D_OUTPUT_BASE.exists():
        return []
    items: List[Dict] = []
    for path in MODEL3D_OUTPUT_BASE.rglob("*.glb"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(MODEL3D_OUTPUT_BASE)
        stat = path.stat()
        name = path.name if path.parent == MODEL3D_OUTPUT_BASE else path.parent.name
        items.append(
            {
                "name": name,
                "path": str(path),
                "rel_path": str(rel_path).replace("\\", "/"),
                "folder": str(path.parent),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
            }
        )
    items.sort(key=lambda item: item.get("modified", 0), reverse=True)
    return items


@app.get("/modules/model_3d/history")
def model3d_history(limit: int = 20):
    items = _model3d_history_items()
    if limit and limit > 0:
        items = items[:limit]
    return {"items": items}


@app.get("/modules/model_3d/preview")
def model3d_preview(path: str = Query(...)):
    target = _model3d_safe_rel_path(path)
    if target.suffix.lower() != ".glb":
        raise HTTPException(status_code=400, detail="Unsupported file")
    return FileResponse(str(target), media_type="model/gltf-binary", filename=target.name)


@app.post("/modules/model_3d/set_backend")
def model3d_set_backend(payload: Model3DSetBackend):
    config = _model3d_load_config()
    config["backend"] = payload.backend_key
    _model3d_save_config(config)
    return {"ok": True}


@app.post("/modules/model_3d/install_backend")
def model3d_install_backend(payload: Model3DSetBackend):
    repo_path = _model3d_repo_path(payload.backend_key)
    repo_url = _model3d_repo_url(payload.backend_key)
    if not repo_path or not repo_url:
        raise HTTPException(status_code=400, detail="Backend not supported")
    if repo_path.exists():
        return {"ok": True}
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd("model3d", ["git", "clone", "--depth", "1", repo_url, str(repo_path)], cwd=repo_path.parent)
    return {"ok": True}


@app.post("/modules/model_3d/uninstall_backend")
def model3d_uninstall_backend(payload: Model3DSetBackend):
    repo_path = _model3d_repo_path(payload.backend_key)
    if repo_path and repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/model_3d/install_weights")
def model3d_install_weights(payload: Model3DWeights):
    options = _model3d_weights_options(payload.backend_key)
    option = next((o for o in options if o["key"] == payload.weight_key), None)
    if not option:
        raise HTTPException(status_code=400, detail="Weights not supported")
    local_dir = Path(option["local_dir"])
    if local_dir.exists():
        return {"ok": True}
    local_dir.parent.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=option["repo_id"], local_dir=str(local_dir), local_dir_use_symlinks=False)
    return {"ok": True}


@app.post("/modules/model_3d/uninstall_weights")
def model3d_uninstall_weights(payload: Model3DWeights):
    options = _model3d_weights_options(payload.backend_key)
    option = next((o for o in options if o["key"] == payload.weight_key), None)
    if not option:
        raise HTTPException(status_code=400, detail="Weights not supported")
    local_dir = Path(option["local_dir"])
    if local_dir.exists():
        shutil.rmtree(local_dir, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/model_3d/reinstall_weights")
def model3d_reinstall_weights(payload: Model3DWeights):
    options = _model3d_weights_options(payload.backend_key)
    option = next((o for o in options if o["key"] == payload.weight_key), None)
    if not option:
        raise HTTPException(status_code=400, detail="Weights not supported")
    local_dir = Path(option["local_dir"])
    if local_dir.exists():
        shutil.rmtree(local_dir, ignore_errors=True)
    _model3d_clear_hf_cache(option["repo_id"])
    local_dir.parent.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=option["repo_id"],
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        force_download=True,
    )
    return {"ok": True}


@app.post("/modules/model_3d/run")
def model3d_run(payload: Model3DRun):
    backend = payload.backend_key
    input_paths = payload.input_paths
    if backend in ("stepx1", "hunyuan3d2", "sam3d") and not _model3d_is_backend_installed(backend):
        raise HTTPException(status_code=404, detail="Backend not installed")
    if backend == "reconv":
        webbrowser.open("https://huggingface.co/spaces/Stable-X/ReconViaGen")
        return {"ok": True}
    if not input_paths:
        raise HTTPException(status_code=400, detail="Input paths required")
    output_dir = payload.output_dir or str(MODEL3D_OUTPUT_BASE / f"model3d_{int(time.time())}")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    repo_path = _model3d_repo_path(backend)
    if backend == "hunyuan3d2":
        if not _model3d_torch_at_least("2.6"):
            raise HTTPException(
                status_code=400,
                detail=f"Torch >= 2.6 requerido. Detectado: {_model3d_torch_version() or 'N/A'}. Ejecuta 'Actualizar dependencias' para actualizar PyTorch.",
            )
        if not _model3d_has_custom_rasterizer():
            raise HTTPException(
                status_code=400,
                detail="Falta custom_rasterizer. Ejecuta 'Actualizar dependencias' para compilarlo.",
            )
        try:
            from huggingface_hub import is_offline_mode  # noqa: F401
        except Exception:
            _append_log("model3d", "Actualizando huggingface_hub...")
            rc = _run_cmd_blocking(
                "model3d",
                [python_path, "-m", "pip", "install", "--upgrade", "huggingface_hub", "--user"],
                cwd=repo_path,
            )
            if rc != 0:
                raise HTTPException(status_code=500, detail="No se pudo actualizar huggingface_hub.")
            try:
                from huggingface_hub import is_offline_mode  # noqa: F401
            except Exception:
                raise HTTPException(status_code=500, detail="huggingface_hub sigue desactualizado.")
    if backend == "stepx1":
        script_path = _model3d_write_stepx1_script(input_paths[0], output_dir, repo_path)
    elif backend == "hunyuan3d2":
        script_path = _model3d_write_hunyuan_script(input_paths[0], output_dir, repo_path)
    elif backend == "sam3d":
        if len(input_paths) < 2:
            raise HTTPException(status_code=400, detail="sam3d requires image and mask")
        script_path = _model3d_write_sam3d_script(input_paths[0], input_paths[1], output_dir, repo_path)
    else:
        raise HTTPException(status_code=400, detail="Backend not supported")
    env = os.environ.copy()
    env["XFORMERS_FORCE_DISABLE"] = "1"
    _run_cmd("model3d", [python_path, str(script_path)], cwd=repo_path, env=env)
    config = _model3d_load_config()
    config["last_output_dir"] = output_dir
    _model3d_save_config(config)
    return {"ok": True, "output_dir": output_dir}


@app.post("/modules/model_3d/update_deps")
def model3d_update_deps():
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    _append_log("model3d", "Actualizando dependencias de Model 3D...")
    _stop_proc("model3d")
    _run_cmd("model3d", [python_path, "-m", "pip", "install", "pybind11", "pygltflib"])
    torch_targets = [
        ("cu121", "https://download.pytorch.org/whl/cu121"),
        ("cu124", "https://download.pytorch.org/whl/cu124"),
    ]
    torch_installed = False
    for tag, index_url in torch_targets:
        _append_log("model3d", f"Actualizando PyTorch 2.6 ({tag})...")
        rc = _run_cmd_blocking(
            "model3d",
            [
                python_path,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--force-reinstall",
                "--no-cache-dir",
                "--no-deps",
                f"torch==2.6.0+{tag}",
                f"torchvision==0.21.0+{tag}",
                "--index-url",
                index_url,
            ],
        )
        if rc == 0:
            torch_installed = True
            break
    if not torch_installed:
        _append_log("model3d", "No se pudo instalar PyTorch 2.6 con CUDA.")
        _append_log("model3d", "Cierra otras apps Python y reintenta. Si persiste, ejecuta el bridge como admin.")
        return {"ok": True, "needs_manual": True, "reason": "torch", "prereqs": _model3d_prereqs_status()}
    _append_log("model3d", f"PyTorch actualizado: {_model3d_torch_version()}")
    _run_cmd(
        "model3d",
        [
            python_path,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "transformers",
            "huggingface_hub",
            "accelerate",
            "safetensors",
        ],
        cwd=BASE_DIR,
    )
    _run_cmd(
        "model3d",
        [python_path, "-m", "pip", "uninstall", "-y", "torchao"],
        cwd=BASE_DIR,
    )
    _run_cmd(
        "model3d",
        [python_path, "-m", "pip", "uninstall", "-y", "xformers"],
        cwd=BASE_DIR,
    )
    prereqs = _model3d_prereqs_status()
    if not prereqs.get("compiler_ok"):
        _append_log("model3d", "Falta el compilador C++. Instala Visual Studio Build Tools (Desktop development with C++).")
        _append_log("model3d", "https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        return {"ok": True, "needs_manual": True, "prereqs": prereqs, "reason": "compiler"}
    if prereqs.get("torch_cuda") and prereqs.get("nvcc_version") and not prereqs.get("cuda_match"):
        _append_log(
            "model3d",
            f"CUDA del sistema ({prereqs.get('nvcc_version')}) no coincide con PyTorch ({prereqs.get('torch_cuda')}).",
        )
        _append_log("model3d", "Instala CUDA 12.1 o usa un PyTorch compatible.")
        _append_log("model3d", "https://developer.nvidia.com/cuda-12-1-0-download-archive")
        return {"ok": True, "needs_manual": True, "prereqs": prereqs, "reason": "cuda"}
    hunyuan_dir = _model3d_repo_path("hunyuan3d2")
    if hunyuan_dir and hunyuan_dir.exists():
        custom_dir = hunyuan_dir / "hy3dgen" / "texgen" / "custom_rasterizer"
        if custom_dir.exists():
            _append_log("model3d", "Compilando custom_rasterizer...")
            _run_cmd("model3d", [python_path, "setup.py", "install"], cwd=custom_dir)
        renderer_dir = hunyuan_dir / "hy3dgen" / "texgen" / "differentiable_renderer"
        if renderer_dir.exists():
            _append_log("model3d", "Compilando differentiable_renderer...")
            _run_cmd("model3d", [python_path, "setup.py", "install"], cwd=renderer_dir)
    return {"ok": True, "needs_manual": False, "prereqs": _model3d_prereqs_status()}


@app.post("/modules/model_3d/restart")
def model3d_restart():
    _append_log("model3d", "Reiniciando proceso Model 3D...")
    _stop_proc("model3d")
    return {"ok": True}


@app.post("/modules/model_3d/stop")
def model3d_stop():
    _append_log("model3d", "Deteniendo proceso Model 3D...")
    _stop_proc("model3d")
    return {"ok": True}


@app.post("/modules/model_3d/open_output")
def model3d_open_output(payload: GaussianScene):
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/model_3d/logs")
def model3d_logs(lines: int = 200):
    return {"lines": _tail_log("model3d", lines)}

@app.post("/modules/model_3d/clear_logs")
def model_3d_clear_logs():
    _clear_log("model3d")
    return {"ok": True}



@app.post("/modules/model_3d/save_hf")
def model3d_save_hf(payload: Model3DHfToken):
    try:
        from huggingface_hub import HfFolder
        HfFolder.save_token(payload.token)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"ok": True}


@app.post("/modules/model_3d/delete_hf")
def model3d_delete_hf():
    try:
        from huggingface_hub import HfFolder
        HfFolder.delete_token()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"ok": True}


@app.get("/modules/neutts/state")
def neutts_state(repo_id: str = ""):
    espeak = _neutts_espeak_status()
    return {
        "installed": NEUTTS_BACKEND_DIR.exists(),
        "deps_ok": _neutts_deps_ok(repo_id) if repo_id else False,
        "output_dir": str(NEUTTS_OUTPUT_DIR),
        "last_output": MODULE_STATE.get("neutts_last_output"),
        "espeak_ok": espeak["ok"],
        "espeak_detail": espeak["detail"],
        "repo_id": repo_id,
        "running": _is_running("neutts"),
    }


@app.post("/modules/neutts/install")
def neutts_install():
    if NEUTTS_BACKEND_DIR.exists():
        return {"ok": True}
    NEUTTS_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd("neutts", ["git", "clone", "--depth", "1", "https://github.com/neuphonic/neutts", str(NEUTTS_BACKEND_DIR)], cwd=NEUTTS_BACKEND_DIR.parent)
    return {"ok": True}


@app.post("/modules/neutts/uninstall")
def neutts_uninstall():
    if NEUTTS_BACKEND_DIR.exists():
        shutil.rmtree(NEUTTS_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/neutts/deps")
def neutts_deps(payload: NeuttsDeps):
    if not NEUTTS_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    req_path = NEUTTS_BACKEND_DIR / "requirements.txt"
    if not req_path.exists():
        raise HTTPException(status_code=404, detail="requirements.txt not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    packages = ["-r", str(req_path), "soundfile"]
    if payload.repo_id.endswith("gguf"):
        packages.append("llama-cpp-python")
    _run_cmd("neutts", [python_path, "-m", "pip", "install", *packages], cwd=NEUTTS_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/neutts/generate")
def neutts_generate(payload: NeuttsGenerate):
    if not NEUTTS_BACKEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Backend not installed")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    if not payload.ref_audio.strip():
        raise HTTPException(status_code=400, detail="Reference audio is required")
    if not payload.ref_text.strip():
        raise HTTPException(status_code=400, detail="Reference text is required")
    script_path = NEUTTS_DATA_DIR / "neutts_run.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="neutts_run.py not found")
    NEUTTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = NEUTTS_OUTPUT_DIR / f"neutts_{int(time.time() * 1000)}.wav"
    MODULE_STATE["neutts_last_output"] = str(output_path)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-u",
        str(script_path),
        "--text",
        payload.text,
        "--ref-audio",
        payload.ref_audio,
        "--ref-text",
        payload.ref_text,
        "--backbone",
        payload.repo_id,
        "--codec",
        "neuphonic/neucodec",
        "--device",
        payload.device,
        "--output",
        str(output_path),
    ]
    _run_cmd("neutts", cmd, cwd=NEUTTS_BACKEND_DIR)
    return {"ok": True, "output": str(output_path)}


@app.post("/modules/neutts/open_output")
def neutts_open_output(payload: GaussianScene):
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    os.startfile(str(target))
    return {"ok": True}


@app.get("/modules/neutts/logs")
def neutts_logs(lines: int = 200):
    return {"lines": _tail_log("neutts", lines)}

@app.post("/modules/neutts/clear_logs")
def neutts_clear_logs():
    _clear_log("neutts")
    return {"ok": True}



@app.get("/modules/finetune_glm/state")
def finetune_glm_state():
    deps = {}
    for pkg in ("unsloth", "transformers", "trl", "datasets", "peft", "accelerate"):
        try:
            deps[pkg] = importlib.metadata.version(pkg)
        except Exception:
            deps[pkg] = ""
    return {
        "deps": deps,
        "deps_ok": all(deps.values()),
        "running": _is_running("finetune_glm"),
        "output_dir": str(FINETUNE_OUTPUT_DIR),
        "script_ok": FINETUNE_SCRIPT_PATH.exists(),
    }


@app.post("/modules/finetune_glm/deps")
def finetune_glm_deps():
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    packages = [
        "unsloth",
        "transformers==5.0.0rc3",
        "datasets",
        "trl",
        "peft",
        "accelerate",
    ]
    _run_cmd("finetune_glm", [python_path, "-m", "pip", "install", "--pre", *packages])
    return {"ok": True}


@app.post("/modules/finetune_glm/run")
def finetune_glm_run(payload: FinetuneRun):
    dataset_path = Path(payload.dataset_path)
    if not dataset_path.exists():
        raise HTTPException(status_code=400, detail="Dataset not found")
    if not FINETUNE_SCRIPT_PATH.exists():
        raise HTTPException(status_code=400, detail="Script not found")
    output_dir = Path(payload.output_dir) if payload.output_dir else FINETUNE_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-u",
        str(FINETUNE_SCRIPT_PATH),
        "--dataset",
        str(dataset_path),
        "--output-dir",
        str(output_dir),
        "--max-seq-len",
        str(payload.max_seq_len),
        "--epochs",
        str(payload.epochs),
        "--batch-size",
        str(payload.batch_size),
        "--grad-accum",
        str(payload.grad_accum),
        "--learning-rate",
        str(payload.learning_rate),
        "--lora-r",
        str(payload.lora_r),
        "--lora-alpha",
        str(payload.lora_alpha),
        "--lora-dropout",
        str(payload.lora_dropout),
    ]
    if payload.export_gguf:
        cmd += ["--export-gguf", "--gguf-quant", payload.gguf_quant]
    _run_cmd("finetune_glm", cmd, cwd=BASE_DIR)
    return {"ok": True}


@app.post("/modules/finetune_glm/open_output")
def finetune_glm_open_output():
    FINETUNE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    os.startfile(str(FINETUNE_OUTPUT_DIR))
    return {"ok": True}


@app.get("/modules/finetune_glm/logs")
def finetune_glm_logs(lines: int = 200):
    return {"lines": _tail_log("finetune_glm", lines)}

@app.post("/modules/finetune_glm/clear_logs")
def finetune_glm_clear_logs():
    _clear_log("finetune_glm")
    return {"ok": True}



@app.get("/modules/proedit/state")
def proedit_state():
    return {"output_dir": str(PROEDIT_OUTPUT_DIR)}


@app.post("/modules/proedit/open_output")
def proedit_open_output():
    PROEDIT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    os.startfile(str(PROEDIT_OUTPUT_DIR))
    return {"ok": True}


@app.get("/modules/research_assistant/state")
def research_state():
    settings = _get_settings()
    library = _research_load_library()
    index = _research_load_index()
    return {
        "library": library,
        "docs_dir": str(RESEARCH_DOCS_DIR),
        "index_ready": bool(index),
        "pdf_available": PyPDF2 is not None,
        "endpoint": settings.get("rag_endpoint", ""),
        "indexing": MODULE_STATE.get("research_indexing", False),
    }


@app.post("/modules/research_assistant/add")
def research_add(payload: ResearchAdd):
    if not PyPDF2:
        raise HTTPException(status_code=400, detail="PyPDF2 not available")
    src = Path(payload.path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    doc_id = str(uuid4())
    ext = src.suffix.lower() or ".pdf"
    dest_name = f"{doc_id}{ext}"
    dest_path = RESEARCH_DOCS_DIR / dest_name
    RESEARCH_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_path)
    library = _research_load_library()
    library.append(
        {
            "id": doc_id,
            "filename": dest_name,
            "original_name": src.name,
            "path": str(dest_path),
            "title": "",
            "authors": "",
            "year": "",
            "venue": "",
            "url": "",
            "summary": "",
        }
    )
    _research_save_library(library)
    return {"library": library}


@app.post("/modules/research_assistant/remove")
def research_remove(payload: ResearchRemove):
    library = _research_load_library()
    doc = _research_get_doc(library, payload.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        path = Path(doc.get("path", ""))
        if path.exists():
            path.unlink()
    except Exception:
        pass
    library = [d for d in library if d.get("id") != payload.doc_id]
    _research_save_library(library)
    index = [chunk for chunk in _research_load_index() if chunk.get("doc_id") != payload.doc_id]
    _research_save_index(index)
    return {"library": library}


@app.post("/modules/research_assistant/save_meta")
def research_save_meta(payload: ResearchMeta):
    library = _research_load_library()
    doc = _research_get_doc(library, payload.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc["title"] = payload.title.strip()
    doc["authors"] = payload.authors.strip()
    doc["year"] = payload.year.strip()
    doc["venue"] = payload.venue.strip()
    doc["url"] = payload.url.strip()
    _research_save_library(library)
    return {"doc": doc}


@app.post("/modules/research_assistant/summary")
def research_summary(payload: ResearchDoc):
    if not PyPDF2:
        raise HTTPException(status_code=400, detail="PyPDF2 not available")
    library = _research_load_library()
    doc = _research_get_doc(library, payload.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    text = _research_extract_pdf_text(path)
    if not text:
        raise HTTPException(status_code=400, detail="No text extracted")
    summary = _research_extractive_summary(text, max_sentences=5)
    doc["summary"] = summary
    _research_save_library(library)
    return {"summary": summary}


@app.post("/modules/research_assistant/citations")
def research_citations(payload: ResearchDoc):
    library = _research_load_library()
    doc = _research_get_doc(library, payload.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "apa": _research_format_citation(doc, "apa"),
        "ieee": _research_format_citation(doc, "ieee"),
    }


@app.post("/modules/research_assistant/build_index")
def research_build_index():
    if not PyPDF2:
        raise HTTPException(status_code=400, detail="PyPDF2 not available")
    if MODULE_STATE.get("research_indexing"):
        return {"ok": True}

    def worker():
        MODULE_STATE["research_indexing"] = True
        _append_log("research_assistant", "[index] start")
        library = _research_load_library()
        chunks = []
        try:
            for doc in library:
                path = Path(doc.get("path", ""))
                if not path.exists():
                    continue
                text = _research_extract_pdf_text(path)
                if not text:
                    continue
                for idx, chunk in enumerate(_research_chunk_text(text)):
                    tf = _research_term_freq(_research_tokenize(chunk))
                    chunks.append({"doc_id": doc.get("id"), "chunk_id": idx, "text": chunk, "tf": tf})
            _research_save_index(chunks)
            _append_log("research_assistant", "[index] done")
        except Exception as exc:
            _append_log("research_assistant", f"[index] error {exc}")
        finally:
            MODULE_STATE["research_indexing"] = False

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True}


@app.post("/modules/research_assistant/ask")
def research_ask(payload: ResearchAsk):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question required")
    index = _research_load_index()
    if not index:
        return {"answer": "", "sources": "", "hits": [], "status": "no_index"}
    hits = _research_search(index, question, top_k=4)
    if not hits:
        return {"answer": "", "sources": "", "hits": [], "status": "no_results"}
    library = _research_load_library()
    context_text = "\n\n".join([hit.get("text", "") for hit in hits])
    sources_text = _research_format_sources(hits, library)
    endpoint = (payload.endpoint or "").strip() or _get_settings().get("rag_endpoint", "")
    answer = _research_answer_with_llm(endpoint, question, context_text)
    if not answer:
        answer = context_text
    _append_log("research_assistant", f"[ask] {question}")
    return {"answer": answer, "sources": sources_text, "hits": hits, "status": "ok"}


@app.get("/modules/research_assistant/logs")
def research_logs(lines: int = 200):
    return {"lines": _tail_log("research_assistant", lines)}

@app.post("/modules/research_assistant/clear_logs")
def research_assistant_clear_logs():
    _clear_log("research_assistant")
    return {"ok": True}



@app.get("/modules/spotedit/state")
def spotedit_state():
    deps_marker = SPOTEDIT_BACKEND_DIR / ".deps_installed"
    return {
        "installed": SPOTEDIT_BACKEND_DIR.exists(),
        "deps_installed": deps_marker.exists(),
        "running": _is_running("spotedit"),
        "output_dir": str(SPOTEDIT_OUTPUT_DIR),
        "backend_dir": str(SPOTEDIT_BACKEND_DIR),
    }


@app.post("/modules/spotedit/install")
def spotedit_install():
    if SPOTEDIT_BACKEND_DIR.exists():
        return {"ok": True}
    if not which("git"):
        raise HTTPException(status_code=400, detail="Git not available")
    SPOTEDIT_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", "https://github.com/Biangbiang0321/SpotEdit", str(SPOTEDIT_BACKEND_DIR)]
    _run_cmd("spotedit", cmd, cwd=SPOTEDIT_BACKEND_DIR.parent)
    return {"ok": True}


@app.post("/modules/spotedit/uninstall")
def spotedit_uninstall():
    if SPOTEDIT_BACKEND_DIR.exists():
        shutil.rmtree(SPOTEDIT_BACKEND_DIR, ignore_errors=True)
    return {"ok": True}


@app.post("/modules/spotedit/deps")
def spotedit_deps():
    if not SPOTEDIT_BACKEND_DIR.exists():
        raise HTTPException(status_code=400, detail="Backend not installed")
    req_path = SPOTEDIT_BACKEND_DIR / "requirements.txt"
    if not req_path.exists():
        raise HTTPException(status_code=400, detail="requirements.txt not found")
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    marker = SPOTEDIT_BACKEND_DIR / ".deps_installed"
    _run_cmd_with_marker(
        "spotedit",
        [python_path, "-m", "pip", "install", "-r", str(req_path)],
        cwd=SPOTEDIT_BACKEND_DIR,
        marker=marker,
    )
    return {"ok": True}


@app.post("/modules/spotedit/download")
def spotedit_download(payload: SpotEditModel):
    if not SPOTEDIT_BACKEND_DIR.exists():
        raise HTTPException(status_code=400, detail="Backend not installed")
    script_path = SPOTEDIT_DATA_DIR / "spotedit_run.py"
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-u",
        str(script_path),
        "--backend",
        payload.backend,
        "--input",
        str(script_path),
        "--mask",
        str(script_path),
        "--output",
        str(script_path),
        "--prompt",
        "download",
        "--download-only",
    ]
    _run_cmd("spotedit", cmd, cwd=SPOTEDIT_BACKEND_DIR)
    return {"ok": True}


@app.post("/modules/spotedit/run")
def spotedit_run(payload: SpotEditRun):
    if not SPOTEDIT_BACKEND_DIR.exists():
        raise HTTPException(status_code=400, detail="Backend not installed")
    input_path = Path(payload.input_path)
    mask_path = Path(payload.mask_path)
    if not input_path.exists() or not mask_path.exists():
        raise HTTPException(status_code=400, detail="Input or mask not found")
    output_dir = Path(payload.output_dir) if payload.output_dir else SPOTEDIT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"spotedit_{int(time.time() * 1000)}.png"
    MODULE_STATE["spotedit_last_output"] = str(output_path)
    script_path = SPOTEDIT_DATA_DIR / "spotedit_run.py"
    python_path = sys.executable.replace("pythonw.exe", "python.exe")
    cmd = [
        python_path,
        "-u",
        str(script_path),
        "--backend",
        payload.backend,
        "--input",
        str(input_path),
        "--mask",
        str(mask_path),
        "--output",
        str(output_path),
        "--prompt",
        payload.prompt or "Describe the edit.",
    ]
    _run_cmd("spotedit", cmd, cwd=SPOTEDIT_BACKEND_DIR)
    return {"ok": True, "output": str(output_path)}


@app.post("/modules/spotedit/open_output")
def spotedit_open_output():
    SPOTEDIT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    os.startfile(str(SPOTEDIT_OUTPUT_DIR))
    return {"ok": True}


@app.post("/modules/spotedit/open_backend")
def spotedit_open_backend():
    if SPOTEDIT_BACKEND_DIR.exists():
        os.startfile(str(SPOTEDIT_BACKEND_DIR))
    return {"ok": True}


@app.get("/modules/spotedit/logs")
def spotedit_logs(lines: int = 200):
    return {"lines": _tail_log("spotedit", lines)}

@app.post("/modules/spotedit/clear_logs")
def spotedit_clear_logs():
    _clear_log("spotedit")
    return {"ok": True}



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8787, log_level="info")
