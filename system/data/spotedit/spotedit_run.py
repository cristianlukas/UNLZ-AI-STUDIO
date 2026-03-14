import argparse
import gc
import os
import sys
from pathlib import Path


def load_hf_token():
    try:
        from huggingface_hub import HfFolder

        return HfFolder.get_token()
    except Exception:
        return None


def prepare_paths():
    app_root = Path(__file__).resolve().parents[3]
    backend_dir = app_root / "system" / "ai-backends" / "SpotEdit"
    return app_root, backend_dir


def ensure_model_download(model_id, token):
    try:
        from huggingface_hub import HfApi, hf_hub_download

        print(f"Checking model cache: {model_id}", flush=True)
        api = HfApi()
        files = api.list_repo_files(model_id, token=token)
        total = len(files)
        for idx, filename in enumerate(files, start=1):
            print(f"Downloading {idx}/{total}: {filename}", flush=True)
            hf_hub_download(repo_id=model_id, filename=filename, token=token)
        print("Model files ready.", flush=True)
    except Exception as exc:
        print(f"Model download error: {exc}", flush=True)
        raise


def build_pipeline(backend, token):
    import torch

    def is_paging_file_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return (
            "os error 1455" in text
            or "archivo de paginacion" in text
            or "archivo de paginacion" in text
            or "archivo de paginacion" in text
            or "archivo de paginacion" in text
            or "paging file" in text
        )

    def is_unsupported_device_map_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "not supported" in text and "device_map" in text

    force_cpu_env = os.environ.get("SPOTEDIT_FORCE_CPU", "0").strip().lower() in ("1", "true", "yes", "on")
    auto_force_cpu = False
    if backend == "qwen" and torch.cuda.is_available():
        try:
            total_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            if total_gb <= 6.5:
                auto_force_cpu = True
                print(f"Auto-enabling CPU mode for Qwen on low VRAM GPU ({total_gb:.1f} GB).", flush=True)
        except Exception:
            pass

    force_cpu = force_cpu_env or auto_force_cpu
    device = "cpu" if force_cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float32

    if device == "cuda":
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        allow_bf16 = os.environ.get("SPOTEDIT_ALLOW_BF16", "0").strip().lower() in ("1", "true", "yes", "on")
        if allow_bf16:
            try:
                major, _minor = torch.cuda.get_device_capability()
                dtype = torch.bfloat16 if major >= 8 else torch.float16
            except Exception:
                dtype = torch.float16
        else:
            dtype = torch.float16

    print(f"Device: {device}, dtype: {dtype}", flush=True)

    def load_pipeline_with_fallback(pipeline_cls, model_id, requested_dtype):
        offload_dir = Path(__file__).resolve().parent / "offload_cache"
        offload_dir.mkdir(parents=True, exist_ok=True)

        if force_cpu:
            attempts = [
                (
                    "cpu_map_float32",
                    {
                        "torch_dtype": torch.float32,
                        "token": token,
                        "low_cpu_mem_usage": True,
                        "device_map": "cpu",
                        "offload_folder": str(offload_dir),
                        "offload_state_dict": True,
                    },
                )
            ]
        else:
            attempts = [
                (
                    "balanced_offload",
                    {
                        "torch_dtype": requested_dtype,
                        "token": token,
                        "low_cpu_mem_usage": True,
                        "device_map": "balanced",
                        "offload_folder": str(offload_dir),
                        "offload_state_dict": True,
                    },
                ),
                (
                    "cpu_map_float32",
                    {
                        "torch_dtype": torch.float32,
                        "token": token,
                        "low_cpu_mem_usage": True,
                        "device_map": "cpu",
                        "offload_folder": str(offload_dir),
                        "offload_state_dict": True,
                    },
                ),
            ]

        last_exc = None
        for name, kwargs in attempts:
            try:
                print(f"Loading pipeline attempt: {name}", flush=True)
                return pipeline_cls.from_pretrained(model_id, **kwargs)
            except Exception as exc:
                last_exc = exc
                if is_paging_file_error(exc) or is_unsupported_device_map_error(exc):
                    print(f"Low-memory load failure on {name}: {exc}", flush=True)
                    continue
                raise

        if last_exc:
            print(
                "All low-memory load attempts failed. Windows virtual memory may be too small; "
                "increase pagefile size and retry.",
                flush=True,
            )
            raise last_exc

    def finalize_pipeline(pipe, pipeline_cls, model_id):
        if device != "cuda":
            return pipe.to("cpu")

        if getattr(pipe, "hf_device_map", None):
            print("Pipeline loaded with device_map/offload; skipping explicit .to(cuda).", flush=True)
            return pipe

        try:
            gc.collect()
            torch.cuda.empty_cache()
        except Exception:
            pass

        if hasattr(pipe, "enable_model_cpu_offload"):
            try:
                pipe.enable_model_cpu_offload()
                print("Enabled model CPU offload for reduced VRAM usage.", flush=True)
                return pipe
            except Exception as exc:
                print(f"CPU offload unavailable, trying full CUDA load: {exc}", flush=True)

        try:
            return pipe.to("cuda")
        except torch.OutOfMemoryError as exc:
            print(f"CUDA OOM during pipeline load: {exc}", flush=True)
            print("Falling back to CPU pipeline reload.", flush=True)
            try:
                del pipe
                gc.collect()
                torch.cuda.empty_cache()
            except Exception:
                pass
            cpu_pipe = load_pipeline_with_fallback(pipeline_cls, model_id, torch.float32)
            return cpu_pipe.to("cpu")

    if backend == "flux":
        from diffusers import FluxKontextPipeline
        from FLUX_kontext import SpotEditConfig, generate

        model_id = "black-forest-labs/FLUX.1-Kontext-dev"
        print(f"Loading model: {model_id}", flush=True)
        ensure_model_download(model_id, token)
        pipe = load_pipeline_with_fallback(FluxKontextPipeline, model_id, dtype)
        pipe = finalize_pipeline(pipe, FluxKontextPipeline, model_id)
        config = SpotEditConfig(threshold=0.2)
        return pipe, generate, config

    from diffusers import QwenImageEditPipeline
    from Qwen_image_edit import SpotEditConfig, generate

    model_id = "Qwen/Qwen-Image-Edit"
    print(f"Loading model: {model_id}", flush=True)
    ensure_model_download(model_id, token)
    pipe = load_pipeline_with_fallback(QwenImageEditPipeline, model_id, dtype)
    pipe = finalize_pipeline(pipe, QwenImageEditPipeline, model_id)
    config = SpotEditConfig(threshold=0.15)
    return pipe, generate, config


