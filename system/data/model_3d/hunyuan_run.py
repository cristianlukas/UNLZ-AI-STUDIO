import os
import sys
import time
sys.path.insert(0, r"D:\Descargas\_Facultad\PPS\Repositorio\UNLZ-AI-STUDIO\system\3d-backends\Hunyuan3D-2")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HUNYUAN_NO_TEXTURE"] = "1"
print("[Hunyuan] Starting pipeline", flush=True)
print("[Hunyuan] Mode: geometry only", flush=True)
import torch
from PIL import Image
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen import Hunyuan3DPaintPipeline
input_image_path = r"D:/Fotos/UwU/ULTRA ESPADON DEL HUMO.png"
out_dir = r"D:\Descargas\_Facultad\PPS\Repositorio\UNLZ-AI-STUDIO\system\3d-out\model3d_2026-03-11_02-11-23"
os.makedirs(out_dir, exist_ok=True)
mesh_path = os.path.join(out_dir, "mesh.glb")
with Image.open(input_image_path) as img:
    input_image = img.convert("RGBA")
weights_dir = r"D:\Descargas\_Facultad\PPS\Repositorio\UNLZ-AI-STUDIO\system\3d-weights\Hunyuan3D-2"
base = "tencent/Hunyuan3D-2"
base_is_local = False
if weights_dir and os.path.exists(weights_dir):
    os.environ["HY3DGEN_MODELS"] = weights_dir
    local_candidates = [
        os.path.join(weights_dir, "hunyuan3d-dit-v2-0"),
        os.path.join(weights_dir, "hunyuan3d-dit-v2-0-fast"),
        os.path.join(weights_dir, "hunyuan3d-dit-v2-0-turbo"),
        os.path.join(weights_dir, "tencent", "Hunyuan3D-2", "hunyuan3d-dit-v2-0"),
        os.path.join(weights_dir, "tencent", "Hunyuan3D-2", "hunyuan3d-dit-v2-0-fast"),
        os.path.join(weights_dir, "tencent", "Hunyuan3D-2", "hunyuan3d-dit-v2-0-turbo"),
    ]
    if any(os.path.exists(path) for path in local_candidates):
        base = weights_dir
        base_is_local = True
        os.environ["HF_HUB_OFFLINE"] = "1"
shape_subfolder = os.environ.get("HUNYUAN_SHAPE_SUBFOLDER", "").strip()
if not shape_subfolder:
    for candidate in ("hunyuan3d-dit-v2-0-turbo", "hunyuan3d-dit-v2-0-fast", "hunyuan3d-dit-v2-0"):
        if not base_is_local or os.path.exists(os.path.join(base, candidate)):
            shape_subfolder = candidate
            break
if not shape_subfolder:
    shape_subfolder = "hunyuan3d-dit-v2-0"
default_steps = 30
if "turbo" in shape_subfolder:
    default_steps = 5
elif "fast" in shape_subfolder:
    default_steps = 20
num_steps = int(os.environ.get("HUNYUAN_STEPS", str(default_steps)))
print(f"[Hunyuan] Loading shape model: base={base} subfolder={shape_subfolder} steps={num_steps}", flush=True)
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(base, subfolder=shape_subfolder)
if hasattr(pipeline, "enable_flashvdm") and "turbo" in shape_subfolder:
    try:
        pipeline.enable_flashvdm(mc_algo="mc")
        print("[Hunyuan] FlashVDM enabled", flush=True)
    except Exception as exc:
        print(f"[Hunyuan] FlashVDM unavailable: {exc}", flush=True)
print("[Hunyuan] Generating geometry...", flush=True)
t0 = time.time()
mesh = pipeline(image=input_image, num_inference_steps=num_steps, guidance_scale=5.0)[0]
print(f"[Hunyuan] Geometry done in {time.time() - t0:.1f}s", flush=True)
mesh.export(mesh_path)
print(f"[Hunyuan] Saved geometry: {mesh_path}", flush=True)
vram_gb = None
if torch.cuda.is_available():
    try:
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except Exception:
        vram_gb = None
force_texture = os.environ.get("HUNYUAN_FORCE_TEXTURE", "0") == "1"
disable_texture = os.environ.get("HUNYUAN_NO_TEXTURE", "0") == "1"
enable_texture = force_texture or (not disable_texture and (vram_gb is None or vram_gb >= 12.0))
if not enable_texture:
    print(f"[Hunyuan] Skipping texture stage (VRAM={vram_gb} GB). Set HUNYUAN_FORCE_TEXTURE=1 to force.", flush=True)
else:
    print("[Hunyuan] Loading texture model...", flush=True)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    paint = Hunyuan3DPaintPipeline.from_pretrained(base, subfolder="hunyuan3d-paint-v2-0-turbo")
    if hasattr(paint, "enable_model_cpu_offload"):
        try:
            paint.enable_model_cpu_offload()
        except Exception:
            pass
    print("[Hunyuan] Generating texture...", flush=True)
    t1 = time.time()
    mesh = paint(mesh, image=input_image)
    tex_path = os.path.join(out_dir, "mesh_textured.glb")
    mesh.export(tex_path)
    print(f"[Hunyuan] Texture done in {time.time() - t1:.1f}s", flush=True)
    print(f"[Hunyuan] Saved textured mesh: {tex_path}", flush=True)
