import argparse
import atexit
import importlib.util
import os
import sys
from pathlib import Path


def _patch_multiprocess_cleanup():
    """Patch multiprocess ResourceTracker to handle cleanup errors gracefully.
    
    On Windows with certain Python/torch/multiprocess combinations, the
    ResourceTracker cleanup fails with AttributeError on _thread.RLock._recursion_count.
    This patch wraps the cleanup to suppress the error silently.
    """
    try:
        from multiprocess import resource_tracker
        
        _original_stop_locked = resource_tracker.ResourceTracker._stop_locked
        
        def _patched_stop_locked(self):
            try:
                _original_stop_locked(self)
            except AttributeError as e:
                if "_recursion_count" in str(e):
                    # Silently ignore the known multiprocess cleanup error
                    pass
                else:
                    raise
        
        resource_tracker.ResourceTracker._stop_locked = _patched_stop_locked
    except Exception:
        # If patching fails, just continue; this is a best-effort fix
        pass


_patch_multiprocess_cleanup()


def _error_chain_text(exc: Exception) -> str:
    parts = []
    seen = set()
    stack = [exc]
    while stack:
        current = stack.pop(0)
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        text = str(current)
        if text:
            parts.append(text)
        cause = getattr(current, "__cause__", None)
        context = getattr(current, "__context__", None)
        if cause is not None:
            stack.append(cause)
        if context is not None:
            stack.append(context)
    return "\n".join(parts).lower()


def _is_torchvision_mismatch(exc: Exception) -> bool:
    text = _error_chain_text(exc)
    return (
        "torchvision::nms" in text
        or "could not import module 'hubertmodel'" in text
        or "from torchvision.transforms import interpolationmode" in text
    )


def _import_neutts_with_torchvision_fallback():
    try:
        from neutts import NeuTTS
        return NeuTTS
    except Exception as exc:
        if not _is_torchvision_mismatch(exc):
            raise

        # Transformers marks torchvision as available via find_spec(). If torchvision
        # is installed but ABI-incompatible with torch, force it as unavailable.
        original_find_spec = importlib.util.find_spec

        def _patched_find_spec(name, package=None):
            if name == "torchvision" or name.startswith("torchvision."):
                return None
            return original_find_spec(name, package)

        importlib.util.find_spec = _patched_find_spec
        try:
            for module_name in list(sys.modules.keys()):
                if module_name == "transformers" or module_name.startswith("transformers."):
                    sys.modules.pop(module_name, None)
                elif module_name == "torchvision" or module_name.startswith("torchvision."):
                    sys.modules.pop(module_name, None)
            from neutts import NeuTTS
            return NeuTTS
        finally:
            importlib.util.find_spec = original_find_spec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--ref-audio", required=True)
    parser.add_argument("--ref-text", required=True)
    parser.add_argument("--backbone", required=True)
    parser.add_argument("--codec", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure local backend package is importable even when it is not installed in site-packages.
    backend_dir = Path(os.environ.get("NEUTTS_BACKEND_DIR", "")).resolve() if os.environ.get("NEUTTS_BACKEND_DIR") else None
    if not backend_dir:
        backend_dir = Path(__file__).resolve().parents[2] / "ai-backends" / "neutts"
    backend_str = str(backend_dir)
    if backend_dir.exists() and backend_str not in sys.path:
        sys.path.insert(0, backend_str)

    NeuTTS = _import_neutts_with_torchvision_fallback()
    import soundfile as sf

    tts = NeuTTS(
        backbone_repo=args.backbone,
        backbone_device=args.device,
        codec_repo=args.codec,
        codec_device=args.device,
    )
    ref_codes = tts.encode_reference(args.ref_audio)
    wav = tts.infer(args.text, ref_codes, args.ref_text)
    sf.write(str(output_path), wav, 24000)
    print(str(output_path))


if __name__ == "__main__":
    main()