def blend_mask(original, edited, mask):
    import numpy as np
    from PIL import Image

    mask = mask.convert("L")
    mask_np = np.array(mask).astype("float32") / 255.0
    if mask_np.ndim == 2:
        mask_np = mask_np[:, :, None]

    orig_np = np.array(original).astype("float32")
    edit_np = np.array(edited).astype("float32")
    out = edit_np * mask_np + orig_np * (1.0 - mask_np)
    out = out.clip(0, 255).astype("uint8")
    return Image.fromarray(out)


def is_erase_prompt(prompt):
    prompt_l = (prompt or "").strip().lower()
    erase_keywords = (
        "erase",
        "remove",
        "delete",
        "clean",
        "borrar",
        "borra",
        "eliminar",
        "elimina",
        "quitar",
        "quita",
        "limpiar",
        "limpia",
    )
    return any(word in prompt_l for word in erase_keywords)


def lightweight_inpaint(image, mask, prompt=""):
    import numpy as np
    from PIL import Image

    mask_l = mask.convert("L")
    mask_np = np.array(mask_l).astype("uint8")
    image_np = np.array(image.convert("RGB")).astype("uint8")

    prompt_l = (prompt or "").strip().lower()

    wants_erase = is_erase_prompt(prompt)
    if wants_erase:
        try:
            import cv2

            mask_bin = (mask_np > 127).astype("uint8") * 255
            area_ratio = float((mask_bin > 0).mean())
            if area_ratio <= 0.0001:
                return image

            ys, xs = np.where(mask_bin > 0)
            y1, y2 = int(ys.min()), int(ys.max()) + 1
            x1, x2 = int(xs.min()), int(xs.max()) + 1

            base_k = int(round(max(image_np.shape[0], image_np.shape[1]) * 0.004))
            if area_ratio > 0.08:
                base_k = max(base_k, 7)
            if area_ratio > 0.18:
                base_k = max(base_k, 11)
            base_k = max(3, min(base_k, 15))
            if base_k % 2 == 0:
                base_k += 1

            pad = max(32, base_k * 6)
            h, w = image_np.shape[:2]
            ry1 = max(0, y1 - pad)
            ry2 = min(h, y2 + pad)
            rx1 = max(0, x1 - pad)
            rx2 = min(w, x2 + pad)

            roi_image = image_np[ry1:ry2, rx1:rx2]
            roi_mask = mask_bin[ry1:ry2, rx1:rx2]

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (base_k, base_k))
            # Smooth and expand the mask so inpaint pulls cleaner context near edges.
            expanded_mask = cv2.morphologyEx(roi_mask, cv2.MORPH_CLOSE, kernel)
            expanded_mask = cv2.dilate(expanded_mask, kernel, iterations=1)
            expanded_mask = cv2.GaussianBlur(
                expanded_mask,
                (0, 0),
                sigmaX=max(1.2, base_k / 3.0),
                sigmaY=max(1.2, base_k / 3.0),
            )
            expanded_mask = (expanded_mask > 12).astype("uint8") * 255

            bgr = cv2.cvtColor(roi_image, cv2.COLOR_RGB2BGR)
            inpaint_radius = 5
            if area_ratio > 0.05:
                inpaint_radius = 7
            if area_ratio > 0.15:
                inpaint_radius = 9

            inpaint_telea = cv2.inpaint(bgr, expanded_mask, inpaint_radius, cv2.INPAINT_TELEA)
            inpaint_ns = cv2.inpaint(bgr, expanded_mask, max(3, inpaint_radius - 1), cv2.INPAINT_NS)
            telea_weight = 0.7 if area_ratio < 0.04 else 0.45
            mixed_inpaint = cv2.addWeighted(inpaint_telea, telea_weight, inpaint_ns, 1.0 - telea_weight, 0.0)

            roi_h, roi_w = expanded_mask.shape[:2]
            scale = 0.5 if max(roi_h, roi_w) > 600 else 1.0
            if scale < 1.0:
                small_w = max(32, int(round(roi_w * scale)))
                small_h = max(32, int(round(roi_h * scale)))
                bgr_small = cv2.resize(bgr, (small_w, small_h), interpolation=cv2.INTER_AREA)
                mask_small = cv2.resize(expanded_mask, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
                small_radius = max(3, int(round(inpaint_radius * scale * 1.8)))
                low_telea = cv2.inpaint(bgr_small, mask_small, small_radius, cv2.INPAINT_TELEA)
                low_ns = cv2.inpaint(bgr_small, mask_small, small_radius, cv2.INPAINT_NS)
                low_mix = cv2.addWeighted(low_telea, 0.5, low_ns, 0.5, 0.0)
                low_mix = cv2.resize(low_mix, (roi_w, roi_h), interpolation=cv2.INTER_CUBIC)
                mixed_inpaint = cv2.addWeighted(mixed_inpaint, 0.72, low_mix, 0.28, 0.0)

            mixed_inpaint = cv2.bilateralFilter(mixed_inpaint, d=7, sigmaColor=45, sigmaSpace=45)

            rgb_inpainted = cv2.cvtColor(mixed_inpaint, cv2.COLOR_BGR2RGB).astype("float32")
            rgb_original = roi_image.astype("float32")

            soft_alpha = cv2.GaussianBlur(
                expanded_mask,
                (0, 0),
                sigmaX=max(1.8, base_k / 2.0),
                sigmaY=max(1.8, base_k / 2.0),
            ).astype("float32") / 255.0
            core_alpha = (roi_mask.astype("float32") / 255.0)
            soft_alpha = np.maximum(soft_alpha, core_alpha)
            soft_alpha = soft_alpha[:, :, None]
            out = rgb_inpainted * soft_alpha + rgb_original * (1.0 - soft_alpha)

            final = image_np.copy().astype("float32")
            final[ry1:ry2, rx1:rx2] = out
            return Image.fromarray(final.clip(0, 255).astype("uint8"))
        except Exception:
            rgb = image_np.copy()
            keep = mask_np == 0
            if keep.any():
                mean_color = rgb[keep].mean(axis=0)
            else:
                mean_color = np.array([127, 127, 127], dtype="float32")
            rgb[mask_np > 0] = mean_color.astype("uint8")
            return Image.fromarray(rgb)

    color_map = {
        "red": (220, 40, 40),
        "green": (30, 180, 70),
        "blue": (45, 105, 220),
        "yellow": (230, 205, 35),
        "orange": (230, 120, 35),
        "purple": (145, 70, 190),
        "pink": (230, 110, 170),
        "black": (20, 20, 20),
        "white": (235, 235, 235),
        "gray": (140, 140, 140),
        "grey": (140, 140, 140),
        # Spanish aliases
        "rojo": (220, 40, 40),
        "verde": (30, 180, 70),
        "azul": (45, 105, 220),
        "amarillo": (230, 205, 35),
        "naranja": (230, 120, 35),
        "morado": (145, 70, 190),
        "violeta": (145, 70, 190),
        "rosa": (230, 110, 170),
        "negro": (20, 20, 20),
        "blanco": (235, 235, 235),
        "gris": (140, 140, 140),
    }

    target_color = None
    for key, rgb in color_map.items():
        if key in prompt_l:
            target_color = rgb
            break

    if target_color is not None:
        out = image_np.copy().astype("float32")
        alpha = (mask_np.astype("float32") / 255.0)[:, :, None]
        color_np = np.array(target_color, dtype="float32")[None, None, :]
        # Strong blend so changes are visually obvious for color prompts.
        strength = 0.9
        out = out * (1.0 - alpha * strength) + color_np * (alpha * strength)
        return Image.fromarray(out.clip(0, 255).astype("uint8"))

    try:
        import cv2

        bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        # 3px radius gives a fast, stable fill for masked regions.
        inpainted = cv2.inpaint(bgr, mask_np, 3, cv2.INPAINT_TELEA)
        rgb = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    except Exception:
        # Fallback if OpenCV is unavailable: fill masked area with mean color.
        rgb = image_np.copy()
        keep = mask_np == 0
        if keep.any():
            mean_color = rgb[keep].mean(axis=0)
        else:
            mean_color = np.array([127, 127, 127], dtype="float32")
        rgb[mask_np > 0] = mean_color.astype("uint8")
        return Image.fromarray(rgb)


def should_use_lightweight_fallback(backend):
    force_light = os.environ.get("SPOTEDIT_LIGHTWEIGHT_ONLY", "0").strip().lower() in ("1", "true", "yes", "on")
    if force_light:
        return True, "forced by SPOTEDIT_LIGHTWEIGHT_ONLY"

    # Qwen model is very memory-intensive. If Windows virtual memory is low,
    # trying to load shards can crash the process before Python catches errors.
    if backend != "qwen":
        return False, ""

    try:
        import torch

        if torch.cuda.is_available():
            total_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            if total_gb <= 6.5:
                return True, f"qwen on low VRAM GPU ({total_gb:.1f} GB)"
    except Exception:
        pass

    try:
        import psutil

        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        total_virtual_gb = (vm.total + sm.total) / (1024 ** 3)
        available_virtual_gb = (vm.available + sm.free) / (1024 ** 3)
        if total_virtual_gb < 28.0 or available_virtual_gb < 8.0:
            reason = (
                f"low virtual memory (total={total_virtual_gb:.1f} GB, "
                f"available={available_virtual_gb:.1f} GB)"
            )
            return True, reason
    except Exception:
        pass

    return False, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["flux", "qwen"], default="qwen")
    parser.add_argument("--input", required=True)
    parser.add_argument("--mask", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--guidance", type=float, default=3.5)
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()

    app_root, backend_dir = prepare_paths()
    sys.path.insert(0, str(backend_dir))

    token = load_hf_token()
    if token:
        os.environ["HF_TOKEN"] = token
        os.environ["HUGGINGFACE_HUB_TOKEN"] = token
    else:
        print("Warning: HF token not found. If the model is gated, download will fail.", flush=True)

    from PIL import Image

    if args.download_only:
        model_id = "black-forest-labs/FLUX.1-Kontext-dev" if args.backend == "flux" else "Qwen/Qwen-Image-Edit"
        print(f"Downloading model only: {model_id}", flush=True)
        ensure_model_download(model_id, token)
        print("Download completed.", flush=True)
        return

    input_image = Image.open(args.input).convert("RGB")
    mask_image = Image.open(args.mask).convert("L")

    target_size = (1024, 1024)
    try:
        import torch

        if torch.cuda.is_available():
            total_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            if total_gb <= 6.5:
                target_size = (768, 768)
            elif total_gb <= 8.5:
                target_size = (896, 896)
            print(f"Adjusted working size for VRAM ({total_gb:.1f} GB): {target_size}", flush=True)
    except Exception:
        pass

    if is_erase_prompt(args.prompt):
        # Keep original resolution for lightweight erase to preserve edges/details.
        target_size = input_image.size

    resized = input_image.resize(target_size, Image.LANCZOS) if input_image.size != target_size else input_image
    mask_resized = mask_image.resize(resized.size, Image.NEAREST)

    use_lightweight, lightweight_reason = should_use_lightweight_fallback(args.backend)
    if use_lightweight:
        print(f"Using lightweight fallback inpainting: {lightweight_reason}", flush=True)
        print("Note: lightweight mode approximates prompt edits and is not full generative SpotEdit.", flush=True)
        edited = lightweight_inpaint(resized, mask_resized, args.prompt)
        if is_erase_prompt(args.prompt):
            # Erase already applies its own soft blending to avoid hard mask seams.
            blended = edited
        else:
            blended = blend_mask(resized, edited, mask_resized)
        if blended.size != input_image.size:
            blended = blended.resize(input_image.size, Image.LANCZOS)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        blended.save(output_path)
        print(f"Saved output to {output_path}", flush=True)
        return

    print("Building pipeline (first run may download weights)...", flush=True)
    pipe, generate, config = build_pipeline(args.backend, token)
    print("Running SpotEdit...", flush=True)

    def run_once(active_pipe, image):
        return generate(
            active_pipe,
            image=image,
            prompt=args.prompt,
            config=config,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
        )

    try:
        result = run_once(pipe, resized)
    except Exception as exc:
        is_cuda_oom = "out of memory" in str(exc).lower() and "cuda" in str(exc).lower()
        if not is_cuda_oom:
            raise

        print(f"CUDA OOM during generation: {exc}", flush=True)

        if resized.size[0] > 640:
            retry_size = (640, 640)
            print(f"Retrying generation at lower resolution: {retry_size}", flush=True)
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            gc.collect()
            resized = input_image.resize(retry_size, Image.LANCZOS)
            mask_resized = mask_image.resize(resized.size, Image.NEAREST)

            try:
                result = run_once(pipe, resized)
            except Exception as retry_exc:
                retry_is_oom = "out of memory" in str(retry_exc).lower() and "cuda" in str(retry_exc).lower()
                if not retry_is_oom:
                    raise
                print(f"Retry still OOM: {retry_exc}", flush=True)
                print("Switching to CPU pipeline fallback.", flush=True)
                os.environ["SPOTEDIT_FORCE_CPU"] = "1"
                gc.collect()
                pipe, generate, config = build_pipeline(args.backend, token)
                result = run_once(pipe, resized)
        else:
            print("Switching to CPU pipeline fallback.", flush=True)
            os.environ["SPOTEDIT_FORCE_CPU"] = "1"
            gc.collect()
            pipe, generate, config = build_pipeline(args.backend, token)
            result = run_once(pipe, resized)

    edited = result.images[0] if hasattr(result, "images") else result[0]
    blended = blend_mask(resized, edited, mask_resized)
    if blended.size != input_image.size:
        blended = blended.resize(input_image.size, Image.LANCZOS)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blended.save(output_path)
    print(f"Saved output to {output_path}")


if __name__ == "__main__":
    main()
