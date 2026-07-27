"""Prepare a CorridorKey shot and run its official CLI.

CorridorKey remains an external checkout. This adapter only translates paths
selected in UNLZ AI Studio to CorridorKey's Input/AlphaHint folder convention.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "shot"


def link_or_copy(source: Path, destination: Path) -> None:
    if source.is_dir():
        try:
            os.symlink(source, destination, target_is_directory=True)
            return
        except OSError:
            shutil.copytree(source, destination)
            return
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source.name
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--alpha", required=True)
    parser.add_argument("--job", default="shot")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu", "mps"), default="auto")
    parser.add_argument("--screen-color", choices=("auto", "green", "blue"), default="auto")
    parser.add_argument("--colorspace", choices=("srgb", "linear"), default="srgb")
    parser.add_argument("--despill", type=int, default=5)
    parser.add_argument("--despeckle-size", type=int, default=400)
    parser.add_argument("--refiner", type=float, default=1.0)
    parser.add_argument("--image-size", type=int, choices=(512, 1024, 2048), default=2048)
    parser.add_argument("--no-despeckle", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    backend = Path(args.backend).resolve()
    input_path = Path(args.input).expanduser().resolve()
    alpha_path = Path(args.alpha).expanduser().resolve()
    if not backend.is_dir():
        raise SystemExit("CorridorKey backend not found")
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    if not alpha_path.exists():
        raise SystemExit(f"Alpha Hint not found: {alpha_path}")

    job_name = safe_name(args.job)
    workspace = backend.parents[1] / "corridorkey-out" / job_name
    clips_dir = workspace / "ClipsForInference"
    shot_dir = clips_dir / job_name
    if shot_dir.exists() and not args.skip_existing:
        shutil.rmtree(shot_dir)
    shot_dir.mkdir(parents=True, exist_ok=True)
    input_dir = shot_dir / "Input"
    alpha_dir = shot_dir / "AlphaHint"
    if not input_dir.exists():
        link_or_copy(input_path, input_dir)
    if not alpha_dir.exists():
        link_or_copy(alpha_path, alpha_dir)
    (shot_dir / "VideoMamaMaskHint").mkdir(exist_ok=True)

    cmd = [
        sys.executable, "-m", "uv", "run", "--project", str(backend), "corridorkey",
        "--device", args.device, "run-inference",
        "--screen-color", args.screen_color,
        "--linear" if args.colorspace == "linear" else "--srgb",
        "--despill", str(max(0, min(10, args.despill))),
        "--despeckle" if not args.no_despeckle else "--no-despeckle",
        "--despeckle-size", str(max(0, args.despeckle_size)),
        "--refiner", str(args.refiner),
        "--image-size", str(args.image_size),
        "--comp",
        "--cpu-post",
        "--skip-existing",
    ]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    print(f"Prepared shot: {shot_dir}", flush=True)
    print("Outputs will be written to FG, Matte, Processed and Comp.", flush=True)
    return subprocess.call(cmd, cwd=workspace, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
