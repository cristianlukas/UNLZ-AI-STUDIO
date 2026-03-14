import argparse
import os
import sys
from pathlib import Path


def _patch_torch_for_diffusers():
    """
    Fix PyTorch 2.4+ compatibility with diffusers' flash attention custom ops.
    
    The issue: diffusers tries to register custom PyTorch ops with type annotations
    that newer PyTorch versions don't accept. This bypass prevents the registration
    and uses the fallback implementation.
    """
    try:
        import torch._library.custom_ops as custom_ops_module
        
        original_define = custom_ops_module.define
        
        def patched_define(name, *args, **kwargs):
            """Wrapper that skips registration for known problematic functions"""
            def decorator(fn):
                # Skip custom op registration for difussers' flash attention functions
                if "_wrapped_flash_attn" in name or "flash_attention" in name:
                    return fn  # Return unwrapped function
                return original_define(name, *args, **kwargs)(fn)
            return decorator
        
        custom_ops_module.define = patched_define
        
    except Exception:
        pass  # If outer patch fails, try another approach
    
    try:
        import torch._library
        
        # Also patch the register_op function that gets called internally
        if hasattr(torch._library, "impl"):
            original_torch_def = getattr(torch._library.impl, "_define", None)
            if original_torch_def:
                def patched_torch_def(*args, **kwargs):
                    try:
                        return original_torch_def(*args, **kwargs)
                    except (ValueError, RuntimeError) as e:
                        if "_wrapped_flash_attn" in str(args) or "flash_attention" in str(args):
                            return None
                        raise
                
                torch._library.impl._define = patched_torch_def
    except Exception:
        pass


# Apply patch immediately before any imports
_patch_torch_for_diffusers()


def load_hf_token():
    try:
        from huggingface_hub import HfFolder
        return HfFolder.get_token()
    except Exception:
        return None


def ensure_model_download(model_id, token):
    from huggingface_hub import HfApi, hf_hub_download

    print(f"Checking model cache: {model_id}", flush=True)
    api = HfApi()
    files = api.list_repo_files(model_id, token=token)
    total = len(files)
    for idx, filename in enumerate(files, start=1):
        print(f"Downloading {idx}/{total}: {filename}", flush=True)
        hf_hub_download(repo_id=model_id, filename=filename, token=token)
    print("Model files ready.", flush=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--guidance", type=float, default=3.5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--output", default="")
    parser.add_argument("--download-only", action="store_true")
    return parser.parse_args()


def resolve_device(requested):
    import torch

    if requested and requested != "auto":
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


def main():
    args = parse_args()

    token = load_hf_token()
    if token:
        os.environ["HF_TOKEN"] = token
        os.environ["HUGGINGFACE_HUB_TOKEN"] = token
    else:
        print("Warning: HF token not found. If the model is gated, download will fail.", flush=True)

    if args.download_only:
        ensure_model_download(args.model, token)
        print("Download completed.", flush=True)
        return

    if not args.prompt:
        raise SystemExit("Prompt is required.")

    import torch
    
    try:
        from diffusers import Flux2KleinPipeline
    except (ImportError, ValueError, RuntimeError) as e:
        message = str(e)
        if "Qwen3ForCausalLM" in message:
            print(
                "\n" + "="*80,
                "COMPATIBILITY ERROR: transformers could not load Qwen3ForCausalLM.",
                "="*80,
                "\nThis is usually caused by torchao 0.16.x with torch 2.5.0.",
                "\nFix:",
                "1. Remove torchao:   python -m pip uninstall -y torchao",
                "2. Reinstall deps:   python -m pip install --upgrade diffusers transformers accelerate safetensors huggingface_hub pillow",
                "\nAfter that, run Flux 2 Klein again.",
                "="*80,
                sep="\n",
                flush=True,
            )
            raise SystemExit(f"Cannot import Flux2KleinPipeline: {e}") from e
        if "infer_schema" in str(e) and "_wrapped_flash_attn" in str(e):
            print(
                "\n" + "="*80,
                "COMPATIBILITY ERROR: PyTorch/diffusers version mismatch detected.",
                "="*80,
                "\nThe Flux2Klein model requires compatible versions of PyTorch and diffusers.",
                "\nPossible solutions:",
                "1. Upgrade diffusers:  pip install --upgrade diffusers",
                "2. Downgrade PyTorch:  Use a stable 2.0.x or 2.1.x version",
                "3. Reinstall both:     pip install --upgrade --force-reinstall torch diffusers",
                "\nFor immediate use, try reducing the constraint by updating packages.",
                "="*80,
                sep="\n",
                flush=True,
            )
            raise SystemExit(f"Cannot import Flux2KleinPipeline: {e}") from e
        raise

    device = resolve_device(args.device)
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"Device: {device}, dtype: {dtype}", flush=True)

    ensure_model_download(args.model, token)
    pipe = Flux2KleinPipeline.from_pretrained(args.model, torch_dtype=dtype, token=token)
    pipe = pipe.to(device)

    generator = None
    if args.seed is not None:
        generator = torch.Generator(device=device).manual_seed(args.seed)

    result = pipe(
        prompt=args.prompt,
        width=args.width,
        height=args.height,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance,
        generator=generator,
    )
    image = result.images[0] if hasattr(result, "images") else result[0]

    output_path = Path(args.output or f"klein_{int(torch.randint(0, 999999, (1,)).item())}.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Saved output to {output_path}", flush=True)


if __name__ == "__main__":
    main()
